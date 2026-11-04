from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    APP_NAME: str = 'EduRAG'
    APP_ENV: str = 'development'
    HOST: str = '0.0.0.0'
    PORT: int = 8000
    DATA_DIR: str = 'data'
    DB_DIR: str = 'data/db'
    QUESTION_PAPERS_DIR: str = 'data/question_papers'
    SYLLABUS_DIR: str = 'data/syllabus'
    TEXTBOOKS_DIR: str = 'data/textbooks'
    EMBED_MODEL: str = 'sentence-transformers/all-MiniLM-L6-v2'
    VLLM_BASE_URL: str = 'http://localhost:11434'
    VECTOR_DIR: str = 'data/db/faiss'
    TOP_K: int = 5
    # Drop publisher front matter before grading; near-zero cost.
    FILTER_BOILERPLATE: bool = True
    # Corrective RAG: grade retrieved passages and re-retrieve when they are weak.
    ENABLE_CRAG: bool = True
    # Empty uses LLM_SMALL_MODEL. Grading quality bounds the whole corrective
    # layer, so it is configurable independently of the generator.
    CRAG_GRADER_MODEL: str = ''
    CRAG_KEEP_SCORE: float = 0.5      # keep a passage at or above this grade
    CRAG_CORRECT_SCORE: float = 0.9   # at or above this, retrieval needs no correction
    # Smallest number of passages to hand the generator when retrieval did
    # find candidates above the similarity floor. Guards against a harsh
    # grader rejecting everything and leaving the model to answer from
    # memory; does not affect abstention, which happens earlier.
    CRAG_MIN_EVIDENCE: int = 3
    # A passage is restored past the grader only if the dense index puts it
    # plainly on topic. Well above MIN_SIMILARITY, but a tuned operating point
    # rather than a separator: over the benchmark the answerable and
    # out-of-syllabus top-1 similarity distributions overlap (see the threshold
    # sweep in evaluation/retrieval_study.py). At 0.45 the floor declines to
    # restore for 11% of answerable questions and could restore for 4 of 24
    # out-of-syllabus ones, which the grader must then refuse on its own.
    CRAG_FLOOR_SIMILARITY: float = 0.45
    EMBED_THREADS: int = 4
    DOCUMENT_TOKENS: int = 500
    DOCUMENT_OVERLAP: int = 50
    CHUNK_SIZE: int = 700
    CHUNK_OVERLAP: int = 120
    MIN_SIMILARITY: float = 0.3
    PERSONA_MIN_SIMILARITY: float = 0.3
    STORAGE_KEY: str = ''
    RETENTION_DAYS: int = 30
    TEACHER_API_KEY: str = ''
    TELEGRAM_BOT_TOKEN: str = ''
    TELEGRAM_WEBHOOK_SECRET: str = ''
    PUBLIC_APP_URL: str = 'http://127.0.0.1:3000'
    WHISPER_MODEL: str = 'base'
    ENABLE_GTTS: bool = False
    RATE_LIMIT_PER_MINUTE: int = 60
    LLM_MAIN_MODEL: str = 'qwen2.5:3b'
    LLM_SOCRATIC_MODEL: str = 'qwen2.5:3b'
    LLM_SMALL_MODEL: str = 'qwen2.5:3b'
    # The 3B model cannot hold a 15-question blueprint in valid JSON; paper
    # generation needs the larger model even though it only partly fits in VRAM.
    LLM_MOCK_MODEL: str = 'qwen2.5:7b'
    # Diagram structure is harder than prose: the model must hold a whole
    # graph consistent at once. Routed separately so a stronger model can
    # draw while a local model answers. Empty falls back to LLM_MAIN_MODEL.
    LLM_DIAGRAM_MODEL: str = ''
    # Hybrid retrieval: fuse dense vectors with BM25 lexical scoring.
    # Dense embeddings generalise but blur exact tokens, so a query naming
    # 'Snell' or 'Le Chatelier' can rank a paraphrase above the passage
    # that defines it. Lexical scoring recovers those; fusion keeps both.
    ENABLE_HYBRID: bool = True
    # Reciprocal rank fusion constant, k in 1/(k + rank). Larger flattens
    # the contribution of top ranks.
    RRF_K: int = 60
    # Candidates drawn from each arm before fusion.
    HYBRID_CANDIDATES: int = 40
    # Grounding audit: read the generated answer back against the passages
    # it was given. This is where accuracy is actually lost -- a small model
    # handed correct passages still writes claims they do not support.
    ENABLE_GROUNDING: bool = True
    # Fraction of a claim's content words that must appear in the evidence
    # before it is treated as traceable. Deliberately low: the lexical pass
    # decides only what to examine, so false alarms cost a check, while a
    # miss reaches the student unflagged.
    GROUNDING_MIN_SUPPORT: float = 0.4
    # Put flagged claims to a model for an entailment verdict. Costs one
    # extra short generation, and only when something was flagged.
    ENABLE_GROUNDING_VERIFY: bool = True
    GROUNDING_VERIFY_LIMIT: int = 8
    GROUNDING_VERIFIER_MODEL: str = ''
    # CPU-only hosts generate in minutes, not seconds: an 8192-token mock paper
    # takes roughly half an hour at a few tokens per second.
    LLM_TIMEOUT_SECONDS: float = 3600.0
    # Empty keeps inference on the local Ollama runtime. Set only to reach an
    # OpenAI-compatible endpoint that requires bearer auth.
    LLM_API_KEY: str = ''
    # OpenRouter, used only to reach a judge from a different model family
    # than the generator. Kept separate from LLM_API_KEY so a judge
    # credential is never silently used for generation.
    OPENROUTER_API_KEY: str = ''
    # 'google' mints and refreshes an access token from application default
    # credentials instead of using the static LLM_API_KEY.
    LLM_AUTH: str = ''
    # Default backend for model names with no "ollama:"/"vertex:" prefix.
    # Any LLM_*_MODEL may carry a prefix to override this per task, so local
    # and cloud models can serve different tools at the same time.
    LLM_PROVIDER: str = 'ollama'
    # Full chat-completions URL, for providers whose path is not
    # "<base>/v1/chat/completions" (Vertex AI). Empty keeps the Ollama path.
    LLM_CHAT_URL: str = ''
    SUBJECTS: str = 'physics,chemistry,mathematics,biology'
    LEVELS: str = '1st,2nd'
    QUESTION_PAPER_BOARDS: str = 'cbse,ka'

    def subjects_list(self):
        return [s.strip() for s in self.SUBJECTS.split(',') if s.strip()]

    def levels_list(self):
        return [s.strip() for s in self.LEVELS.split(',') if s.strip()]

    def boards_list(self):
        return [s.strip() for s in self.QUESTION_PAPER_BOARDS.split(',') if s.strip()]

settings = Settings()
