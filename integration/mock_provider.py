
"""
ENU Opportunity AI
Тестілік университеттік авторизация провайдері.

Бұл SMART.ENU-дың ресми API-і емес.
Тек жергілікті әзірлеу және демонстрация үшін.
"""

from copy import deepcopy

# Тестілік пайдаланушылар
MOCK_USERS = {
    "student_001": {
        "sub": "mock_student_001",
        "full_name": "Данияр Мұратбек",
        "email": "student001@example.test",
        "role": "student",
        "major": "Компьютерлік ғылымдар",
        "course": 4,
        "research_interests": [
            "Жасанды интеллект",
            "Машиналық оқыту",
            "Үлкен деректер"
        ]
    },

    "teacher_001": {
        "sub": "mock_teacher_001",
        "full_name": "Ерлан Мұратов",
        "email": "teacher001@example.test",
        "role": "teacher",
        "department": "Ақпараттық технологиялар",
        "research": [
            "Жасанды интеллект",
            "Машиналық оқыту"
        ]
    }
}


def get_mock_user(user_id: str):
    """Тестілік пайдаланушыны алу."""

    user = MOCK_USERS.get(user_id)

    if user is None:
        return None

    return deepcopy(user)


def get_mock_users():
    """Барлық тестілік пайдаланушыларды алу."""

    return deepcopy(MOCK_USERS)


def validate_mock_user(user_id: str):
    """Пайдаланушының бар-жоғын тексеру."""

    return user_id in MOCK_USERS
