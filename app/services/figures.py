"""Textbook figure extraction and retrieval.

A Mermaid study map shows how ideas relate; it is not what a board paper means
by a diagram. A 5-mark Karnataka item asking for a labelled diagram of the
human heart wants the heart. Those diagrams already exist in the prescribed
NCERT and PUC books that are indexed for text, so they are taken from there
rather than from the open web: the figure is the one the exam was written
against, and it arrives with a source and page like every other claim.

Extraction is deliberately conservative. A page's embedded images include
rules, logos and page furniture as well as figures, and nothing in the PDF
marks which is which, so three filters run:

  * content hash — furniture repeats byte-identically across a book, so any
    image appearing on several pages of the same file is dropped;
  * size — thumbnails and rules are below the floor;
  * caption — an image on a page with no "Figure N.N" caption is skipped,
    because an uncaptioned figure is both unsearchable and unverifiable.

The caption is what gets embedded, so "diagram of the heart" matches
"Figure 18.4 Section of the human heart". Pairing a caption to an image on a
multi-figure page is positional and therefore approximate; the page number is
always carried so a student can check.
"""
from __future__ import annotations

import hashlib
import io
import re
from collections import Counter
from pathlib import Path

from app.core.config import settings

FIGURES_DIRNAME = 'figures'

# "Figure 3.1 Algae : (a) Green algae" / "Fig. 18.4 Section of the human heart"
# A plate caption runs over several lines in the source:
#     Figure 2.4 (a) Dinoflagellates
#     (b) Euglena
#     (c) Slime mould
# Reading only to the first newline saw "(a) Dinoflagellates" and nothing
# else, so every panel inherited the first panel's name. The caption is now
# read up to the next blank line, page footer or figure number.
CAPTION = re.compile(
    r'(Fig(?:ure)?\.?\s*(\d+\.\d+[a-z]?))\s*[:\-–]?\s*'
    r'([\s\S]{0,240}?)(?=\n\s*\n|Reprint\s*20|Fig(?:ure)?\.?\s*\d+\.\d+|\Z)',
    re.IGNORECASE,
)

MIN_BYTES = 14_000
MIN_SIDE = 110
# Furniture repeats; a real figure does not appear on many pages of one book.
MAX_PAGES_PER_IMAGE = 3


def figures_dir() -> Path:
    return Path(settings.DATA_DIR) / FIGURES_DIRNAME


def _clean(text: str) -> str:
    return ' '.join(text.split()).strip(' .;:,')


# NCERT captions a plate of images once: "Figure 2.4 (a) Dinoflagellates
# (b) Euglena (c) Slime mould". Each panel is a different organism, so the
# caption has to be split or every panel inherits the first panel's name.
PANEL = re.compile(r'\(([a-z])\)\s*')


def panel_names(body: str) -> list[str]:
    """Names of the lettered panels in a plate caption, in caption order."""
    parts = PANEL.split(body)
    # re.split with one group yields [pre, letter, text, letter, text, ...].
    if len(parts) < 3:
        return []
    lead = _clean(parts[0])
    names = []
    for _letter, text in zip(parts[1::2], parts[2::2]):
        name = _clean(text)
        if not name:
            # Bare "(a)" markers are printed beside each panel on the page;
            # no text follows them.
            continue
        # Keep the shared stem ("Fungi:") so a name still reads in isolation.
        names.append(_clean(f'{lead} {name}'.strip() if lead else name))
    return names


