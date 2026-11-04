# StudyMate
## Platform
Web. A Next.js frontend backed by the existing FastAPI project.
## Users and purpose
Students use their indexed PUC textbooks and question papers to ask questions, revise, and practice.
## Confirmed scope
The user requested a simple frontend with no login or signup and confirmed use of current PUC subjects and years. Review implementation against the supplied research paper; do not represent proposed modules or acceptance targets as achieved.
## Stack
Next.js requested by user. Existing Python, MiniLM, FAISS, Ollama backend retained.
## Design constraints
Simple task-focused interface. No authentication screens. Visual details delegated to implementation judgment.

## Implemented persona extension
YouTube lecture registration, accessible-caption import with supplied-text fallback, cached educator style profiles and optional style-conditioned tutoring are implemented. The local engine uses SQLite transcript vectors and Ollama; it does not claim the paper's full Qdrant/MongoDB stack or measured persona consistency.
