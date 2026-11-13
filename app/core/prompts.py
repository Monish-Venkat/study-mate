"""Board-aware prompts.

Interpolating "Board=KA" tells a model nothing, so each board carries an
explicit description of its examination conventions and every prompt states the
answer shape the marking scheme rewards.
"""

BOARDS = {
    'KA': ('Karnataka PUC (Department of Pre-University Education). Papers use 1, 2, 3 and 5 mark '
           'questions; 5-mark items usually ask for a derivation, a labelled diagram or a numerical, '
           'and long questions carry internal choice. Marks are awarded per stated step, so the '
           'steps must be visible.'),
    'CBSE': ('CBSE senior secondary (NCERT). Papers use 1, 2, 3 and 5 mark questions with '
             'competency-based and assertion-reason items; answers are marked against a stepwise '
             'value-point scheme, so each distinct value point must appear separately.'),
}

LEVELS = {'PUC1': 'First year PUC / Class 11', 'PUC2': 'Second year PUC / Class 12'}


def _frame(board, level, subject):
    return (f'You are preparing a {LEVELS.get(level, level)} {subject} student for the '
            f'{BOARDS.get(board, board)}\n')


CITE = ('Cite evidence inline as [1], [2] immediately after the sentence it supports. '
        'Use only the numbered CONTEXT passages for facts. If the context does not cover part of '
        'the question, say plainly which part is missing instead of filling it from memory.\n')

# Formulas are rendered as mathematics in the web client and converted to plain
# symbols for Telegram, so the delimiters have to be predictable. Left to
# itself the model mixes \[ \], \( \), code fences and bare backslash commands,
# and the unrecognised ones reach the student as literal "\frac{1}{f}".
FORMULA = ('Write every formula as LaTeX: $...$ for an inline symbol or quantity, and $$...$$ on '
           'its own line for a displayed equation. For example $v = u + at$, or\n'
           '$$\\frac{1}{f} = (n-1)\\left(\\frac{1}{R_1} - \\frac{1}{R_2}\\right)$$\n'
           'Never write a backslash command outside these delimiters, and never put a formula in '
           'a code fence: it is rendered as mathematics, not as code. Define every symbol and '
           'give SI units.\n'
           # The rule above is read too broadly: "$Euglena$" came back in a
           # Biology answer, where the delimiters render an organism's name as
           # italic mathematics. Only quantities are mathematics.
           'Use these delimiters for mathematics only. An ordinary word, a name, a term '
           'of art or a unit spelled out is plain text, never wrapped in $.\n'
           # A biology answer tried to draw the fluid mosaic model with
           # $$\begin{array}{l}\text{Outer Layer:}\\ ...\end{array}$$. KaTeX
           # cannot parse it, so it rendered as red raw LaTeX and the unbalanced
           # $$ swallowed the sources line after it. Labelled diagrams come from
           # the figure strip, not from the model.
           'Never use a LaTeX environment: no \\begin{array}, \\begin{aligned}, \\begin{matrix} '
           'or any other \\begin{...}. Never use LaTeX to lay out a diagram, a table or a list — '
           'write those as ordinary numbered points.\n')

# Both boards mark per visible step, so an answer written as continuous prose
# throws away marks the same content would earn as separate points. The length
# of the list is set by what the question is worth, not by the model's mood.
POINTS = ('Structure the answer as a numbered list, one idea or one algebraic step per point, not '
          'as continuous prose: both boards award marks per visible step, so a point that is not '
          'separated is a mark the student does not get. Scale the list to what the question is '
          'worth. A 1 or 2 mark question takes a direct statement and at most two points. A 3 '
          'mark question takes three or four points. A 5 mark question takes five or more and '
          'must show the full derivation, the labelled stages or the complete description that '
          'earns the marks. Keep each point to one sentence or one step.\n'
          # A small model told to produce "five or more" points pads to the count
          # by restating what it has already said. An examiner awards a value point
          # once, so a padded list earns no extra marks; it just reads as a loop.
          # Observed: one answer repeated the same three sentences about Euglena
          # three times over.
          'Each point must state something the earlier points did not. Never restate an '
          'earlier point in different words to reach a count. If the context yields fewer '
          'distinct points than the mark value suggests, give the distinct ones and stop.\n')


