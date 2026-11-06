
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from integration_api import router as smart_enu_router
from auth.routes import registration_router
from schemas import IntegrationStatusSchema


# ==========================================
# ENU OPPORTUNITY AI - FASTAPI
# ==========================================

app = FastAPI(
    title="ENU Opportunity AI API",
    description=(
        "Студент пен ғылыми жетекшіні "
        "интеллектуалды сәйкестендіру платформасы. "
        "SMART.ENU интеграциясына арналған REST API."
    ),
    version="1.0.0"
)


# ==========================================
# ROUTERS
# ==========================================

app.include_router(smart_enu_router)
app.include_router(registration_router)


# ==========================================
# DATABASE
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
DB_NAME = BASE_DIR / "enu_opportunity.db"


def get_count(table_name: str) -> int:

    allowed_tables = {"students", "teachers"}

    if table_name not in allowed_tables:
        raise ValueError("Белгісіз кесте")

    if not DB_NAME.exists():
        return 0

    try:
        with sqlite3.connect(DB_NAME, timeout=10) as conn:

            cursor = conn.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            )

            result = cursor.fetchone()

            return result[0] if result else 0

    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="Деректер базасынан статистика алу мүмкін емес"
        ) from exc


# ==========================================
# HOME
# ==========================================

@app.get("/")
def home():

    return {
        "project": "ENU Opportunity AI",
        "status": "working",
        "integration": "SMART.ENU demo API",
        "version": "1.0.0",
        "documentation": "/docs"
    }


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/api/health")
def health():

    return {
        "status": "ok",
        "service": "ENU Opportunity AI API",
        "database_exists": DB_NAME.exists(),
        "version": "1.0.0"
    }


# ==========================================
# STATISTICS
# ==========================================

@app.get("/api/statistics")
def statistics():

    return {
        "students_count": get_count("students"),
        "teachers_count": get_count("teachers"),
        "integration_status": "demo"
    }


# ==========================================
# AI MATCHING REQUEST
# ==========================================

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


# ==========================================
# AI MATCHING API
# ==========================================

@app.post("/api/match")
def match_student_teacher(data: MatchRequest):

    # ЖИ моделі тек сұраныс келгенде импортталады.
    # Бұл сервердің бастапқы іске қосылуын жеңілдетеді.

    try:
        from ai_model import calculate_match, explain_match

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

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="ЖИ сәйкестендіру қызметі уақытша қолжетімсіз"
        ) from exc


# ==========================================
# SMART.ENU INTEGRATION STATUS
# ==========================================

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


# ==========================================
# LOCAL DEVELOPMENT
# ==========================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )
