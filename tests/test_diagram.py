"""The diagram renderer is tested against the Mermaid a small model really writes.

Every case here is output shape observed from qwen2.5:3b, not invented: labels
containing parentheses, LaTeX left in a node, an arrow to a node that was never
defined, ragged mindmap indentation, a missing code fence, and the model's
explanation spilling into the diagram because it forgot to close one.

The contract is that the module never emits Mermaid it did not construct
itself, so a malformed model response degrades into a smaller diagram or an
abstention, never into a parser error on the student's screen.
"""
import re

import pytest

from app.services.diagram import MIN_NODES, _render
from app.services.grounding import audit, caveat


def render(raw, kind='process', topic='test topic'):
    return _render(raw, kind, topic)


def test_clean_flowchart_keeps_every_node_and_edge():
    code, count, _, notes = render('''```mermaid
flowchart TD
    N1["Incident ray strikes the surface"] --> N2["Ray bends at the boundary"]
    N2 -->|"because speed changes"| N3["Refracted ray in medium 2"]
```
How to read this
The chain shows refraction [1].''')
    assert count == 3
    assert code.startswith('flowchart TD')
    assert 'N2 -->|"because speed changes"| N3' in code
    assert notes.startswith('The chain shows refraction')


def test_unquoted_label_containing_parentheses_survives():
    """A label like "2F (far from lens)" must not take its node down with it."""
    code, count, _, _ = render('''```mermaid
flowchart TD
    A[Object placed beyond 2F (far from lens)] --> B[Rays converge]
    B --> C[Real, inverted image forms]
```''')
    assert count == 3
    assert 'far from lens' in code
    assert code.count('-->') == 2


def test_latex_is_rewritten_not_left_as_noise():
    code, _, _, _ = render('''```mermaid
flowchart TD
    S1["Start from $v = u + at$"] --> S2["Obtain s = ut + \\frac{1}{2}at^2"]
```''', kind='derivation')
    assert '(1/2)' in code
    assert '\\frac' not in code and '$' not in code and '{' not in code


def test_injected_directives_are_dropped():
    code, _, _, _ = render('''```mermaid
flowchart TD
    S1["Step one"] --> S2["Step two"]
    click S1 "http://example.invalid/steal" _blank
    style S1 fill:#f00
    S2 --> S3["Step three"]
```''')
    assert 'click' not in code and 'style' not in code and 'example.invalid' not in code
    assert code.count('-->') == 2


def test_arrow_to_undefined_node_is_discarded_not_rendered():
    code, count, problems, _ = render('''```mermaid
flowchart TD
    P1["Heating begins"] --> P2["Temperature rises"]
    P2 --> P9
    P2 --> P3["Phase change at constant T"]
```''')
    assert count == 3
    assert 'P9' not in code
    assert any('undefined' in p for p in problems)


def test_mindmap_siblings_stay_siblings_despite_ragged_indentation():
    code, count, _, _ = render('''```mermaid
mindmap
  root((Thermodynamics))
      First Law
            Internal energy [U]
            Heat (Q) and work (W)
    Second Law
        Entropy: always increases
                Carnot engine
```''', kind='concept_map')
    lines = code.splitlines()
    depth = {l.strip(): len(l) - len(l.lstrip(' ')) for l in lines[2:]}
    assert depth['Internal energy U'] == depth['Q and work W'], 'siblings were nested'
    assert depth['Carnot engine'] > depth['Entropy always increases']
    # Mindmap labels are unquoted, so grouping characters must be gone.
    for line in lines[2:]:
        assert not re.search(r'[\[\](){}"]', line), line
    assert count >= MIN_NODES


def test_root_written_with_single_parentheses_is_still_the_root():
    code, _, _, _ = render('''```mermaid
mindmap
  root(refraction through a prism)
    angles
      angle of incidence
      angle of emergence
```''', kind='concept_map')
    body = code.split('\n', 2)[2]
    assert code.splitlines()[1].strip() == 'root((refraction through a prism))'
    assert 'refraction through a prism' not in body, 'root repeated as its own branch'


def test_prose_cannot_leak_in_when_the_fence_is_missing():
    """Observed live: the explanation was drawn as a branch of the mindmap."""
    code, _, _, notes = render('''mindmap
  root((refraction through a prism))
    angles
      angle of incidence
      angle of emergence
How to read this: the structure shows the key concepts [1].''', kind='concept_map')
    assert 'How to read' not in code
    assert notes == 'the structure shows the key concepts [1].'


def test_identifier_style_names_are_readable_in_both_diagram_and_notes():
    code, _, _, notes = render('''```mermaid
mindmap
  root((prism))
    total_internal_reflection
      critical_angle
```

How to read this: the branch "total_internal_reflection" is the examinable one.''',
                               kind='concept_map')
    assert 'total internal reflection' in code and '_' not in code
    assert 'total internal reflection' in notes


def test_unusable_response_abstains_rather_than_rendering():
    code, count, problems, _ = render('I am not able to draw this diagram, sorry.')
    assert code == '' and count == 0 and problems


# --- grounding audit ------------------------------------------------------

HITS = [{'text': 'A lens forms an image of an object. The lens formula relates the object '
                 'distance and the image distance as 1/v - 1/u = 1/f, where f is the focal '
                 'length in metres.'},
        {'text': 'Magnification m equals image height over object height.'}]


def test_audit_separates_invention_miscitation_and_dangling_citations():
    answer = ('The lens formula relates object and image distance [1]. '
              'It is written 1/v - 1/u = 1/f, where f is the focal length in metres [1]. '
              'Magnification is image height over object height [1]. '
              'The refractive index of diamond is 2.42 at 24 degrees [2]. '
              'Snell law states n1 sin i equals n2 sin r [5].')
    report = audit(answer, HITS)

    def status_of(fragment):
        matches = [c['status'] for c in report['claims'] if fragment in c['text']]
        assert len(matches) == 1, f'{fragment!r} matched {len(matches)} claims'
        return matches[0]

    assert status_of('relates object and image distance') == 'supported'
    # A formula sentence reduces to very few content words; it must still be read.
    assert status_of('1/v - 1/u = 1/f') == 'supported'
    assert status_of('Magnification is image height') == 'miscited'
    assert status_of('refractive index of diamond') == 'unsupported'
    assert report['dangling_citations'] == [5]
    assert 'could not be traced' in caveat(report)


def test_headline_and_detail_numbers_describe_the_same_answer():
    """grounded_fraction once gave half credit for uncited claims, which let the
    badge report a percentage that its own subtitle contradicted."""
    report = audit('The lens formula relates object and image distance [1]. '
                   'The refractive index of diamond is 2.42 at 24 degrees [2].', HITS)
    total = len(report['claims'])
    traceable = total - report['counts']['unsupported']
    assert report['grounded_fraction'] == pytest.approx(traceable / total)
    assert report['cited_fraction'] == pytest.approx(report['counts']['supported'] / total)


def test_a_fully_grounded_answer_carries_no_caveat():
    report = audit('The lens formula is 1/v - 1/u = 1/f where f is the focal '
                   'length in metres [1].', HITS)
    assert report['counts']['unsupported'] == 0
    assert caveat(report) == ''