def ask_prompt(context, question, board, level, subject):
    return (_frame(board, level, subject) + CITE + POINTS + FORMULA +
            'Open with a one-sentence direct answer, then the numbered points, covering in order: '
            'the explanation in the terminology the prescribed textbook uses, then the governing '
            'formula, then a worked example or application.\n'
            # The formula and worked-example slots are a template, not part of
            # what the student asked. Saying "the governing formula is not provided
            # in the context" under a biology diagram question spends a numbered
            # point on the absence of something nobody asked for. The citation
            # rule's instruction to name missing material is about the question,
            # not about these two slots.
            'The formula and the worked example belong only to questions that have them. '
            'Where the question or the context has no formula or no worked example, leave '
            'that part out silently: do not write a point saying it is absent, not provided '
            'or not applicable.\n'
            f'CONTEXT:\n{context}\nQUESTION: {question}')


def socratic_prompt(context, question, board, level, subject):
    return (_frame(board, level, subject) + CITE +
            'Do not give the final answer yet. Instead:\n'
            '1. Name the single concept the student must grasp first.\n'
            '2. Ask two or three short guiding questions, easiest first, each answerable from the context.\n'
            '3. Give one hint that points at the relevant idea without stating the conclusion.\n'
            '4. End by inviting the student to attempt the next step.\n'
            'Keep it under 200 words and encouraging in tone.\n'
            f'CONTEXT:\n{context}\nQUESTION: {question}')


def summary_prompt(context, chapter, board, level, subject, summary_type):
    shapes = {
        'bullet_points': 'tight bullets, one idea each, no sub-bullets',
        'detailed': 'short prose paragraphs grouped under headings',
        'quick_revision': 'a compact list a student can read in two minutes before the exam',
    }
    return (_frame(board, level, subject) + CITE +
            f'Produce revision notes on "{chapter}" as {shapes.get(summary_type, summary_type)}.\n'
            'Lead with the definitions and statements that are examinable, then formulas with symbols '
            'defined, then the distinctions examiners commonly test. Mark anything the context '
            'presents as commonly confused. Do not imply these notes cover the whole chapter: they '
            'cover only the retrieved passages.\n'
            f'CONTEXT:\n{context}')


def mock_prompt(context, subject, board, level, total_marks):
    return (_frame(board, level, subject) +
            f'Write a {total_marks}-mark practice paper for {subject} using only the CONTEXT.\n'
            'Rules: every question must be answerable from the context; label each with its marks and '
            'Bloom level; scale difficulty with marks, so 1-2 mark items recall, 3 mark items apply, '
            'and 5 mark items derive, analyse or evaluate; give long questions an internal choice of '
            'equal marks, counting only one alternative toward the total.\n'
            'Ask about the physics, chemistry, mathematics or biology itself. Never ask about the '
            'textbook as an object: its preface, structure, chapter titles or pedagogy are not '
            'examinable content.\n'
            'This is practice material, not a verified official paper.\n'
            f'CONTEXT:\n{context}')


def pyq_prompt(context, subject, board, level):
    return (_frame(board, level, subject) +
            f'Review these previous-year question excerpts for {subject}. Identify which topics recur '
            'and what form the questions take, and say what a student should therefore practise. '
            'State clearly that this is a limited excerpt review, not a complete five-year statistical '
            'trend analysis. Never invent frequencies, years or weightings that the context does not show.\n'
            f'CONTEXT:\n{context}')


def study_plan_prompt(context, topic, board, level, subject, minutes):
    """Turn one scheduled slot into specific work, instead of "Learn and practice"."""
    return (_frame(board, level, subject) +
            f'A student has a {minutes}-minute session on "{topic}".\n'
            'Using only the CONTEXT, return ONLY a JSON object:\n'
            '{"subtopics": ["..."], "focus": "...", "practice": "...", "checkpoint": "..."}\n'
            'subtopics: 2 to 4 specific named ideas from the context to study in this session, in '
            'teaching order, not the topic name repeated.\n'
            'focus: one sentence on what actually matters in these subtopics for the exam.\n'
            'practice: one concrete exercise the student should attempt, derived from the context.\n'
            'checkpoint: one question the student should be able to answer by the end of the session.\n'
            'If the context is too thin to name real subtopics, return an empty subtopics list.\n'
            f'CONTEXT:\n{context}')


# Diagram-based learning -----------------------------------------------------
# Each kind fixes the Mermaid grammar the model must write, because a grammar
# chosen per request is a grammar the validator cannot check.
DIAGRAM_KINDS = {
    'concept_map': ('mindmap', '',
                    'a concept map: the topic at the centre, its major ideas as branches, and the '
                    'specific facts, laws or quantities under each branch'),
    'process': ('flowchart', 'TD',
                'a process flow: the ordered stages of the phenomenon, one stage per node, each '
                'arrow labelled with what causes the next stage'),
    'derivation': ('flowchart', 'TD',
                   'a derivation chain: start from the stated premises or defining equation and '
                   'reach the final result, one algebraic step per node, each arrow labelled with '
                   'the substitution or assumption that licenses the step'),
    'comparison': ('flowchart', 'LR',
                   'a comparison: two concepts side by side, each with nodes for the properties on '
                   'which they are usually contrasted in the exam'),
    'classification': ('flowchart', 'TD',
                       'a classification tree: the general category at the top branching into its '
                       'types and sub-types, with the distinguishing criterion on each arrow'),
}

_FLOWCHART_RULES = (
    'Write Mermaid flowchart syntax and nothing else inside the code fence. The worked '
    'example below is from an unrelated topic: copy its shape and none of its words.\n'
    'flowchart {direction}\n'
    '  N1["water is heated at constant pressure"] --> N2["temperature rises to 100 C"]\n'
    '  N2 -->|"latent heat is absorbed"| N3["liquid turns to vapour"]\n'
    '  N3 --> N4["temperature holds steady until all of it boils"]\n'
    'Hard syntax rules, because the diagram is parsed mechanically:\n'
    '- Every node id is a letter followed by digits, like N1, N2. Define each id once with its '
    'label, then refer to it by id alone.\n'
    '- Every label is wrapped in double quotes inside square brackets.\n'
    '- Never put a double quote, a newline or a backtick inside a label.\n'
    '- Write formulas as plain text, like "v = u + at" or "delta H = -ve", never as LaTeX.\n'
    '- Use between 5 and 14 nodes.\n')

_MINDMAP_RULES = (
    'Write Mermaid mindmap syntax and nothing else inside the code fence. The worked '
    'example below is from an unrelated topic: copy its shape and none of its words.\n'
    'mindmap\n'
    '  root((photosynthesis))\n'
    '    light reaction\n'
    '      chlorophyll absorbs photons\n'
    '      ATP and NADPH are formed\n'
    '    dark reaction\n'
    '      Calvin cycle fixes carbon dioxide\n'
    'Hard syntax rules, because the diagram is parsed mechanically:\n'
    '- Exactly one root line, written as root((topic name)). Never repeat the topic name '
    'as a branch underneath the root.\n'
    '- Branch names must be real divisions of the topic, never placeholders.\n'
    '- Indent with spaces only, two spaces per level, at most three levels below the root.\n'
    '- Plain text labels only: no brackets, quotes, parentheses, colons or LaTeX.\n'
    '- Write formulas as plain text, like v = u + at.\n'
    '- Use between 6 and 16 nodes.\n')


def diagram_prompt(context, topic, board, level, subject, kind):
    grammar, direction, description = DIAGRAM_KINDS[kind]
    rules = (_MINDMAP_RULES if grammar == 'mindmap'
             else _FLOWCHART_RULES.replace('{direction}', direction))
    return (_frame(board, level, subject) +
            f'Draw {description}, for the topic "{topic}".\n'
            'Every node must come from the CONTEXT. Do not add stages, categories or steps the '
            'context does not state; a smaller correct diagram beats a fuller invented one.\n\n'
            + rules +
            '\nReturn the diagram inside a ```mermaid code fence and close that fence with ``` '
            'before writing anything else. After the fence, write 2 to 4 short '
            'lines under the heading "How to read this", explaining what the structure shows and '
            'naming the one relationship an examiner is most likely to test. Cite the context '
            'passages you used as [1], [2] in those lines.\n'
            f'\nCONTEXT:\n{context}')


def diagram_repair_prompt(code, problems, kind):
    grammar, direction, _ = DIAGRAM_KINDS[kind]
    rules = (_MINDMAP_RULES if grammar == 'mindmap'
             else _FLOWCHART_RULES.replace('{direction}', direction))
    return ('This Mermaid diagram failed to parse:\n\n' + code +
            '\n\nThe parser reported:\n' + '\n'.join(f'- {p}' for p in problems) +
            '\n\nRewrite it so it parses, keeping the same content.\n\n' + rules +
            '\nReturn only the corrected ```mermaid code fence.')


# Answer language -----------------------------------------------------------
#
# The selector was accepted by the API, echoed in the response and ignored by
# the model: asking in Hindi or Kannada returned 100% Latin-script English.
# The instruction did exist, but it sat at the FRONT of the prompt, roughly
# two thousand tokens before generation and followed by a wall of English
# rules and English textbook passages. A small local model simply continues in
# the language it has just been reading.
#
# So the directive is repeated here and appended AFTER the question, where it
# is the last thing read, and a matching line goes in the system prompt. The
# retrieved passages stay English regardless -- they are the evidence, not the
# answer -- so the instruction has to say explicitly that the source language
# is not the reply language.
LANGUAGES = {'en': 'English', 'hi': 'Hindi', 'kn': 'Kannada', 'ta': 'Tamil',
             'te': 'Telugu', 'ml': 'Malayalam', 'mr': 'Marathi', 'bn': 'Bengali'}

SCRIPTS = {'hi': 'Devanagari', 'kn': 'Kannada', 'ta': 'Tamil', 'te': 'Telugu',
           'ml': 'Malayalam', 'mr': 'Devanagari', 'bn': 'Bengali'}


def language_directive(code: str) -> str:
    """The closing instruction. Empty for English, which needs no restating."""
    name = LANGUAGES.get(code)
    if not name or code == 'en':
        return ''
    script = SCRIPTS.get(code, name)
    return (
        f'\n\nIMPORTANT: Write your entire answer in {name}, in the {script} script. '
        f'The CONTEXT passages above are in English because that is the language of '
        f'the prescribed textbook; they are the evidence, not the language of your '
        f'reply. Translate your explanation into {name}.\n'
        f'Keep unchanged, exactly as they appear: all mathematics and LaTeX between '
        f'$ delimiters, chemical formulae, SI units and the [1] [2] citation markers. '
        f'Where a technical term has no settled {name} equivalent, give the {name} '
        f'term with the English in brackets after it.\n'
        f'Do not answer in English.'
    )


def language_system(code: str) -> str:
    """A system-prompt line reinforcing the same thing."""
    name = LANGUAGES.get(code)
    if not name or code == 'en':
        return ''
    return (f' The student has asked for answers in {name}: reply only in {name}, '
            f'never in English, whatever language the supplied passages are in.')
