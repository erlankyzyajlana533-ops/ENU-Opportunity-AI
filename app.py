
import sqlite3
from pathlib import Path
from html import escape

import requests
import streamlit as st

from design import apply_design
from teacher_photos import get_teacher_photo
from ai_model import calculate_match, explain_match


from database import (
    initialize_database,
    create_database,
    get_students,
    get_teachers,
    get_student_requests,
    get_teacher_requests,
    send_request,
    update_request_status,
    create_requests_table,
    create_chat_table,
    send_chat_message,
    get_chat_messages,
    seed_demo_teachers,
)

# ==========================================
# ENU OPPORTUNITY AI
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "enu_opportunity.db"
API_URL = "https://enu-opportunity-ai.onrender.com"

st.set_page_config(
    page_title="ENU Opportunity AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


apply_design()
initialize_database()
seed_demo_teachers()

# ==========================================
# SESSION STATE
# ==========================================

DEFAULTS = {
    "current_user": None,
    "access_token": None,
    "active_page": "Басты бет",
    "show_matches": False,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ==========================================
# API FUNCTIONS
# ==========================================

def api_request(method, endpoint, data=None):
    headers = {}

    token = st.session_state.access_token

    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.request(
            method,
            f"{API_URL}{endpoint}",
            json=data,
            headers=headers,
            timeout=15,
        )

        try:
            result = response.json()
        except ValueError:
            result = {}

        if response.status_code >= 400:
            detail = result.get(
                "detail",
                f"API қатесі: {response.status_code}",
            )
            return False, detail

        return True, result

    except requests.RequestException:
        return False, (
            "API серверіне қосылу мүмкін болмады. "
            "FastAPI серверін тексеріңіз."
        )


def api_register(name, email, password, role):
    return api_request(
        "POST",
        "/auth/register",
        {
            "full_name": name,
            "email": email,
            "password": password,
            "role": role,
        },
    )


def api_me():
    return api_request("GET", "/auth/me")


def api_login(email, password):
    success, result = api_request(
        "POST",
        "/auth/login",
        {
            "email": email,
            "password": password,
        },
    )

    if not success:
        return False, result

    token = result.get("access_token")

    if not token:
        return False, "Сессия токені алынбады"

    st.session_state.access_token = token

    verified, user = api_me()

    if not verified:
        st.session_state.access_token = None
        return False, user

    st.session_state.current_user = user
    st.session_state.active_page = "Басты бет"

    return True, "Кіру сәтті орындалды"


def api_logout():
    if st.session_state.access_token:
        api_request("POST", "/auth/logout")

    st.session_state.access_token = None
    st.session_state.current_user = None
    st.session_state.active_page = "Басты бет"
    st.session_state.show_matches = False


# ==========================================
# DATABASE HELPERS
# ==========================================

def db_connection():
    conn = sqlite3.connect(
        str(DB_PATH),
        timeout=10,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_my_profile(user):
    profile_id = user.get("profile_id")

    if not profile_id:
        return None

    if user["role"] == "student":
        table = "students"
    elif user["role"] == "teacher":
        table = "teachers"
    else:
        return None

    with db_connection() as conn:
        row = conn.execute(
            f"SELECT * FROM {table} WHERE id = ?",
            (profile_id,),
        ).fetchone()

        return dict(row) if row else None



def save_my_profile(user, values):
    """Студент немесе оқытушы профилін сақтау."""

    if not user:
        raise ValueError("Жүйеге қайта кіріңіз")

    user_id = user.get("id")
    role = user.get("role")

    if not user_id:
        raise ValueError("Пайдаланушы ID табылмады")

    if role == "student":
        table = "students"
        fields = [
            "name",
            "major",
            "course",
            "skills",
            "interests",
        ]

    elif role == "teacher":
        table = "teachers"
        fields = [
            "name",
            "research",
            "articles",
            "projects",
        ]

    else:
        raise ValueError("Пайдаланушы рөлі белгісіз")

    for field in fields:
        if field not in values:
            raise ValueError(
                f"Міндетті өріс жоқ: {field}"
            )

    with db_connection() as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")

            account = conn.execute(
                """
                SELECT id, role, profile_id
                FROM users
                WHERE id = ? AND is_active = 1
                """,
                (user_id,),
            ).fetchone()

            if not account:
                raise ValueError(
                    "Аккаунт жергілікті базадан табылмады"
                )

            if account["role"] != role:
                raise ValueError(
                    "Аккаунт рөлі сәйкес келмейді"
                )

            profile_id = account["profile_id"]

            if profile_id:
                existing = conn.execute(
                    f"SELECT id FROM {table} WHERE id = ?",
                    (profile_id,),
                ).fetchone()

                if not existing:
                    raise ValueError(
                        "Байланыстырылған профиль табылмады"
                    )

                assignments = ", ".join(
                    f"{field} = ?" for field in fields
                )

                params = [values[field] for field in fields]
                params.append(profile_id)

                conn.execute(
                    f"""
                    UPDATE {table}
                    SET {assignments}
                    WHERE id = ?
                    """,
                    params,
                )

            else:
                columns = ", ".join(fields)
                placeholders = ", ".join(
                    "?" for _ in fields
                )

                params = [values[field] for field in fields]

                cursor = conn.execute(
                    f"""
                    INSERT INTO {table} ({columns})
                    VALUES ({placeholders})
                    """,
                    params,
                )

                profile_id = cursor.lastrowid

                conn.execute(
                    """
                    UPDATE users
                    SET profile_id = ?
                    WHERE id = ?
                    """,
                    (profile_id, user_id),
                )

            conn.commit()
            return profile_id

        except Exception:
            conn.rollback()
            raise  


def get_photo(name):
    try:
        return get_teacher_photo(name)
    except Exception:
        return None


def show_teacher_header(name, number=None):
    photo = get_photo(name)

    col1, col2 = st.columns(
        [1, 7],
        vertical_alignment="center",
    )

    with col1:
        if photo is not None:
            st.image(photo, width=85)
        else:
            st.markdown("### 👨‍🏫")

    with col2:
        prefix = f"{number}. " if number else ""
        st.markdown(
            f"### {prefix}{escape(str(name))}"
        )
        st.caption("Ғылыми жетекші")


# ==========================================
# LOGIN AND REGISTRATION
# ==========================================

# ==========================================
# DEMO LOGIN
# ==========================================

DEMO_ACCOUNTS = {
    "student": {
        "password": "Demo2026!",
        "role": "student",
        "full_name": "Демо студент"
    },
    "teacher": {
        "password": "Demo2026!",
        "role": "teacher",
        "full_name": "Демо оқытушы"
    }
}


def show_demo_login():
    st.markdown("### 🚀 Демо нұсқаға кіру")

    role = st.radio(
        "Рөлді таңдаңыз",
        ["🎓 Студент", "👨‍🏫 Оқытушы"],
        horizontal=True,
        key="demo_role"
    )

    login = (
        "student"
        if role == "🎓 Студент"
        else "teacher"
    )

    st.info(
        f"Логин: {login}\n\n"
        "Пароль: Demo2026!"
    )

    if st.button(
        "🚀 Демо ретінде кіру",
        type="primary",
        use_container_width=True
    ):
        account = DEMO_ACCOUNTS[login]

        st.session_state.current_user = {
            "id": -1 if login == "student" else -2,
            "username": login,
            "full_name": account["full_name"],
            "role": account["role"],
            "profile_id": None,
            "is_demo": True
        }

        st.session_state.active_page = "Басты бет"
        st.session_state.show_matches = False

        st.rerun()

def show_login():
    st.markdown(
        """
        <style>
        .auth-banner {
            background: linear-gradient(
                120deg, #061d50, #075bc5
            );
            color: white;
            border-radius: 20px;
            padding: 32px;
            text-align: center;
            margin-bottom: 25px;
        }

        .auth-banner h1,
        .auth-banner h2,
        .auth-banner p {
            color: white !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    
    left, center, right = st.columns([1, 2, 1])

    with center:
        with st.container(border=True):

            login_tab, register_tab = st.tabs([
                "🔐 Жүйеге кіру",
                "📝 Тіркелу",
            ])

            with login_tab:
                st.subheader("Қош келдіңіз!")

                with st.form("login_form"):
                    email = st.text_input(
                        "Электрондық пошта"
                    )

                    password = st.text_input(
                        "Құпиясөз",
                        type="password",
                    )

                    submitted = st.form_submit_button(
                        "🔵 Жүйеге кіру",
                        type="primary",
                        use_container_width=True,
                    )

                if submitted:
                    if not email or not password:
                        st.warning(
                            "Барлық өрістерді толтырыңыз"
                        )
                    else:
                        success, message = api_login(
                            email.strip().lower(),
                            password,
                        )

                        if success:
                            st.rerun()
                        else:
                            st.error(str(message))

            with register_tab:
                st.subheader("Жаңа аккаунт ашу")

                with st.form("register_form"):
                    name = st.text_input(
                        "Аты-жөніңіз"
                    )

                    email = st.text_input(
                        "Email",
                        key="register_email",
                    )

                    role_label = st.radio(
                        "Сіз кімсіз?",
                        ["Студент", "Оқытушы"],
                        horizontal=True,
                    )

                    password = st.text_input(
                        "Құпиясөз",
                        type="password",
                        key="register_password",
                    )

                    confirm = st.text_input(
                        "Құпиясөзді қайталаңыз",
                        type="password",
                    )

                    submitted = st.form_submit_button(
                        "📝 Тіркелу",
                        type="primary",
                        use_container_width=True,
                    )

                if submitted:
                    if not all([
                        name.strip(),
                        email.strip(),
                        password,
                        confirm,
                    ]):
                        st.warning(
                            "Барлық өрістерді толтырыңыз"
                        )

                    elif len(password) < 12:
                        st.warning(
                            "Құпиясөз кемінде 12 таңба "
                            "болуы керек"
                        )

                    elif password != confirm:
                        st.error(
                            "Құпиясөздер сәйкес келмейді"
                        )

                    else:
                        role = (
                            "student"
                            if role_label == "Студент"
                            else "teacher"
                        )

                        success, result = api_register(
                            name.strip(),
                            email.strip().lower(),
                            password,
                            role,
                        )

                        if success:
                            st.success(
                                "Тіркелу сәтті аяқталды! "
                                "Енді жүйеге кіріңіз."
                            )
                        else:
                            st.error(str(result))

            st.divider()

            st.caption(
                "SMART.ENU ресми кіру жүйесі "
                "әзірге қосылмаған."
            )

    show_demo_login()
    st.divider()
# ==========================================
# RESEARCH PLATFORMS
# ==========================================

RESEARCH_PLATFORMS = [
    (
        "Scopus",
        "scopus.com",
        "Ғылыми мақалалар мен дәйексөздер",
        "https://www.scopus.com/",
    ),
    (
        "Web of Science",
        "webofscience.com",
        "Ғылыми жарияланымдарды талдау",
        "https://www.webofscience.com/",
    ),
    (
        "Google Scholar",
        "scholar.google.com",
        "Ғылыми мақалаларды іздеу",
        "https://scholar.google.com/",
    ),
    (
        "ORCID",
        "orcid.org",
        "Зерттеушінің жеке идентификаторы",
        "https://orcid.org/",
    ),
    (
        "GitHub",
        "github.com",
        "Бағдарламалық жобалар",
        "https://github.com/",
    ),
    (
        "arXiv",
        "arxiv.org",
        "Ғылыми препринттер",
        "https://arxiv.org/",
    ),
    (
        "IEEE Xplore",
        "ieeexplore.ieee.org",
        "Инженерлік және IT зерттеулер",
        "https://ieeexplore.ieee.org/",
    ),
    (
        "ResearchGate",
        "researchgate.net",
        "Ғылыми қауымдастық",
        "https://www.researchgate.net/",
    ),
    (
        "DOAJ",
        "doaj.org",
        "Ашық ғылыми журналдар",
        "https://doaj.org/",
    ),
]


PROJECT_DIRECTIONS = [
    (
        "🤖 Жасанды интеллект",
        "Машиналық оқыту және нейрондық желілер",
    ),
    (
        "📊 Data Science",
        "Деректерді талдау және болжау",
    ),
    (
        "🔐 Киберқауіпсіздік",
        "Ақпарат пен желілерді қорғау",
    ),
    (
        "🌐 IoT",
        "Ақылды құрылғылар және сенсорлар",
    ),
    (
        "🎓 EdTech",
        "Білім берудегі цифрлық технологиялар",
    ),
    (
        "🦾 Робототехника",
        "Роботтарды бағдарламалау",
    ),
]


# ==========================================
# RESEARCH RESOURCES UI
# ==========================================

def show_research_resources():
    st.subheader("🔬 Ғылыми зерттеу кеңістігі")

    st.caption(
        "Ғылыми платформалар мен зерттеу ресурстары"
    )

    tab1, tab2 = st.tabs([
        "🌐 Ғылыми платформалар",
        "🚀 Жоба бағыттары",
    ])

    with tab1:
        st.write(
            "Ғылыми мақалаларды іздеуге, "
            "зерттеуші профилін дамытуға және "
            "жобаларды жариялауға арналған ресурстар."
        )

        for start in range(
            0, len(RESEARCH_PLATFORMS), 3
        ):
            columns = st.columns(3)

            for col, item in zip(
                columns,
                RESEARCH_PLATFORMS[start:start + 3],
            ):
                name, domain, description, url = item

                with col:
                    with st.container(border=True):
                        logo = (
                            "https://www.google.com/"
                            "s2/favicons?domain="
                            f"{domain}&sz=128"
                        )

                        st.markdown(
                            f"""
                            <div style="
                                height:110px;
                                display:flex;
                                align-items:center;
                                justify-content:center;
                                background:#eaf3ff;
                                border-radius:12px;
                            ">
                                <img
                                    src="{logo}"
                                    width="65"
                                    alt="{escape(name)}"
                                >
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        st.markdown(f"### {name}")
                        st.caption(description)

                        with st.popover(
                            "📖 Толық ақпарат",
                            use_container_width=True,
                        ):
                            st.write(description)

                            st.link_button(
                                "🌐 Ресми сайт",
                                url,
                                use_container_width=True,
                            )

    with tab2:
        for start in range(
            0, len(PROJECT_DIRECTIONS), 3
        ):
            columns = st.columns(3)

            for col, item in zip(
                columns,
                PROJECT_DIRECTIONS[start:start + 3],
            ):
                with col:
                    with st.container(border=True):
                        st.markdown(f"### {item[0]}")
                        st.write(item[1])


# ==========================================
# STUDENT PROFILE
# ==========================================
st.session_state.show_matches = True

# ==========================================
# DEMO PROFILE STORAGE
# ==========================================
def save_demo_profile(user, values):
    profile = {
        "id": 1,
        "name": values.get("name", ""),
        "major": values.get("major", ""),
        "course": values.get("course", 1),
        "skills": values.get("skills", ""),
        "interests": values.get("interests", "")
    }

    st.session_state.demo_student = profile
    return profile["id"]


def get_demo_profile():
    return st.session_state.get("demo_student")

def show_student_profile(user):
    st.subheader("📋 Менің профилім")

    profile = get_my_profile(user)

    if profile is None:
        st.info(
            "Ғылыми жетекші табу үшін "
            "профиліңізді толтырыңыз."
        )

    with st.form("student_profile_form"):
        name = st.text_input(
            "Аты-жөні",
            value=(
                profile["name"]
                if profile
                else user["full_name"]
            ),
        )

        major = st.text_input(
            "Мамандығы",
            value=(
                profile.get("major") or ""
                if profile else ""
            ),
        )

        course = st.number_input(
            "Курс",
            min_value=1,
            max_value=8,
            value=(
                int(profile.get("course") or 1)
                if profile else 1
            ),
        )

        skills = st.text_area(
            "Дағдылар",
            value=(
                profile.get("skills") or ""
                if profile else ""
            ),
            placeholder="Python, Machine Learning",
        )

        interests = st.text_area(
            "Ғылыми қызығушылықтар",
            value=(
                profile.get("interests") or ""
                if profile else ""
            ),
            placeholder="AI, Data Science, IoT",
        )

        submitted = st.form_submit_button(
            "💾 Профильді сақтау",
            type="primary",
        )
        if submitted:
            if not name.strip():
                st.warning("Аты-жөніңізді енгізіңіз")
                return

        try:
            profile_id = save_demo_profile(
                user,
                {
                    "name": name.strip(),
                    "major": major.strip(),
                    "course": int(course),
                    "skills": skills.strip(),
                    "interests": interests.strip(),
                },
            )

            st.session_state.current_user[
                "profile_id"
            ] = profile_id

            st.session_state.show_matches = True

            st.success("✅ Демо профиль сақталды!")
            st.rerun()

        except Exception as error:
            st.error(f"Сақтау қатесі: {error}")



# ==========================================
# TEACHER PROFILE
# ==========================================

def show_teacher_profile(user):
    st.subheader("📋 Оқытушы профилі")

    profile = get_my_profile(user)

    if profile:
        show_teacher_header(profile["name"])

    with st.form("teacher_profile_form"):
        name = st.text_input(
            "Аты-жөні",
            value=(
                profile["name"]
                if profile
                else user["full_name"]
            ),
        )

        research = st.text_area(
            "Ғылыми бағыттары",
            value=(
                profile.get("research") or ""
                if profile else ""
            ),
        )

        articles = st.text_area(
            "Ғылыми мақалалары",
            value=(
                profile.get("articles") or ""
                if profile else ""
            ),
        )

        projects = st.text_area(
            "Ғылыми жобалары",
            value=(
                profile.get("projects") or ""
                if profile else ""
            ),
        )

        submitted = st.form_submit_button(
            "💾 Профильді сақтау",
            type="primary",
        )

    if submitted:
        if not name.strip():
            st.warning("Аты-жөніңізді енгізіңіз")
            return

        try:
            profile_id = save_my_profile(
                user,
                {
                    "name": name.strip(),
                    "research": research.strip(),
                    "articles": articles.strip(),
                    "projects": projects.strip(),
                },
            )

            st.session_state.current_user[
                "profile_id"
            ] = profile_id

            st.success("Профиль сақталды!")
            st.rerun()

        except Exception as error:
            st.error(f"Сақтау қатесі: {error}")


# ==========================================
# AI MATCHING
# ==========================================

def show_student_matches(student):
    teachers = get_teachers()

    if not teachers:
        st.warning("Оқытушылар базасы бос")
        return

    student_text = (
        f"{student.get('interests') or ''}. "
        f"{student.get('skills') or ''}"
    )

    results = []

    with st.spinner("🤖 ЖИ сәйкестікті есептеуде..."):
        for teacher in teachers:
            teacher_text = (
                f"{teacher.get('research') or ''}. "
                f"{teacher.get('articles') or ''}. "
                f"{teacher.get('projects') or ''}"
            )

            if not teacher_text.strip(" ."):
                continue

            score = calculate_match(
                student_text,
                teacher_text,
            )

            explanation = explain_match(
                student_text,
                teacher_text,
            )

            results.append(
                (teacher, float(score), explanation)
            )

    results.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    st.subheader("🤖 ЖИ сәйкестендіру нәтижелері")

    for index, item in enumerate(
        results[:3],
        start=1,
    ):
        teacher, score, explanation = item

        with st.container(border=True):
            show_teacher_header(
                teacher["name"],
                index,
            )

            st.metric(
                "Мағыналық ұқсастық",
                f"{score:.1f}%",
            )

            st.progress(
                max(0.0, min(1.0, score / 100))
            )

            st.write(
                "**🔬 Ғылыми бағыты:**",
                teacher.get("research")
                or "Көрсетілмеген",
            )

            st.write(
                "**📚 Жобалары:**",
                teacher.get("projects")
                or "Көрсетілмеген",
            )

            with st.expander(
                "💡 Неліктен ұсынылды?"
            ):
                st.write(explanation)

            message = st.text_area(
                "Ғылыми жетекшіге хабарлама",
                key=(
                    f"msg_{student['id']}_"
                    f"{teacher['id']}"
                ),
            )

            if st.button(
                "📨 Өтінім жіберу",
                key=(
                    f"send_{student['id']}_"
                    f"{teacher['id']}"
                ),
                type="primary",
            ):
                if not message.strip():
                    st.warning("Хабарлама жазыңыз")
                else:
                    success = send_request(
                        student["id"],
                        teacher["id"],
                        message.strip(),
                    )

                    if success:
                        st.success("Өтінім жіберілді!")
                    else:
                        st.info(
                            "Бұл оқытушыға күтілудегі "
                            "өтінім бар."
                        )


# ==========================================
# PRIVATE CHAT
# ==========================================

def show_chat(request_id, role, teacher_name):
    st.markdown("### 💬 Жеке чат")

    show_teacher_header(teacher_name)

    if st.button(
        "🔄 Жаңарту",
        key=f"refresh_{role}_{request_id}",
    ):
        st.rerun()

    messages = get_chat_messages(request_id)

    with st.container(height=350, border=True):
        for msg in messages:
            sender = msg["sender_role"]

            avatar = "🎓"

            if sender == "Оқытушы":
                avatar = (
                    get_photo(teacher_name)
                    or "👨‍🏫"
                )

            with st.chat_message(
                "user"
                if sender == role
                else "assistant",
                avatar=avatar,
            ):
                st.caption(sender)
                st.write(msg["message"])
                st.caption(str(msg["created_at"]))

    with st.form(
        f"chat_{role}_{request_id}",
        clear_on_submit=True,
    ):
        message = st.text_area(
            "Хабарлама",
            placeholder="Хабарламаңызды жазыңыз...",
        )

        submitted = st.form_submit_button(
            "📤 Жіберу"
        )

    if submitted:
        if not message.strip():
            st.warning("Хабарлама бос")

        elif send_chat_message(
            request_id,
            role,
            message.strip(),
        ):
            st.rerun()

        else:
            st.error("Хабарлама жіберілмеді")


# ==========================================
# STUDENT DASHBOARD
# ==========================================


# ==========================================
# STUDENT DASHBOARD
# ==========================================

def show_student_dashboard():
    user = st.session_state.current_user

    st.header("🎓 Студент кабинеті")

    # Студент профилі
    show_student_profile(user)

    # Сақталған профильді алу
    try:
        student = get_demo_profile()
    except Exception as error:
        st.error(f"Профильді алу қатесі: {error}")
        return

    if student is None:
        st.info(
            "Ғылыми жетекшілерді көру үшін "
            "алдымен профиліңізді сақтаңыз."
        )
        return

    st.divider()

    st.success("✅ Студент профилі дайын!")

    # Ғылыми жетекшілерді іздеу
    st.subheader("🤖 ЖИ ұсынған ғылыми жетекшілер")

    if st.button(
        "🔍 Маған сәйкес оқытушыларды табу",
        type="primary",
        use_container_width=True,
    ):
        st.session_state.show_matches = True

    if st.session_state.get("show_matches", False):
        try:
            show_student_matches(student)
        except Exception as error:
            st.error(
                f"Оқытушыларды іздеу қатесі: {error}"
            )

    st.divider()

    # Студенттің өтінімдері
    st.subheader("📨 Менің өтінімдерім")

    try:
        requests_list = get_student_requests(
            student["id"]
        )
    except Exception as error:
        st.error(
            f"Өтінімдерді алу қатесі: {error}"
        )
        return

    if not requests_list:
        st.info("Әзірге өтінімдер жоқ")

    for req in requests_list:
        with st.container(border=True):

            teacher_name = req["teacher_name"]

            show_teacher_header(teacher_name)

            st.write(
                "**Мәртебесі:**",
                req["status"],
            )

            if req["status"] == "Қабылданды":
                show_chat(
                    req["id"],
                    "Студент",
                    teacher_name,
                )

            elif req["status"] == "Күтуде":
                st.warning("Жауап күтілуде")

            else:
                st.error("Өтінім қабылданбады")



# ==========================================
# TEACHER DASHBOARD
# ==========================================

def show_teacher_dashboard():
    user = st.session_state.current_user

    st.header("👨‍🏫 Оқытушы кабинеті")

    show_teacher_profile(user)

    teacher = get_my_profile(user)

    if teacher is None:
        return

    st.divider()
    st.subheader("📥 Маған келген өтінімдер")

    requests_list = get_teacher_requests(
        teacher["id"]
    )

    if not requests_list:
        st.info("Әзірге өтінімдер жоқ")

    for req in requests_list:
        with st.container(border=True):
            st.markdown(
                "### 🎓 "
                + escape(str(req["student_name"]))
            )

            st.write(
                "**Мамандығы:**",
                req["major"],
            )

            st.write(
                "**Курс:**",
                req["course"],
            )

            st.write(
                "**Дағдылары:**",
                req["skills"],
            )

            st.write(
                "**Қызығушылықтары:**",
                req["interests"],
            )

            st.write(
                "**Хабарлама:**",
                req["message"],
            )

            st.write(
                "**Мәртебесі:**",
                req["status"],
            )

            if req["status"] == "Күтуде":
                col1, col2 = st.columns(2)

                with col1:
                    if st.button(
                        "✅ Қабылдау",
                        key=f"accept_{req['id']}",
                    ):
                        update_request_status(
                            req["id"],
                            teacher["id"],
                            "Қабылданды",
                        )
                        st.rerun()

                with col2:
                    if st.button(
                        "❌ Қабылдамау",
                        key=f"reject_{req['id']}",
                    ):
                        update_request_status(
                            req["id"],
                            teacher["id"],
                            "Қабылданбады",
                        )
                        st.rerun()

            elif req["status"] == "Қабылданды":
                show_chat(
                    req["id"],
                    "Оқытушы",
                    teacher["name"],
                )


# ==========================================
# HOME PAGE
# ==========================================

def show_home(user):
    

    st.title("🎓 ENU Opportunity AI")

    st.subheader(
        "Студент пен ғылыми жетекшіні "
        "интеллектуалды сәйкестендіру жүйесі"
    )

    st.success(
        f"Қош келдіңіз, {user['full_name']}!"
    )

    st.write(
        "Жасанды интеллект арқылы ғылыми "
        "жетекшілерді табыңыз, өтінім жіберіңіз "
        "және ғылыми байланыс орнатыңыз."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "🎓 Студенттер",
            len(get_students()),
        )

    with col2:
        st.metric(
            "👨‍🏫 Оқытушылар",
            len(get_teachers()),
        )

    with col3:
        st.metric(
            "🤖 ЖИ моделі",
            "MiniLM",
        )

    st.divider()

    show_research_resources()

    st.divider()

    if user["role"] == "student":
        st.info(
            "Ғылыми жетекші табу үшін "
            "«Студент кабинеті» бөліміне өтіңіз."
        )

    else:
        st.info(
            "Өтінімдерді қарау үшін "
            "«Оқытушы кабинеті» бөліміне өтіңіз."
        )


# ==========================================
# SIDEBAR
# ==========================================

def show_sidebar(user):
    with st.sidebar:
        st.title("🎓 ENU Opportunity AI")
        st.caption("L.N. Gumilyov ENU")

        st.divider()

        st.write(
            f"👤 **{user['full_name']}**"
        )

        role = user["role"]

        st.caption(
            "Студент"
            if role == "student"
            else "Оқытушы"
        )

        pages = ["Басты бет"]

        if role == "student":
            pages.append("Студент кабинеті")

        elif role == "teacher":
            pages.append("Оқытушы кабинеті")

        current = st.session_state.active_page

        selected = st.radio(
            "Навигация",
            pages,
            index=(
                pages.index(current)
                if current in pages
                else 0
            ),
        )

        st.session_state.active_page = selected

        st.divider()

        if st.button(
            "🚪 Жүйеден шығу",
            use_container_width=True,
        ):
            api_logout()
            st.rerun()

        st.caption(
            "ENU Opportunity AI | Demo MVP"
        )

    return selected


# ==========================================
# MAIN
# ==========================================

def main():
    if not st.session_state.access_token:
        show_login()
        return

    success, user = api_me()

    if not success:
        api_logout()

        st.warning(
            "Сессия аяқталды. Қайта кіріңіз."
        )

        show_login()
        return

    st.session_state.current_user = user

    if user.get("role") not in (
        "student",
        "teacher",
    ):
        st.error("Рөлге рұқсат жоқ")
        return

    page = show_sidebar(user)

    if page == "Басты бет":
        show_home(user)

    elif (
        page == "Студент кабинеті"
        and user["role"] == "student"
    ):
        show_student_dashboard()

    elif (
        page == "Оқытушы кабинеті"
        and user["role"] == "teacher"
    ):
        show_teacher_dashboard()

    st.divider()

    st.caption(
        "ENU Opportunity AI | "
        "Ғылыми жетекшілерді интеллектуалды "
        "сәйкестендіру платформасы"
    )


if __name__ == "__main__":
    main()