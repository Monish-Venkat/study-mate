"""Remove repeated points from a generated answer.

A small local model asked for "five or more points" pads to the count by
saying the same thing again. Observed on a Biology question: one answer
restated the same six sentences about Euglena eleven times over, ninety-odd
bullets deep, until the token budget ran out mid-word.

The prompt now forbids it and the sampler penalises it, but neither is a
guarantee: a prompt is advice, and a repetition penalty acts on tokens rather
than on meaning, so a reworded restatement slips through both. This pass is
the guarantee. It runs on the finished text, before the grounding audit, so a
duplicate never reaches the audit, the page, Telegram or the voice surface.

What counts as a repeat is deliberately narrow. Only list items are compared,
because prose legitimately returns to a term and a derivation legitimately
restates an expression. Two items are the same point when their normalised
text matches, or when they are long and near-identical -- the model's
restatements differ only in connectives ("that it uses" / "which it uses"),
which no exact comparison would catch.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

# "1. ", "2) ", "- ", "* ", "• " at any indent.
ITEM = re.compile(r'^(\s*)(?:([0-9]+)[.)]|[-*•])\s+(.*)$')

# Below this length an item is too short to judge by similarity: "1. Yes" and
# "2. No" are 67% similar and both belong. Short items are dropped only on an
# exact normalised match.
SHORT = 40

# Two long items this similar are the same value point reworded. Measured on
# the observed loop: the restatements scored 0.94 to 1.00 against each other,
# and genuinely distinct points in the same answers scored below 0.78.
NEAR = 0.90

# Character similarity misses a restatement whose lead-in changed: "Euglena
# also has a nucleus, which contains its genetic material" against "It has a
# nucleus, which contains its genetic material" scores 0.88, under the bar,
# although one says nothing the other does not. Comparing word sets instead
# puts the pair at 0.89 of the shorter item, while genuinely distinct points
# from the same answers stay near 0.5 ("...called a flagellum" against
# "...called a chloroplast"), so the two tests catch different rewordings and
# neither has to be loosened to the point where it merges real content.
CONTAINED = 0.85


# A step that carries mathematics is compared only by exact equality. Two
# steps of a derivation differ by exactly the marks they earn: "for the first
# surface ... 1/v - 1/u = 1/f" and "for the second surface ... 1/v' - 1/u' =
# 1/f" are the two halves of the lens maker derivation, and they are 0.97
# similar as text. Normalising punctuation away made them identical, because
# the prime that distinguishes them is punctuation. Dropping the second one
# cost the student the second half of a 5-mark derivation, so similarity is
# not allowed to judge anything with a formula in it.
MATH = re.compile(r'\$|\\[a-zA-Z]')


def _key(text: str) -> str:
    """Normalise an item for comparison: case, punctuation and spacing."""
    return re.sub(r'[^a-z0-9 ]+', '', text.lower()).strip()


def _same_point(a: tuple[str, str], b: tuple[str, str]) -> bool:
    """Is b the same value point as a? Each item is (normalised key, raw text)."""
    a_key, a_raw = a
    b_key, b_raw = b
    if a_key == b_key and not MATH.search(a_raw) and not MATH.search(b_raw):
        return True
    # With a formula present, only the raw text repeating verbatim is a repeat.
    if MATH.search(a_raw) or MATH.search(b_raw):
        return ' '.join(a_raw.split()) == ' '.join(b_raw.split())
    if a_key == b_key:
        return True
    if len(a_key) < SHORT or len(b_key) < SHORT:
        return False
    if SequenceMatcher(None, a_key, b_key).ratio() >= NEAR:
        return True
    first, second = set(a_key.split()), set(b_key.split())
    smaller = min(len(first), len(second))
    return bool(smaller) and len(first & second) / smaller >= CONTAINED


def drop_repeats(answer: str) -> str:
    """Return the answer with repeated list items removed and numbering fixed.

    The first occurrence of a point is always the one kept, so the answer
    keeps the order the model chose to teach in.
    """
    if not answer:
        return answer

    lines = answer.split('\n')
    kept: list[str] = []
    seen: list[tuple[str, str]] = []
    for line in lines:
        match = ITEM.match(line)
        if not match:
            kept.append(line)
            continue
        body = match.group(3)
        item = (_key(body), body)
        if not item[0]:
            kept.append(line)
            continue
        if any(_same_point(item, previous) for previous in seen):
            continue
        seen.append(item)
        kept.append(line)

    return _renumber('\n'.join(kept))


def _renumber(text: str) -> str:
    """Make numbered items run 1, 2, 3 again after removals.

    Dropping item 7 of a list leaves "6. 8. 9.", which reads as a missing
    step rather than a removed duplicate. Each indent level counts separately,
    and a line of prose ends only the lists nested inside it.
    """
    lines = text.split('\n')
    counters: dict[int, int] = {}
    for i, line in enumerate(lines):
        match = ITEM.match(line)
        if not match:
            if line.strip():
                # Only a line further left than a list ends it. An indented
                # line belongs to the item above it -- a displayed equation
                # written as its own "$$" block is indented under its step,
                # and resetting on it restarted every derivation's numbering
                # at 1 after each formula.
                indent = len(line) - len(line.lstrip())
                counters = {d: n for d, n in counters.items() if d < indent}
            continue
        indent_text, number, body = match.groups()
        if number is None:
            continue
        depth = len(indent_text)
        counters[depth] = counters.get(depth, 0) + 1
        lines[i] = f'{indent_text}{counters[depth]}. {body}'
    return '\n'.join(lines)