def page_captions(text: str) -> list[tuple[str, str, bool]]:
    """Return (label, description, is_plate) for each caption on a page.

    A plate caption covering several panels is deliberately NOT split across
    the images. Three different orders are in play: the order the caption
    lists the panels, the order the "(a) (b) (c)" markers are printed beside
    the figures on the page, and the order the images come out of the PDF.
    They do not agree, so pairing positionally produced a Euglena confidently
    captioned "Dinoflagellates" — a wrong label a student has no way to catch.

    Every panel of a plate therefore carries the whole plate caption, which is
    true of all of them, and is flagged so the client can say it is a plate.
    """
    out = []
    for match in CAPTION.finditer(text or ''):
        label = _clean(match.group(1)).replace('Fig ', 'Fig. ')
        body = _clean(match.group(3).replace('\n', ' '))
        # A bare cross-reference such as "shown in Figure 3.1)." is not a caption.
        if len(body) < 12 or body.startswith(')'):
            continue
        names = panel_names(body)
        if len(names) > 1:
            out.append((label, ', '.join(names), True))
        else:
            out.append((label, body, False))
    return out


def _normalise(data: bytes, name: str):
    """Return (png_bytes, width, height) or None if unusable.

    Embedded images may be JPEG 2000, which browsers cannot display, so every
    figure is re-encoded to PNG rather than served in its original container.
    """
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - Pillow ships with the project
        return None
    try:
        with Image.open(io.BytesIO(data)) as im:
            width, height = im.size
            if width < MIN_SIDE or height < MIN_SIDE:
                return None
            # Page-sized streams are separation layers and backgrounds, not
            # figures: A4 at 300dpi is 2480x3508.
            if width >= 2300 and height >= 3300:
                return None
            # Masks and backgrounds survive every size filter because they are
            # genuinely large; they are rejected here because they carry no
            # detail. One biology chapter yielded a solid black 2480x3508 PNG.
            grey = im.convert('L')
            low, high = grey.getextrema()
            if high - low < 24:
                return None
            # A near-uniform image has almost all of its mass in a few levels.
            histogram = grey.histogram()
            pixels = width * height
            if max(histogram) / pixels > 0.995:
                return None
            if im.mode not in ('RGB', 'L'):
                im = im.convert('RGB')
            buffer = io.BytesIO()
            # No optimize pass: it roughly triples encode time across a corpus
            # this size for a few percent of file size.
            im.save(buffer, format='PNG', compress_level=6)
            return buffer.getvalue(), width, height
    except Exception:
        return None


def _image_meta(page):
    """Name and pixel size of every image on a page, read without decoding it.

    pypdf decodes a stream the moment `.data` is touched, and the things that
    most need rejecting — full-page separation layers and background masks —
    are the most expensive streams on the page. Reading /Width and /Height
    from the image XObject's dictionary costs a lookup, so the cheap
    rejections happen before any decode rather than after two of them.

    Returned in dictionary order, which is the same provenance `page.images`
    uses, so caption pairing is unchanged.
    """
    try:
        resources = page.get('/Resources')
        xobjects = resources.get('/XObject') if resources else None
        xobjects = xobjects.get_object() if xobjects is not None else None
    except Exception:
        return []
    if not xobjects:
        return []
    out = []
    for name in list(xobjects.keys()):
        try:
            obj = xobjects[name].get_object()
            if obj.get('/Subtype') != '/Image':
                continue
            width = int(obj.get('/Width') or 0)
            height = int(obj.get('/Height') or 0)
        except Exception:
            continue
        if width < MIN_SIDE or height < MIN_SIDE:
            continue
        # A4 at 300dpi is 2480x3508: that is a page, not a figure.
        if width >= 2300 and height >= 3300:
            continue
        out.append((name, width, height))
    return out


