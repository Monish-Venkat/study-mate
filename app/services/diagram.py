"""Diagram-based learning.

A diagram is only useful if it renders. Language models write Mermaid that is
plausible but frequently unparseable: unquoted labels containing brackets,
LaTeX inside nodes, an id reused with two different labels, inconsistent
indentation in a mindmap. Validating such output and rejecting it wastes a
generation; trusting it shows the student a parser error.

So this module does neither. It parses what the model wrote into nodes and
edges, discards anything it cannot interpret, and re-emits the diagram from
that structure. The output is Mermaid this module generated, so it parses by
construction, and a malformed label degrades into a cleaned label rather than
into a broken diagram. Repair is attempted once, and only when parsing
recovered too little to be worth showing.
"""
import re

from app.core.config import settings
from app.core.prompts import DIAGRAM_KINDS, diagram_prompt, diagram_repair_prompt
from app.services.llm_client import generate_text, GenerationUnavailable

MAX_NODES = 18
MAX_LABEL = 72
MIN_NODES = 3

_FENCE = re.compile(r'```[ \t]*mermaid[ \t]*\r?\n(.*?)```', re.S | re.I)
_ANY_FENCE = re.compile(r'```[a-zA-Z]*[ \t]*\r?\n(.*?)```', re.S)
_ID = re.compile(r'^[A-Za-z][A-Za-z0-9_]*$')

# Quoted labels are what the prompt asks for, so they are tried first and are
# unambiguous: the label cannot contain the delimiter that ends it.
_QUOTED_NODE = re.compile(
    r'\b([A-Za-z][A-Za-z0-9_]*)\s*(\(\[|\[\[|\(\(|\{\{|\[|\(|\{)\s*'
    r'"([^"]*)"\s*(?:\]\)|\]\]|\)\)|\}\}|\]|\)|\})')
# Bracket pairs for the unquoted fallback, longest delimiters first so that
# "([" is never mistaken for a bare "(". Each pair forbids only its own
# delimiters inside the label, so a square-bracketed label may legitimately
# contain parentheses -- "F1[focal length (f)]" is common and must not be
# dropped for it.
_PAIRS = [('([', r'\(\[', r'[^\]\)|]*?', r'\]\)'),
          ('[[', r'\[\[', r'[^\]|]*?', r'\]\]'),
          ('((', r'\(\(', r'[^\)|]*?', r'\)\)'),
          ('{{', r'\{\{', r'[^\}|]*?', r'\}\}'),
          ('[', r'\[', r'[^\[\]|]*?', r'\]'),
          ('(', r'\(', r'[^()|]*?', r'\)'),
          ('{', r'\{', r'[^{}|]*?', r'\}')]
_SHAPE = {'([': 'stadium', '[[': 'rect', '((': 'circle', '{{': 'hex',
          '[': 'rect', '(': 'round', '{': 'diamond'}
_OPEN = {'rect': '[', 'round': '(', 'diamond': '{', 'stadium': '([', 'circle': '((', 'hex': '{{'}
_CLOSE = {'rect': ']', 'round': ')', 'diamond': '}', 'stadium': '])', 'circle': '))', 'hex': '}}'}

_ARROW = re.compile(r'\s*(?:-{2,}>|={2,}>|-\.-*>|-{3,}|={3,})\s*'
                    r'(?:\|\s*"?([^|"]*)"?\s*\|\s*)?')
# Directives that restyle, script or re-configure the chart. None are needed
# for a teaching diagram and all are a way for generated text to reach beyond
# the diagram, so they are dropped rather than sanitised.
_DIRECTIVE = re.compile(r'^\s*(?:%%|click|style|classDef|class |linkStyle|subgraph|end\b|'
                        r'direction\b|accTitle|accDescr)', re.I)
_HEADER = re.compile(r'^\s*(?:flowchart|graph)\b', re.I)
# The heading the prompt asks for after the fence. Doubles as the boundary when
# the model never wrote a fence at all.
# Matches the heading only, never the sentence after it: models write both
# "How to read this\n..." and "How to read this: ...", and an alternative
# greedy to end of line would delete the very notes being extracted.
_READING = re.compile(
    r'^[ \t]*#*[ \t]*(?:how to read this|how to read|reading guide|notes?|explanation)'
    r'(?:[ \t]*:[ \t]*|[ \t]*$)', re.I | re.M)


