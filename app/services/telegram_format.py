"""Render an answer for Telegram.

The web client renders Markdown and LaTeX properly. Telegram does neither: a
message is plain text unless a parse_mode is set, and MarkdownV2 demands that
roughly eighteen characters be escaped, which a generated answer full of
brackets, underscores and backslashes fails constantly. Sending the raw answer
therefore delivered literal "**Step 1**" and "\\frac{1}{f}" to students.

The approach here is to send plain text and do the rendering ourselves:
Markdown emphasis is stripped, headings and list markers become typographic
bullets, and LaTeX is converted to Unicode mathematics. Nothing is escaped
because nothing is parsed, so no answer can break the message.

Messages are then split on paragraph boundaries rather than at a fixed offset,
so a formula or a numbered step is never cut in half.
"""
import re

LIMIT = 3500

_GREEK = {
    'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ', 'Delta': 'Δ',
    'epsilon': 'ε', 'zeta': 'ζ', 'eta': 'η', 'theta': 'θ', 'Theta': 'Θ',
    'kappa': 'κ', 'lambda': 'λ', 'Lambda': 'Λ', 'mu': 'μ', 'nu': 'ν',
    'xi': 'ξ', 'pi': 'π', 'Pi': 'Π', 'rho': 'ρ', 'sigma': 'σ', 'Sigma': 'Σ',
    'tau': 'τ', 'phi': 'φ', 'Phi': 'Φ', 'chi': 'χ', 'psi': 'ψ', 'omega': 'ω',
    'Omega': 'Ω',
}

_SYMBOL = {
    'times': '×', 'cdot': '·', 'div': '÷', 'pm': '±', 'mp': '∓',
    'leq': '≤', 'le': '≤', 'geq': '≥', 'ge': '≥', 'neq': '≠', 'ne': '≠',
    'approx': '≈', 'equiv': '≡', 'propto': '∝', 'infty': '∞',
    'rightarrow': '→', 'to': '→', 'leftarrow': '←', 'Rightarrow': '⇒',
    'leftrightarrow': '↔', 'partial': '∂', 'nabla': '∇', 'int': '∫',
    'sum': 'Σ', 'prod': 'Π', 'degree': '°', 'circ': '°', 'angle': '∠',
    'perp': '⊥', 'parallel': '∥', 'therefore': '∴', 'because': '∵',
}

_SUP = str.maketrans('0123456789+-=()n', '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ')
_SUB = str.maketrans('0123456789+-=()', '₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎')


def latex_to_text(fragment: str) -> str:
    """Convert a LaTeX fragment to readable Unicode mathematics."""
    out = fragment
    # Nested fractions are resolved innermost-first so the braces stay balanced.
    for _ in range(4):
        new = re.sub(r'\\(?:d|t)?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}', r'(\1)/(\2)', out)
        if new == out:
            break
        out = new
    out = re.sub(r'\\sqrt\s*\{([^{}]*)\}', r'√(\1)', out)
    out = re.sub(r'\\text\s*\{([^{}]*)\}', r'\1', out)
    out = re.sub(r'\\mathrm\s*\{([^{}]*)\}', r'\1', out)
    out = re.sub(r'\\left\s*([([{|.])', lambda m: '' if m.group(1) == '.' else m.group(1), out)
    out = re.sub(r'\\right\s*([)\]}|.])', lambda m: '' if m.group(1) == '.' else m.group(1), out)

    def _greek(match):
        return _GREEK.get(match.group(1), _SYMBOL.get(match.group(1), match.group(1)))

    out = re.sub(r'\\([A-Za-z]+)', _greek, out)

    # Superscripts and subscripts, braced or single-character.
    def _sup(match):
        body = match.group(1) or match.group(2)
        mapped = body.translate(_SUP)
        return mapped if all(c in '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ' for c in mapped) else f'^{body}'

    def _sub(match):
        body = match.group(1) or match.group(2)
        mapped = body.translate(_SUB)
        return mapped if all(c in '₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎' for c in mapped) else f'_{body}'

    out = re.sub(r'\^\{([^{}]*)\}|\^(\w)', _sup, out)
    out = re.sub(r'_\{([^{}]*)\}|_(\w)', _sub, out)

    out = out.replace('\\\\', ' ').replace('\\,', ' ').replace('\\;', ' ')
    out = out.replace('\\!', '').replace('\\quad', '  ').replace('\\qquad', '    ')
    out = out.replace('{', '').replace('}', '')
    return re.sub(r'[ \t]{2,}', ' ', out).strip()


