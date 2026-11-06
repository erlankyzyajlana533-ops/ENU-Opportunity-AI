
# ==========================================
# ENU OPPORTUNITY AI
# SMART.ENU DEMO INTEGRATION API
# ==========================================

import os
import secrets

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from schemas import StudentSchema, TeacherSchema


# ==========================================
# 1. API ROUTER
# ==========================================

router = APIRouter(
    prefix="/api/v1",
    tags=["SMART.ENU Demo"]
)

security = HTTPBearer(auto_error=False)


# ==========================================
# 2. API TOKEN VERIFICATION
# ==========================================

def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        security
    )
):
    """
    SMART.ENU Demo API токенін тексеру.
    Бұл нақты SMART.ENU авторизациясы емес.
    """

    expected_token = os.getenv("ENU_API_TOKEN")

    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API токені бапталмаған"
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Авторизация токені қажет",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not secrets.compare_digest(
        credentials.credentials,
        expected_token
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен жарамсыз",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return True


# ==========================================
# 3. STUDENTS API
# ==========================================

@router.get(
    "/students",
    response_model=list[StudentSchema],
    summary="Студенттер тізімі"
)
def get_demo_students(
    authorized: bool = Depends(verify_token)
):
    """
    SMART.ENU интеграциясын тексеруге арналған
    демонстрациялық студент мәліметтері.
    """

    return [
        StudentSchema(
            student_id=1001,
            full_name="Demo Student",
            major="Computer Science",
            course=4,
            skills=[
                "Python",
                "Machine Learning"
            ],
            research_interests=[
                "Artificial Intelligence"
            ]
        )
    ]


# ==========================================
# 4. TEACHERS API
# ==========================================

@router.get(
    "/teachers",
    response_model=list[TeacherSchema],
    summary="Оқытушылар тізімі"
)
def get_demo_teachers(
    authorized: bool = Depends(verify_token)
):
    """
    SMART.ENU интеграциясын тексеруге арналған
    демонстрациялық оқытушы мәліметтері.
    """

    return [
        TeacherSchema(
            teacher_id=2001,
            full_name="Demo Teacher",
            research_areas=[
                "Artificial Intelligence"
            ],
            articles=[
                "Machine Learning Research"
            ],
            projects=[
                "AI Recommendation System"
            ]
        )
    ]


# ==========================================
# 5. API HEALTH CHECK
# ==========================================

@router.get(
    "/health",
    summary="API жұмысын тексеру"
)
def api_health(
    authorized: bool = Depends(verify_token)
):
    return {
        "status": "ok",
        "platform": "ENU Opportunity AI",
        "integration": "SMART.ENU Demo",
        "message": "Demo API жұмыс істеп тұр"
    }