def _clean_label(text, strict=False):
    """Make a label safe to place inside Mermaid node syntax."""
    text = re.sub(r'\s+', ' ', str(text)).strip()
    # Models reach for identifier style inside labels; a student reads
    # "angle of incidence", not "angle_of_incidence".
    text = text.replace('_', ' ')
    text = text.replace('`', '').replace('"', "'")
    # LaTeX renders as literal noise inside a node, but a fraction carries real
    # meaning, so rewrite it before stripping the rest of the markup.
    text = re.sub(r'\\[dt]?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}', r'(\1/\2)', text)
    text = re.sub(r'\\[a-zA-Z]+|\$', ' ', text)
    # Braces left behind by other commands are grouping, never content.
    text = re.sub(r'[{}]', ' ', text)
    text = re.sub(r'[<>#&;]', ' ', text)
    if strict:
        # Mindmap labels are unquoted, so every grouping character is a parser
        # instruction rather than text.
        text = re.sub(r'[\[\](){}"\':|]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip(' -:,')
    if len(text) > MAX_LABEL:
        text = text[:MAX_LABEL].rsplit(' ', 1)[0] + '...'
    return text


def _split(raw):
    """Separate the diagram source from the prose that follows it.

    A model that forgets to open or close the fence hands its explanation to
    the diagram parser, which then renders the prose as nodes -- observed live,
    with "How to read this" drawn as a branch of the mindmap. When the fence is
    missing the reading-guide heading is the reliable boundary, so it is
    honoured both as a fallback and as a cut inside an unterminated fence.
    """
    tail = ''
    for pattern in (_FENCE, _ANY_FENCE):
        match = pattern.search(raw)
        if match:
            code, tail = match.group(1), raw[match.end():]
            break
    else:
        heading = _READING.search(raw)
        code = raw[:heading.start()] if heading else raw
        tail = raw[heading.start():] if heading else ''
    inner = _READING.search(code)
    if inner:
        tail = code[inner.start():] + '\n' + tail
        code = code[:inner.start()]
    notes = _READING.sub('', tail).strip().lstrip('#').strip()
    # Models name their nodes in identifier style and then quote those names
    # back in the prose, so "refraction_of_a_plane_wave" reaches the student
    # unless the cleanup applied to labels is applied here too.
    notes = re.sub(r'\b([a-z0-9]+(?:_[a-z0-9]+)+)\b',
                   lambda m: m.group(1).replace('_', ' '), notes, flags=re.I)
    return code, notes


def _strip_definitions(line, nodes):
    """Replace every `id[label]` in the line with `id`, recording the node."""
    def quoted(match):
        node_id, opener, label = match.group(1), match.group(2), match.group(3)
        label = _clean_label(label)
        if label:
            nodes.setdefault(node_id, (_SHAPE.get(opener, 'rect'), label))
        return ' %s ' % node_id

    line = _QUOTED_NODE.sub(quoted, line)
    for literal, opener, content, closer in _PAIRS:
        pattern = re.compile(r'\b([A-Za-z][A-Za-z0-9_]*)\s*' + opener +
                             '(' + content + ')' + closer)

        def unquoted(match, shape=_SHAPE[literal]):
            node_id, label = match.group(1), _clean_label(match.group(2))
            if label:
                nodes.setdefault(node_id, (shape, label))
            return ' %s ' % node_id

        line = pattern.sub(unquoted, line)
    return line


def _parse_flowchart(code):
    """Return (nodes, edges, problems) recovered from a model-written flowchart."""
    nodes, edges, problems = {}, [], []
    for raw_line in code.splitlines():
        line = raw_line.strip()
        if not line or _DIRECTIVE.match(line) or _HEADER.match(line):
            continue
        plain = _strip_definitions(line, nodes)
        parts = _ARROW.split(plain)
        ids = [p.strip() for p in parts[0::2]]
        labels = parts[1::2]
        if len(ids) == 1:
            if ids[0] and not _ID.match(ids[0]):
                problems.append('could not read the line: %s' % line[:60])
            continue
        for i in range(len(ids) - 1):
            src, dst = ids[i], ids[i + 1]
            if not (_ID.match(src) and _ID.match(dst)):
                problems.append('arrow between unreadable nodes: %s' % line[:60])
                continue
            if src not in nodes or dst not in nodes:
                problems.append('arrow uses an undefined node: %s -> %s' % (src, dst))
                continue
            edges.append((src, dst, _clean_label(labels[i] or '')))
    return nodes, edges, problems


def _emit_flowchart(nodes, edges, direction):
    connected = [n for n in nodes if any(n in (s, d) for s, d, _ in edges)]
    used = (connected or list(nodes))[:MAX_NODES]
    keep = set(used)
    lines = ['flowchart %s' % direction]
    for node_id in used:
        shape, label = nodes[node_id]
        lines.append('    %s%s"%s"%s' % (node_id, _OPEN[shape], label, _CLOSE[shape]))
    seen = set()
    for src, dst, label in edges:
        if src not in keep or dst not in keep or (src, dst) in seen:
            continue
        seen.add((src, dst))
        lines.append('    %s -->|"%s"| %s' % (src, label, dst) if label
                     else '    %s --> %s' % (src, dst))
    return '\n'.join(lines), len(used)


def _parse_mindmap(code):
    """Recover (root, [(depth, label)], problems) from a model-written mindmap."""
    rows, problems, root = [], [], ''
    for raw_line in code.splitlines():
        if not raw_line.strip() or raw_line.strip().lower() == 'mindmap':
            continue
        if _DIRECTIVE.match(raw_line):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(' \t'))
        body = raw_line.strip()
        # Single parentheses are a frequent slip, and treating "root(x)" as an
        # ordinary node makes the topic reappear as a branch of itself.
        circle = re.match(r'^(?:root)?\s*\(\(?(.+?)\)?\)$', body, re.I)
        if circle and not root:
            root = _clean_label(circle.group(1), strict=True)
            continue
        body = re.sub(r'^[A-Za-z][A-Za-z0-9_]*\s*(?=[\[({])', '', body)
        label = _clean_label(body, strict=True)
        if not label:
            problems.append('empty node: %s' % raw_line.strip()[:60])
            continue
        rows.append((indent, label))
    if not rows:
        problems.append('no mindmap nodes were found')
        return root, [], problems
    # Model indentation is inconsistent, so rank the distinct indents rather
    # than dividing by an assumed step.
    ranks = {value: i for i, value in enumerate(sorted({r[0] for r in rows}))}
    return root, [(min(ranks[i], 3), label) for i, label in rows], problems