def to_plain(text: str) -> str:
    """Strip Markdown and render LaTeX, leaving text safe to send unparsed."""
    if not text:
        return ''
    out = text.replace('\r\n', '\n')

    # Math first, so Markdown stripping cannot eat a backslash or an underscore
    # that belongs to a formula.
    out = re.sub(r'\\\[([\s\S]*?)\\\]', lambda m: '\n' + latex_to_text(m.group(1)) + '\n', out)
    out = re.sub(r'\\\(([\s\S]*?)\\\)', lambda m: latex_to_text(m.group(1)), out)
    out = re.sub(r'\$\$([\s\S]*?)\$\$', lambda m: '\n' + latex_to_text(m.group(1)) + '\n', out)
    out = re.sub(r'(?<!\$)\$(?!\$)([^\n$]*?)(?<!\$)\$(?!\$)', lambda m: latex_to_text(m.group(1)), out)

    # Fenced code: keep the contents, drop the fence.
    out = re.sub(r'```[a-zA-Z0-9_-]*\n([\s\S]*?)```', r'\1', out)
    out = re.sub(r'`([^`\n]*)`', r'\1', out)

    # Headings become their own emphasised line.
    out = re.sub(r'^\s{0,3}#{1,6}\s*(.+?)\s*#*\s*$', lambda m: m.group(1).upper(), out, flags=re.M)

    # Emphasis markers carry no meaning once unparsed.
    out = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', out, flags=re.S)
    out = re.sub(r'\*\*(.+?)\*\*', r'\1', out, flags=re.S)
    out = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'\1', out, flags=re.S)
    out = re.sub(r'(?<![\w_])__(.+?)__(?![\w_])', r'\1', out, flags=re.S)

    # Links: keep the label and the destination, drop the syntax.
    out = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', out)
    out = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', r'\1 (\2)', out)

    # Bullets become a typographic marker; numbered steps keep their number.
    out = re.sub(r'^\s{0,3}[-*+]\s+', '• ', out, flags=re.M)
    out = re.sub(r'^\s{0,3}>\s?', '', out, flags=re.M)
    out = re.sub(r'^\s*\|.*\|\s*$', lambda m: m.group(0).strip('| ').replace('|', ' · '), out, flags=re.M)
    out = re.sub(r'^\s*[-:| ]{6,}\s*$', '', out, flags=re.M)

    out = re.sub(r'\n{3,}', '\n\n', out)
    return out.strip()


def chunks(text: str, limit: int = LIMIT):
    """Split for delivery on paragraph, then line, then word boundaries."""
    text = text or ''
    if len(text) <= limit:
        return [text] if text else []
    parts, current = [], ''
    for block in text.split('\n\n'):
        candidate = block if not current else current + '\n\n' + block
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            parts.append(current)
            current = ''
        while len(block) > limit:
            cut = block.rfind('\n', 0, limit)
            if cut <= 0:
                cut = block.rfind(' ', 0, limit)
            if cut <= 0:
                cut = limit
            parts.append(block[:cut].rstrip())
            block = block[cut:].lstrip()
        current = block
    if current:
        parts.append(current)
    return [p for p in parts if p.strip()]


def for_telegram(text: str, limit: int = LIMIT):
    """Full pipeline: render, then split into deliverable messages."""
    return chunks(to_plain(text), limit)
