# StudyMate interface system

## Intent
A simple PUC study tool. Prioritize readable questions, course selection and useful responses. No account screens. Present only implemented tools; communicate dataset and service limitations truthfully.

## Tokens and type
Light theme: canvas #f7f8f5, white form/answer surfaces, ink #24362e, secondary #627068, green action #235c42, supporting green #e8f0e7, border #dce2db. DM Sans is self-hosted with @fontsource; Georgia supplies restrained serif headings. Controls use 7px radii and 12px panels. Avoid decorative images, gradients, metrics, or animation in this task-focused interface.

## Layout
Desktop left navigation 252px, topbar 78px, main horizontal padding 46px, primary form plus 248px help/status column. At 1500px and above the supporting column is 285px. At 1150px and below the sidebar is 220px, the supporting column moves below the form, and the help card is hidden. Under 700px navigation becomes horizontally scrollable, course controls use two columns with full-width subject, actions use full width, and supporting decoration is hidden.

## Behavior and accessibility
Semantic navigation, visible labels, keyboard focus and skip link. Errors use alerts; loading and index status use live status. Disable form controls, tool navigation and history selection during generation; keep refresh, clear and cancellation available. Markdown output has no raw HTML rendering. Reduced motion disables the loading rotation. Session answers remain in React memory and disappear on reload. Real dialogue persistence is not implemented.


## YouTube persona extension
A bordered persona panel sits above the study form, with a matching navigation shortcut. It provides subject-filtered educator selection, expandable lecture registration, caption-language selection, optional pasted transcript, progress/error states, and expandable profile/source details. Style reference links are separate from factual citations. The registration grid collapses to one column on mobile. It retains the guest workflow and existing colors, type and controls.