def _emit_mindmap(root, rows, topic):
    rows = rows[:MAX_NODES]
    lines = ['mindmap', '  root((%s))' % (root or _clean_label(topic, strict=True) or 'topic')]
    # A child cannot sit more than one level below its parent or Mermaid
    # throws, so depths are clamped. Clamping each row independently would make
    # siblings at a clamped depth come out nested under one another, so the
    # emitted depth for a source level is remembered and reused; going back up
    # a level forgets the deeper ones, which reopens a genuinely deeper branch.
    emitted_for, previous, seen = {}, -1, set()
    root_label = lines[1].strip()[6:-2].strip().lower()
    written = 0
    for depth, label in rows:
        if depth in emitted_for and emitted_for[depth] <= previous + 1:
            level = emitted_for[depth]
        else:
            level = min(depth, previous + 1)
        emitted_for = {d: e for d, e in emitted_for.items() if d < depth}
        emitted_for[depth] = level
        # Models like to restate the topic as its own first branch, and to
        # repeat a leaf under two parents. Both read as mistakes in a diagram.
        key = label.lower()
        if key == root_label or (level, key) in seen:
            continue
        seen.add((level, key))
        previous = level
        written += 1
        lines.append('  ' * (level + 2) + label)
    return '\n'.join(lines), written


def _render(raw, kind, topic):
    """Turn one model response into renderable Mermaid.

    Returns (code, node count, problems, notes).
    """
    grammar, direction, _ = DIAGRAM_KINDS[kind]
    code, notes = _split(raw)
    if grammar == 'mindmap':
        root, rows, problems = _parse_mindmap(code)
        if not rows:
            return '', 0, problems or ['the mindmap had no readable nodes'], notes
        emitted, count = _emit_mindmap(root, rows, topic)
        return emitted, count, problems, notes
    nodes, edges, problems = _parse_flowchart(code)
    if not edges:
        return '', 0, problems or ['the flowchart had no readable arrows'], notes
    emitted, count = _emit_flowchart(nodes, edges, direction)
    return emitted, count, problems, notes


async def build_diagram(topic, subject, level, board, kind, chapter=None,
                        retrieval_result=None):
    """Retrieve course evidence and draw a validated diagram of it."""
    from app.services.crag import corrective_retrieve
    from app.services.rag import build_context, retrieve

    if kind not in DIAGRAM_KINDS:
        raise ValueError('unknown diagram kind: %s' % kind)

    query = ('%s %s' % (chapter or '', topic)).strip()
    hits, telemetry = await corrective_retrieve(
        query, subject, level, board, ['textbook', 'syllabus'], retrieve)
    if retrieval_result is not None:
        retrieval_result.update(telemetry)
    if not hits:
        return {'mermaid': '', 'notes': '', 'sources': [], 'kind': kind, 'abstained': True,
                'message': 'I could not find supporting passages for this topic in the selected '
                           'course material, so there is nothing to draw from. Check the subject '
                           'and year, or ask for the relevant chapter to be indexed.'}

    model = settings.LLM_DIAGRAM_MODEL or settings.LLM_MAIN_MODEL
    raw = await generate_text(model, diagram_prompt(build_context(hits), topic, board, level,
                                                    subject, kind))
    code, count, problems, notes = _render(raw, kind, topic)

    # Repair only when recovery was too thin to show, not merely imperfect.
    if count < MIN_NODES:
        try:
            repaired = await generate_text(
                model, diagram_repair_prompt(_split(raw)[0],
                                             problems or ['too few nodes'], kind))
            code2, count2, _, notes2 = _render(repaired, kind, topic)
            if count2 > count:
                code, count = code2, count2
                notes = notes or notes2
        except GenerationUnavailable:
            pass

    if count < MIN_NODES:
        return {'mermaid': '', 'notes': '', 'sources': [], 'kind': kind, 'abstained': True,
                'message': 'The retrieved passages did not contain enough connected structure to '
                           'draw this diagram. Try a narrower topic, or a different diagram type.'}

    return {
        'mermaid': code,
        'notes': notes,
        'kind': kind,
        'nodes': count,
        'abstained': False,
        'repaired': bool(problems),
        'sources': [{'source': h.get('source', 'unknown'), 'page': h.get('page', '?')}
                    for h in hits],
    }
