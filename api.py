
from fastapi import FastAPI
import sqlite3
from pathlib import Path

from integration_api import router as smart_enu_router
from auth.routes import registration_router

from auth.routes import registration_router

app = FastAPI(
    title="ENU Opportunity AI API",
    description="SMART.ENU интеграциясына арналған демонстрациялық REST API",
    version="1.0.0"
)

app.include_router(smart_enu_router)
app.include_router(registration_router)

app.include_router(registration_router)

DB_NAME = Path(__file__).resolve().parent / "enu_opportunity.db"


def get_count(table_name):
    allowed_tables = {"students", "teachers"}

    if table_name not in allowed_tables:
        raise ValueError("Белгісіз кесте")

    if not DB_NAME.exists():
        return 0

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        )
        return cursor.fetchone()[0]


@app.get("/")
def home():
    return {
        "project": "ENU Opportunity AI",
        "status": "working",
        "integration": "SMART.ENU demo API",
        "version": "1.0.0"
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "database_exists": DB_NAME.exists()
    }


@app.get("/api/statistics")
def statistics():
    return {
        "students_count": get_count("students"),
        "teachers_count": get_count("teachers"),
        "integration_status": "demo"
    }
  
# ==========================================
# ЖИ СӘЙКЕСТЕНДІРУ API
# ==========================================

from pydantic import BaseModel, Field
from ai_model import calculate_match, explain_match


class MatchRequest(BaseModel):
    student_interests: str = Field(
        min_length=1,
        max_length=3000,
        description="Студенттің ғылыми қызығушылықтары"
    )

    student_skills: str = Field(
        default="",
        max_length=3000,
        description="Студенттің дағдылары"
    )

    teacher_research: str = Field(
        min_length=1,
        max_length=3000,
        description="Оқытушының ғылыми бағыты"
    )

    teacher_projects: str = Field(
        default="",
        max_length=3000,
        description="Оқытушының ғылыми жобалары"
    )


@app.post("/api/match")
def match_student_teacher(data: MatchRequest):

    student_text = (
        f"{data.student_interests}. "
        f"{data.student_skills}"
    )

    teacher_text = (
        f"{data.teacher_research}. "
        f"{data.teacher_projects}"
    )

    score = calculate_match(
        student_text,
        teacher_text
    )

    explanation = explain_match(
        student_text,
        teacher_text
    )

    return {
        "similarity_score": score,
        "explanation": explanation,
        "model": "multilingual-MiniLM-L12-v2",
        "status": "success"
    }

from schemas import IntegrationStatusSchema


@app.get(
    "/api/integration/status",
    response_model=IntegrationStatusSchema
)
def integration_status():
    return {
        "project": "ENU Opportunity AI",
        "api_version": "1.0.0",
        "integration_status": "demo_ready",
        "smart_enu_connected": False
    }
from integration_api import router

app.include_router(router)