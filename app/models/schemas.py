from pydantic import BaseModel, Field, ConfigDict
from typing import Literal
from datetime import date

class CourseRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    student_id: str = Field(min_length=1, max_length=100)
    subject: Literal['physics', 'chemistry', 'mathematics', 'biology']
    level: Literal['PUC1', 'PUC2'] = 'PUC2'
    board: Literal['KA', 'CBSE'] = 'KA'
    persona_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{24}$')

class AskRequest(CourseRequest):
    chapter: str | None = Field(default=None, max_length=200)
    question: str = Field(min_length=1, max_length=4000)
    language: Literal['en', 'hi', 'kn', 'ta', 'te', 'ml', 'mr', 'bn'] = 'en'
    depth: Literal['auto', 'concise', 'step_by_step', 'analogy', 'worked_example', 'socratic'] = 'auto'

class SocraticRequest(AskRequest):
    pass

class SummaryRequest(CourseRequest):
    chapter: str = Field(min_length=1, max_length=200)
    summary_type: Literal['bullet_points', 'detailed', 'quick_revision'] = 'bullet_points'

class DiagramRequest(CourseRequest):
    topic: str = Field(min_length=1, max_length=200)
    chapter: str | None = Field(default=None, max_length=200)
    kind: Literal['concept_map', 'process', 'derivation',
                  'comparison', 'classification'] = 'concept_map'

class PYQRequest(CourseRequest):
    pass

class MockRequest(CourseRequest):
    total_marks: int = Field(default=70, ge=10, le=200)

class PlannerRequest(CourseRequest):
    exam_date: date
    topics: list[str] = Field(default_factory=list, max_length=100)
    daily_minutes: int = Field(default=60, ge=30, le=480)

class ScoreRequest(CourseRequest):
    topic: str = Field(min_length=1, max_length=200)
    earned: float = Field(ge=0, le=200)
    possible: float = Field(gt=0, le=200)

class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    language: Literal['en', 'hi', 'kn', 'ta', 'te', 'ml', 'mr', 'bn'] = 'en'

class PersonaRegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    subject: Literal['physics', 'chemistry', 'mathematics', 'biology']
    url: str = Field(min_length=1, max_length=500)
    title: str = Field(default='', max_length=200)
    educator_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{24}$')
    language: Literal['en', 'hi', 'kn', 'ta', 'te', 'ml', 'mr', 'bn'] = 'en'
    transcript: str | None = Field(default=None, min_length=100, max_length=250000)
