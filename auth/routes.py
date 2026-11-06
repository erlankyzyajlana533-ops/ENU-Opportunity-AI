
import sqlite3

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
from pydantic import BaseModel, EmailStr, Field

from database import (
    create_user,
    get_user_by_email
)
from auth.security import (
    hash_password,
    verify_password
)
from auth.sessions import (
    create_session,
    get_session,
    delete_session
)


registration_router = APIRouter(
    prefix="/auth",
    tags=["Registration and Login"]
)

bearer = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer
    )
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Алдымен жүйеге кіріңіз"
        )

    user = get_session(credentials.credentials)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Сессия жарамсыз немесе мерзімі аяқталған"
        )

    return user


@registration_router.post("/register", status_code=201)
def register_user(data: RegisterRequest):

    if data.role not in ("student", "teacher"):
        raise HTTPException(
            status_code=400,
            detail="Рөл дұрыс емес"
        )

    if get_user_by_email(str(data.email)):
        raise HTTPException(
            status_code=409,
            detail="Бұл email тіркелген"
        )

    password_hash = hash_password(data.password)

    try:
        user_id = create_user(
            data.full_name,
            str(data.email),
            password_hash,
            data.role
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Бұл email тіркелген"
        )

    return {
        "message": "Тіркелу сәтті аяқталды",
        "user_id": user_id,
        "role": data.role
    }


@registration_router.post("/login")
def login_user(data: LoginRequest):

    user = get_user_by_email(str(data.email))

    if (
        user is None
        or not verify_password(
            data.password,
            user["password_hash"]
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Email немесе құпиясөз қате"
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=403,
            detail="Аккаунт белсенді емес"
        )

    token = create_session(user)

    return {
        "message": "Кіру сәтті орындалды",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
            "profile_id": user["profile_id"]
        }
    }


@registration_router.get("/me")
def current_user(user=Depends(require_user)):
    return user


@registration_router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    user=Depends(require_user)
):
    delete_session(credentials.credentials)

    return {
        "status": "success",
        "message": "Жүйеден шықтыңыз"
    }
