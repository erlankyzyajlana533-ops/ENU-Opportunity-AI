
from pydantic import BaseModel, Field
from typing import Optional, List


class StudentSchema(BaseModel):
    student_id: int
    full_name: str
    major: str
    course: int = Field(ge=1, le=4)
    skills: List[str] = []
    research_interests: List[str] = []


class TeacherSchema(BaseModel):
    teacher_id: int
    full_name: str
    research_areas: List[str] = []
    articles: List[str] = []
    projects: List[str] = []


class MatchResultSchema(BaseModel):
    student_id: int
    teacher_id: int
    similarity_score: float = Field(ge=0, le=100)
    explanation: str
    model: str


class IntegrationStatusSchema(BaseModel):
    project: str
    api_version: str
    integration_status: str
    smart_enu_connected: bool