def extract(pdf_path: Path, subject: str, level: str, board: str, out_dir: Path):
    """Extract captioned figures from one PDF. Returns a list of records."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    stem = pdf_path.stem

    # First pass: collect candidates and count hashes so furniture can be seen.
    candidates: list[dict] = []
    seen = Counter()
    for number, page in enumerate(reader.pages, 1):
        # Captions are read first and the page abandoned if it has none.
        # Touching page.images decodes every embedded stream on the page, which
        # dominates runtime, and a page without a caption can yield no figure
        # however many images it holds.
        captions = page_captions(page.extract_text() or '')
        if not captions:
            continue
        # Only images that survive the dictionary-level size filter are
        # decoded. Everything rejected here used to cost a full decode first.
        usable = []
        for name, width, height in _image_meta(page):
            try:
                image = page.images[name]
                data = image.data
            except Exception:
                continue
            if len(data) >= MIN_BYTES:
                usable.append((data, image.name))
        for position, (data, image_name) in enumerate(usable):
            digest = hashlib.sha1(data).hexdigest()
            seen[digest] += 1
            label, body, plate = captions[min(position, len(captions) - 1)]
            candidates.append({
                'digest': digest, 'data': data, 'name': image_name,
                'page': number, 'label': label, 'caption': body,
                'plate': plate,
                # A page with one caption per image pairs exactly. A plate
                # never does, so it is never reported as exact.
                'exact': position < len(captions) and not plate,
                'rendered': False,
            })

        # Captions left without an image are the vector figures: mathematics
        # and chemistry draw them as line art, so there is no raster to find.
        # Those are rendered from the page instead.
        for position in range(len(usable), len(captions)):
            label, body, plate = captions[position]
            rendered = render_caption_region(pdf_path, number, label)
            if not rendered:
                continue
            png, _width, _height = rendered
            digest = hashlib.sha1(png).hexdigest()
            seen[digest] += 1
            candidates.append({
                'digest': digest, 'data': png, 'name': 'render.png',
                'page': number, 'label': label, 'caption': body,
                'plate': plate,
                'exact': not plate,
                # Cropped from the page rather than lifted from an image
                # stream. The crop's top edge is inferred, so this is carried
                # through to the client rather than passed off as an original.
                'rendered': True,
            })

    records = []
    written: set[str] = set()
    out_dir.mkdir(parents=True, exist_ok=True)
    for candidate in candidates:
        digest = candidate['digest']
        if seen[digest] > MAX_PAGES_PER_IMAGE or digest in written:
            continue
        normalised = _normalise(candidate['data'], candidate['name'])
        if not normalised:
            continue
        png, width, height = normalised
        written.add(digest)
        figure_id = f'{digest[:16]}'
        relative = f'{subject}/{level}/{figure_id}.png'
        target = out_dir / subject / level / f'{figure_id}.png'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(png)
        caption = candidate['caption']
        records.append({
            # The embedded text is what a student's words have to match, so it
            # carries the caption, the subject and the word "diagram".
            'text': f"{candidate['label']} {caption} — {subject} diagram",
            'figure_id': figure_id,
            'figure_path': relative,
            'figure_label': candidate['label'],
            'caption': caption,
            'width': width, 'height': height,
            'subject': subject, 'level': level, 'board': board,
            'doc_type': 'figure',
            'source': pdf_path.name,
            'source_path': pdf_path.resolve().as_posix(),
            'page': candidate['page'],
            'caption_exact': candidate['exact'],
            'plate': candidate['plate'],
            'rendered': candidate.get('rendered', False),
        })
    return records


# Re-tuned against the full corpus (164 figures), as the previous note asked.
# The earlier value of 0.40 came from 9 figures drawn from two chapters; with
# the whole corpus indexed there are far more near-misses and that floor lets
# them through.
#
# Measured, top hit per query:
#   correct   mucor 0.749, plane wave 0.694, slime mould 0.582,
#             prism 0.425, cycad 0.397
#   WRONG     "structure of a neuron" -> Chemical structure of Morphine 0.454
#             "human heart" -> female reproductive system 0.407
#   nothing   locomotive 0.227, cake 0.198, capital of France 0.104
#
# The wrong matches outscore two of the correct ones, so no threshold
# separates them cleanly. 0.55 is chosen because the costs are asymmetric: a
# missed figure is a blank space the student can ignore, while a confident
# wrong diagram beside a correct answer is an error they cannot detect. That
# keeps the three strong matches, drops prism and cycad, and sits far above
# the 0.227 ceiling of the true negatives.
#
# Recall improves by indexing more figures, not by lowering this.
FIGURE_FLOOR = 0.55


async def find_figures(query: str, subject: str, level: str, board: str, k: int = 3,
                       floor: float = FIGURE_FLOOR):
    """Retrieve figures for a question. Returns [] when nothing clears the floor."""
    import asyncio

    from app.services.embeddings import embed_text
    from app.services.faiss_store import store

    if not store.index.ntotal:
        return []
    normalised_level = {'PUC1': '1st', 'PUC2': '2nd'}.get(level.upper(), level.lower())
    filters = {'subject': [subject.lower()], 'level': [normalised_level],
               'doc_type': ['figure']}
    vector = await asyncio.to_thread(embed_text, query)
    hits = await asyncio.to_thread(store.search, vector, k, filters)
    # A weak caption match is worse than no figure: showing the wrong diagram
    # beside a correct answer is a mistake a student cannot detect.
    return [h for h in hits if h.get('score', 0) >= floor]


# Vector figures ------------------------------------------------------------
# Mathematics and chemistry draw their figures as vector line art rather than
# as embedded raster images, so nothing in the image XObjects sees them: a
# geometry construction or a reaction mechanism is drawing operators, not a
# picture. Those pages are instead rendered and the region above the caption
# is cropped out.
#
# Where the figure sits is inferred, not known: a caption is almost always
# directly beneath its figure, so the region runs from the top of the caption
# up to whatever text lies above it. That is a heuristic, and a crop that
# comes out blank or implausibly tall is discarded rather than published.

RENDER_SCALE = 2.0
MIN_REGION_POINTS = 54          # shorter than this is a stray line, not a figure
MAX_REGION_FRACTION = 0.72      # taller than this means the bound was not found


def _caption_anchor(textpage, text, label):
    """Bounding box of the caption itself, or None.

    The label also appears in running text — "as shown in Fig. 1.2" — and
    anchoring on that lands in the middle of a paragraph, which is how a crop
    of two columns of prose ended up looking like a successful extraction. A
    real caption starts its line, so occurrences preceded by anything other
    than a line break are skipped.
    """
    index = -1
    search_from = 0
    while True:
        found = text.find(label, search_from)
        if found < 0:
            break
        preceding = text[max(0, found - 1):found]
        if found == 0 or preceding in ('\n', '\r'):
            index = found
            break
        search_from = found + 1
    if index < 0:
        return None
    boxes = []
    for offset in range(index, min(index + len(label), textpage.count_chars())):
        try:
            boxes.append(textpage.get_charbox(offset))
        except Exception:
            continue
    boxes = [b for b in boxes if b and (b[2] - b[0]) >= 0 and (b[3] - b[1]) >= 0]
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def _region_above(textpage, anchor, page_width, page_height):
    """The rectangle between the caption and the nearest text above it."""
    left, _bottom, right, top = anchor
    nearest = None
    span_left, span_right = left, right
    # Only text in the caption's own column counts. Scanning the whole page
    # meant a line in the facing column, level with the figure, set the
    # ceiling and collapsed the region to nothing — which is why almost every
    # candidate was being rejected.
    band_left = left - page_width * 0.03
    band_right = right + page_width * 0.03
    for index in range(textpage.count_chars()):
        try:
            box = textpage.get_charbox(index)
        except Exception:
            continue
        if not box:
            continue
        # Only text genuinely above the caption, with a small tolerance so the
        # caption's own second line is not mistaken for the boundary.
        if box[1] <= top + 2:
            continue
        if box[2] < band_left or box[0] > band_right:
            continue
        if nearest is None or box[1] < nearest:
            nearest = box[1]
    ceiling = nearest if nearest is not None else page_height * 0.96
    if ceiling - top < MIN_REGION_POINTS:
        return None
    if (ceiling - top) / page_height > MAX_REGION_FRACTION:
        return None
    # Figures are usually wider than their caption, so the crop is widened to
    # the page's text column rather than to the caption's own extent.
    margin = page_width * 0.07
    return (max(margin, min(span_left, margin)), top,
            min(page_width - margin, max(span_right, page_width - margin)), ceiling)


def _trim_to_figure(image, caption_px: int, width_px: int):
    """Find the figure's top edge by looking for the whitespace gutter.

    Text geometry cannot do this. A vector figure is full of text — axis
    labels, node names, element symbols — so "the nearest text above the
    caption" lands inside the figure itself, which collapsed the region to a
    few points and rejected nearly every candidate.

    Pixels do not have that problem. Walking up from the caption, the figure
    is ink; the body text above it is separated from it by a band of blank
    rows. The first such band after ink is the figure's top.
    """
    try:
        import numpy as np
    except ImportError:
        return None
    grey = image.convert('L')
    rows = np.asarray(grey, dtype='uint8')
    if rows.size == 0:
        return None
    # A row counts as blank when almost every pixel is near-white.
    blank = (rows > 244).mean(axis=1) > 0.995
    # The gap between a figure and the text above it is larger than the gaps
    # inside the figure. Too small a threshold fires on the whitespace between
    # a tree diagram's rows and lops its top off.
    gutter = max(14, int(image.height * 0.035))
    top = None
    seen_ink = False
    run = 0
    for y in range(min(caption_px, len(blank)) - 1, -1, -1):
        if blank[y]:
            run += 1
            if seen_ink and run >= gutter:
                top = y + run
                break
        else:
            seen_ink = True
            run = 0
    if not seen_ink:
        return None
    if top is None:
        top = 0
    return top


def render_caption_region(pdf_path: Path, page_number: int, label: str):
    """Render the figure above a caption. Returns (png, width, height) or None."""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return None
    try:
        pdf = pdfium.PdfDocument(str(pdf_path))
    except Exception:
        return None
    try:
        page = pdf[page_number - 1]
        page_width, page_height = page.get_size()
        textpage = page.get_textpage()
        text = textpage.get_text_range()
        anchor = _caption_anchor(textpage, text, label)
        if not anchor:
            return None
        anchor_left, _bottom, anchor_right, caption_top = anchor
        margin = page_width * 0.07
        # These books are set in two columns, so cropping the full text width
        # captured the facing column as well. The figure lives in the caption's
        # own column; which one that is follows from where the caption sits.
        midpoint = page_width / 2
        gutter = page_width * 0.02
        if anchor_right < midpoint:
            col_left, col_right = margin, midpoint - gutter
        elif anchor_left > midpoint:
            col_left, col_right = midpoint + gutter, page_width - margin
        else:
            # Spans the middle: a full-width figure.
            col_left, col_right = margin, page_width - margin
        ceiling = min(page_height * 0.97, caption_top + page_height * MAX_REGION_FRACTION)
        if ceiling - caption_top < MIN_REGION_POINTS:
            return None
        image = page.render(scale=RENDER_SCALE).to_pil()
        # PDF space has its origin bottom-left; the rendered bitmap's is top-left.
        band = image.crop((int(col_left * RENDER_SCALE),
                           int((page_height - ceiling) * RENDER_SCALE),
                           int(col_right * RENDER_SCALE),
                           # A couple of points past the caption's top edge:
                           # cutting exactly there clipped the figure's last
                           # row of labels.
                           int((page_height - caption_top + 3) * RENDER_SCALE)))
        cut = _trim_to_figure(band, band.height, band.width)
        if cut is None:
            return None
        crop = band.crop((0, cut, band.width, band.height))
        if crop.width < MIN_SIDE or crop.height < MIN_SIDE:
            return None
        import io as _io
        buffer = _io.BytesIO()
        crop.save(buffer, format='PNG', compress_level=6)
        data = buffer.getvalue()
        # Reuse the uniformity test: a crop of white space is not a figure.
        checked = _normalise(data, 'render.png')
        return checked
    except Exception:
        return None
    finally:
        try:
            pdf.close()
        except Exception:
            pass
