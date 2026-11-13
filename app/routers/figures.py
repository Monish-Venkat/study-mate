"""Serve textbook figures and search them by caption."""
import re

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.services.figures import figures_dir, find_figures

router = APIRouter(tags=['figures'])

ID = re.compile(r'^[0-9a-f]{16}$')


def _record(figure_id: str):
    from app.services.faiss_store import store
    for item in store.meta:
        if item.get('doc_type') == 'figure' and item.get('figure_id') == figure_id:
            return item
    return None


@router.get('/figures/search')
async def search(q: str = Query(min_length=2, max_length=300),
                 subject: str = Query(min_length=2, max_length=40),
                 level: str = 'PUC2', board: str = 'KA', k: int = Query(3, ge=1, le=6)):
    hits = await find_figures(q, subject, level, board, k)
    return {'figures': [{
        'id': h['figure_id'],
        'label': h.get('figure_label'),
        'caption': h.get('caption'),
        'source': h.get('source'),
        'page': h.get('page'),
        'score': round(h.get('score', 0), 3),
        'width': h.get('width'), 'height': h.get('height'),
        # The caption-to-image pairing is positional on a multi-figure page, so
        # the client is told when it was not a one-to-one match.
        'approximate': not h.get('caption_exact', True),
        # A plate is one caption over several lettered panels. The panel a
        # given image shows is NOT known (caption order, the printed (a)(b)(c)
        # markers and the PDF's image order all disagree), so the client gets
        # the whole plate caption and says so rather than naming a panel.
        'plate': bool(h.get('plate')),
        # Cropped from a rendered page rather than lifted from an embedded
        # image. The crop's upper edge is inferred from whitespace, so a tall
        # diagram can lose its top row — the client says so.
        'rendered': bool(h.get('rendered')),
        'url': f"/figures/{h['figure_id']}.png",
    } for h in hits]}


@router.get('/figures/{figure_id}.png')
def figure(figure_id: str):
    if not ID.match(figure_id):
        raise HTTPException(status_code=400, detail='Invalid figure id.')
    record = _record(figure_id)
    if not record:
        raise HTTPException(status_code=404, detail='Figure not found.')
    root = figures_dir().resolve()
    path = (root / record['figure_path']).resolve()
    # The stored path comes from our own extractor, but it is still joined to a
    # root and checked: a traversal here would serve arbitrary local files.
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(status_code=404, detail='Figure not found.')
    return FileResponse(path, media_type='image/png')
