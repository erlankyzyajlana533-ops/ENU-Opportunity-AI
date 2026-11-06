
import sqlite3
import re
from pathlib import Path
from datetime import datetime
from html import escape

import streamlit as st

# =====================================
# ENU OPPORTUNITY AI — DEMO MVP
# =====================================

st.set_page_config(
    page_title="ENU Opportunity AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_PATH = Path(__file__).resolve().parent / "enu_demo.db"
DEMO_PASSWORD = "Demo2026!"

# =====================================
# DESIGN
# =====================================

st.markdown("""
<style>
.stApp {
    background: linear-gradient(
        120deg, #e5f6ff, #f8fbff, #dce7ff
    );
}
[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg, #061b46, #1059af
    );
}
[data-testid="stSidebar"] * {
    color: white;
}
h1, h2, h3 {
    color: #102b57;
}
div.stButton > button[kind="primary"],
div.stFormSubmitButton > button[kind="primary"] {
    background: #ff4b52;
    color: white;
    border-radius: 10px;
    border: none;
}
div[data-testid="stMetric"] {
    background: rgba(255,255,255,0.7);
    padding: 15px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

# =====================================
# DATABASE
# =====================================

def connect():
    conn = sqlite3.connect(str(DB_PATH), timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=20000")
    return conn


TEACHERS = [
    (
        "Демо оқытушы — AI",
        "Жасанды интеллект, Machine Learning, Data Science, Python",
        "Машиналық оқыту әдістері",
        "Білім берудегі интеллектуалды жүйелер"
    ),
    (
        "Демо оқытушы — IoT",
        "IoT, Smart Farming, сенсорлар, Python",
        "Заттар интернеті технологиялары",
        "Ақылды жылыжай мониторингі"
    ),
    (
        "Демо оқытушы — EdTech",
        "EdTech, AI, білім беру, Python",
        "Білім беруді цифрландыру",
        "Инклюзивті білім беру платформасы"
    )
]


def init_db():
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            major TEXT DEFAULT '',
            course INTEGER DEFAULT 1,
            skills TEXT DEFAULT '',
            interests TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            research TEXT DEFAULT '',
            articles TEXT DEFAULT '',
            projects TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            teacher_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'Күтуде',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)

        for item in TEACHERS:
            conn.execute("""
                INSERT OR IGNORE INTO teachers
                (name, research, articles, projects)
                VALUES (?, ?, ?, ?)
            """, item)


init_db()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def get_teachers():
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM teachers ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]


def get_student(username):
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM students WHERE username=?",
            (username,)
        ).fetchone()
        return dict(row) if row else None


def save_student(username, values):
    with connect() as conn:
        conn.execute("""
            INSERT INTO students
            (username, name, major, course, skills, interests)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                name=excluded.name,
                major=excluded.major,
                course=excluded.course,
                skills=excluded.skills,
                interests=excluded.interests
        """, (
            username,
            values["name"],
            values["major"],
            values["course"],
            values["skills"],
            values["interests"]
        ))


def get_student_requests(student_id):
    with connect() as conn:
        rows = conn.execute("""
            SELECT r.*, t.name AS teacher_name
            FROM requests r
            JOIN teachers t ON t.id=r.teacher_id
            WHERE r.student_id=?
            ORDER BY r.id DESC
        """, (student_id,)).fetchall()
        return [dict(r) for r in rows]


def get_teacher_requests(teacher_id):
    with connect() as conn:
        rows = conn.execute("""
            SELECT r.*, s.name AS student_name,
                   s.major, s.course, s.skills, s.interests
            FROM requests r
            JOIN students s ON s.id=r.student_id
            WHERE r.teacher_id=?
            ORDER BY r.id DESC
        """, (teacher_id,)).fetchall()
        return [dict(r) for r in rows]


def send_request(student_id, teacher_id, message):
    with connect() as conn:
        existing = conn.execute("""
            SELECT id FROM requests
            WHERE student_id=? AND teacher_id=?
            AND status IN ('Күтуде', 'Қабылданды')
        """, (student_id, teacher_id)).fetchone()

        if existing:
            return False

        conn.execute("""
            INSERT INTO requests
            (student_id, teacher_id, message, status, created_at)
            VALUES (?, ?, ?, 'Күтуде', ?)
        """, (student_id, teacher_id, message, now()))
        return True


def update_status(request_id, teacher_id, status):
    if status not in ("Қабылданды", "Қабылданбады"):
        return

    with connect() as conn:
        conn.execute("""
            UPDATE requests SET status=?
            WHERE id=? AND teacher_id=?
            AND status='Күтуде'
        """, (status, request_id, teacher_id))


def get_messages(request_id):
    with connect() as conn:
        rows = conn.execute("""
            SELECT * FROM messages
            WHERE request_id=?
            ORDER BY id
        """, (request_id,)).fetchall()
        return [dict(r) for r in rows]


def send_message(request_id, sender, message, user):
    with connect() as conn:
        req = conn.execute("""
            SELECT r.status, r.teacher_id, s.username
            FROM requests r
            JOIN students s ON s.id=r.student_id
            WHERE r.id=?
        """, (request_id,)).fetchone()

        if not req or req["status"] != "Қабылданды":
            raise ValueError("Чат қолжетімсіз")

        if sender == "Студент":
            allowed = (
                user["role"] == "student"
                and user["username"] == req["username"]
            )
        else:
            allowed = (
                user["role"] == "teacher"
                and user["teacher_id"] == req["teacher_id"]
            )

        if not allowed:
            raise ValueError("Чатқа рұқсат жоқ")

        conn.execute("""
            INSERT INTO messages
            (request_id, sender, message, created_at)
            VALUES (?, ?, ?, ?)
        """, (request_id, sender, message, now()))


# =====================================
# SESSION
# =====================================

if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "show_matches" not in st.session_state:
    st.session_state.show_matches = False

if "open_teacher_requests" not in st.session_state:
    st.session_state.open_teacher_requests = False


# =====================================
# LOGIN
# =====================================

def show_login():
    st.title("🎓 ENU Opportunity AI")
    st.subheader(
        "Студент пен ғылыми жетекшіні "
        "интеллектуалды сәйкестендіру жүйесі"
    )
    st.info("🚀 Бірінші кезеңге арналған Demo MVP")

    left, center, right = st.columns([1, 2, 1])

    with center:
        with st.container(border=True):
            st.markdown("### 🔐 Демо жүйеге кіру")

            role = st.radio(
                "Рөлді таңдаңыз",
                ["🎓 Студент", "👨‍🏫 Оқытушы"],
                horizontal=True,
                key="enu_login_role"
            )

            teachers = get_teachers()
            teacher_id = None
            chosen = ""

            if role == "🎓 Студент":
                username = "student"
            else:
                chosen = st.selectbox(
                    "Оқытушы аккаунты",
                    [t["name"] for t in teachers],
                    key="enu_teacher_selection"
                )
                teacher_id = next(
                    t["id"] for t in teachers
                    if t["name"] == chosen
                )
                username = "teacher"

            st.caption("Демо аккаунт деректері")
            st.code(
                f"Логин: {username}\n"
                f"Құпиясөз: {DEMO_PASSWORD}"
            )

            with st.form("enu_login_form"):
                login = st.text_input(
                    "Логин",
                    value=username
                )
                password = st.text_input(
                    "Құпиясөз",
                    value=DEMO_PASSWORD,
                    type="password"
                )
                submitted = st.form_submit_button(
                    "🚀 Жүйеге кіру",
                    type="primary",
                    use_container_width=True
                )

            if submitted:
                if login.strip() != username:
                    st.error("Логин дұрыс емес")
                elif password != DEMO_PASSWORD:
                    st.error("Құпиясөз дұрыс емес")
                else:
                    is_student = role == "🎓 Студент"

                    st.session_state.current_user = {
                        "username": username,
                        "role": (
                            "student" if is_student
                            else "teacher"
                        ),
                        "teacher_id": teacher_id,
                        "full_name": (
                            "Демо студент" if is_student
                            else chosen
                        )
                    }
                    st.session_state.show_matches = False
                    st.rerun()

    st.caption(
        "Демонстрациялық аккаунттар. "
        "Нақты университеттік авторизация қосылмаған."
    )


# =====================================
# MATCHING ALGORITHM
# =====================================

ALIASES = {
    "machine learning": "ml",
    "машиналық оқыту": "ml",
    "data science": "data",
    "деректерді талдау": "data",
    "жасанды интеллект": "ai",
    "artificial intelligence": "ai",
    "заттар интернеті": "iot",
    "ақылды жылыжай": "iot",
    "smart farming": "iot",
    "білім беру": "edtech",
    "инклюзивті": "edtech"
}

STOP_WORDS = {
    "мен", "және", "үшін", "the", "and",
    "with", "бойынша", "туралы", "жоба"
}


def tokenize(value):
    value = str(value or "").lower()

    for original, replacement in ALIASES.items():
        value = value.replace(
            original, f" {replacement} "
        )

    words = re.findall(
        r"[a-zа-яәғқңөұүһі0-9+#]+",
        value
    )

    return {
        word for word in words
        if len(word) > 1 and word not in STOP_WORDS
    }


def calculate_match(student, teacher):
    student_text = " ".join([
        str(student.get("skills", "")),
        str(student.get("interests", ""))
    ])

    teacher_text = " ".join([
        str(teacher.get("research", "")),
        str(teacher.get("articles", "")),
        str(teacher.get("projects", ""))
    ])

    a = tokenize(student_text)
    b = tokenize(teacher_text)

    if not a:
        return 0.0, "Қызығушылықтар енгізілмеген."

    common = a.intersection(b)
    score = round(100 * len(common) / len(a), 1)

    if common:
        reason = (
            "Ортақ ғылыми бағыттар мен дағдылар: "
            + ", ".join(sorted(common))
        )
    else:
        reason = (
            "Тікелей ортақ кілт сөздер анықталмады. "
            "Ғылыми бағыттарын қосымша қарастыруға болады."
        )

    return score, reason


# =====================================
# CHAT
# =====================================

def show_chat(request_id, role, user):
    st.markdown("#### 💬 Жеке чат")

    if st.button(
        "🔄 Чатты жаңарту",
        key=f"refresh_{role}_{request_id}"
    ):
        st.rerun()

    messages = get_messages(request_id)

    with st.container(height=260, border=True):
        if not messages:
            st.info("Әзірге хабарламалар жоқ")

        for msg in messages:
            with st.chat_message(
                "user" if msg["sender"] == role
                else "assistant"
            ):
                st.caption(msg["sender"])
                st.write(msg["message"])
                st.caption(msg["created_at"])

    with st.form(
        f"chat_form_{role}_{request_id}",
        clear_on_submit=True
    ):
        message = st.text_input(
            "Хабарламаңызды жазыңыз"
        )
        submitted = st.form_submit_button("📤 Жіберу")

    if submitted:
        if message.strip():
            try:
                send_message(
                    request_id,
                    role,
                    message.strip(),
                    user
                )
                st.rerun()
            except ValueError as error:
                st.error(str(error))
        else:
            st.warning("Хабарлама бос болмауы керек")


# =====================================
# STUDENT PROFILE
# =====================================

def show_student_profile(user):
    profile = get_student(user["username"])

    st.subheader("📋 Студент профилі")

    with st.form("enu_student_profile"):
        name = st.text_input(
            "Аты-жөні",
            value=profile["name"] if profile else ""
        )
        major = st.text_input(
            "Мамандығы",
            value=profile["major"] if profile
            else "Информатика"
        )
        course = st.number_input(
            "Курс",
            min_value=1,
            max_value=8,
            value=int(profile["course"]) if profile else 4
        )
        skills = st.text_area(
            "Дағдылар",
            value=profile["skills"] if profile else "",
            placeholder="Python, Machine Learning, IoT"
        )
        interests = st.text_area(
            "Ғылыми қызығушылықтар",
            value=profile["interests"] if profile else "",
            placeholder="AI, Data Science, Smart Farming"
        )

        submitted = st.form_submit_button(
            "💾 Профильді сақтау",
            type="primary"
        )

    if submitted:
        if not name.strip():
            st.warning("Аты-жөніңізді енгізіңіз")
        else:
            save_student(user["username"], {
                "name": name.strip(),
                "major": major.strip(),
                "course": int(course),
                "skills": skills.strip(),
                "interests": interests.strip()
            })
            st.session_state.show_matches = True
            st.success("Профиль сақталды!")
            st.rerun()


# =====================================
# TEACHER MATCHES
# =====================================

def show_matches(student):
    st.subheader("🤖 Ұсынылған ғылыми жетекшілер")
    st.caption(
        "Сәйкестік пайызы ортақ кілт сөздер "
        "негізінде есептеледі. Демо алгоритм."
    )

    results = []

    for teacher in get_teachers():
        score, reason = calculate_match(student, teacher)
        results.append((teacher, score, reason))

    results.sort(
        key=lambda item: item[1],
        reverse=True
    )

    for index, (teacher, score, reason) in enumerate(
        results[:3], 1
    ):
        with st.container(border=True):
            st.markdown(
                f"### {index}. 👨‍🏫 {escape(teacher['name'])}"
            )

            st.metric("Сәйкестік", f"{score:.1f}%")
            st.progress(
                min(1.0, max(0.0, score / 100))
            )

            st.write(
                "**🔬 Ғылыми бағыты:**",
                teacher["research"]
            )
            st.write(
                "**📚 Зерттеулері:**",
                teacher["articles"]
            )
            st.write(
                "**🚀 Жобалары:**",
                teacher["projects"]
            )

            with st.expander("💡 Неліктен ұсынылды?"):
                st.write(reason)

            with st.form(f"request_form_{teacher['id']}"):
                message = st.text_area(
                    "Оқытушыға хабарлама",
                    value=(
                        "Сәлеметсіз бе! Сізді ғылыми жетекші "
                        "ретінде таңдағым келеді. "
                        "Ғылыми жобам бойынша бірге "
                        "жұмыс істеуге ұсыныс білдіремін."
                    )
                )
                submitted = st.form_submit_button(
                    "📨 Өтінім жіберу",
                    type="primary"
                )

            if submitted:
                if not message.strip():
                    st.warning("Хабарлама енгізіңіз")
                elif send_request(
                    student["id"],
                    teacher["id"],
                    message.strip()
                ):
                    st.success("Өтінім жіберілді!")
                    st.rerun()
                else:
                    st.warning(
                        "Бұл оқытушыға белсенді өтінім бар."
                    )


# =====================================
# STUDENT DASHBOARD
# =====================================

def show_student_dashboard(user):
    st.header("🎓 Студент кабинеті")

    show_student_profile(user)
    student = get_student(user["username"])

    if not student:
        st.info(
            "Ғылыми жетекші табу үшін "
            "алдымен профиліңізді сақтаңыз."
        )
        return

    st.divider()

    if st.button(
        "🔍 Маған сәйкес ғылыми жетекшілерді табу",
        type="primary",
        use_container_width=True
    ):
        st.session_state.show_matches = True

    if st.session_state.show_matches:
        show_matches(student)

    st.divider()
    st.subheader("📨 Менің өтінімдерім")

    requests_list = get_student_requests(student["id"])

    if not requests_list:
        st.info("Әзірге өтінімдер жоқ")

    for req in requests_list:
        with st.container(border=True):
            st.markdown(
                f"### 👨‍🏫 {escape(req['teacher_name'])}"
            )
            st.write("**Өтінім:**", req["message"])
            st.write("**Мәртебесі:**", req["status"])

            if req["status"] == "Күтуде":
                st.warning("⏳ Оқытушы жауабы күтілуде")

            elif req["status"] == "Қабылданды":
                st.success("✅ Өтінім қабылданды!")
                show_chat(req["id"], "Студент", user)

            else:
                st.error("❌ Өтінім қабылданбады")


# =====================================
# TEACHER DASHBOARD
# =====================================

def show_teacher_dashboard(user):
    st.header("👨‍🏫 Оқытушы кабинеті")

    teacher_id = user["teacher_id"]

    teacher = next(
        (
            t for t in get_teachers()
            if t["id"] == teacher_id
        ),
        None
    )

    if not teacher:
        st.error("Оқытушы табылмады")
        return

    st.subheader(teacher["name"])
    st.write(
        "**Ғылыми бағыттары:**",
        teacher["research"]
    )
    st.write(
        "**Жобалары:**",
        teacher["projects"]
    )

    st.divider()
    st.subheader("🔔 Хабарламалар")

    requests_list = get_teacher_requests(teacher_id)

    pending = [
        req for req in requests_list
        if req["status"] == "Күтуде"
    ]

    if pending:
        st.warning(
            f"📩 Сізге {len(pending)} жаңа өтінім келді!"
        )
    else:
        st.info("Қазір жаңа өтінімдер жоқ")

    if st.button(
        "📥 Өтінімдерді ашу",
        type="primary",
        use_container_width=True
    ):
        st.session_state.open_teacher_requests = True

    if st.session_state.open_teacher_requests:
        st.subheader("📥 Студенттерден келген өтінімдер")

        if not requests_list:
            st.info("Әзірге өтінімдер жоқ")

        for req in requests_list:
            with st.container(border=True):
                st.markdown(
                    f"### 🎓 {escape(req['student_name'])}"
                )

                st.write(
                    "Сізді ғылыми жетекші ретінде таңдады!"
                )
                st.write("**Мамандығы:**", req["major"])
                st.write("**Курс:**", req["course"])
                st.write("**Дағдылары:**", req["skills"])
                st.write(
                    "**Қызығушылықтары:**",
                    req["interests"]
                )
                st.write("**Өтінім:**", req["message"])
                st.write("**Мәртебесі:**", req["status"])

                if req["status"] == "Күтуде":
                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button(
                            "✅ Қабылдау",
                            key=f"accept_{req['id']}"
                        ):
                            update_status(
                                req["id"],
                                teacher_id,
                                "Қабылданды"
                            )
                            st.rerun()

                    with col2:
                        if st.button(
                            "❌ Қабылдамау",
                            key=f"reject_{req['id']}"
                        ):
                            update_status(
                                req["id"],
                                teacher_id,
                                "Қабылданбады"
                            )
                            st.rerun()

                elif req["status"] == "Қабылданды":
                    st.success("Өтінім қабылданды!")
                    show_chat(req["id"], "Оқытушы", user)

                else:
                    st.error("Өтінім қабылданбады")


# =====================================
# RESEARCH RESOURCES
# =====================================

RESEARCH_PLATFORMS = [
    ("Scopus", "https://www.scopus.com/"),
    ("Web of Science", "https://www.webofscience.com/"),
    ("Google Scholar", "https://scholar.google.com/"),
    ("ORCID", "https://orcid.org/"),
    ("GitHub", "https://github.com/"),
    ("arXiv", "https://arxiv.org/")
]

PROJECT_DIRECTIONS = [
    ("🤖 Жасанды интеллект", "Машиналық оқыту"),
    ("📊 Data Science", "Деректерді талдау"),
    ("🔐 Киберқауіпсіздік", "Ақпаратты қорғау"),
    ("🌐 IoT", "Ақылды құрылғылар"),
    ("🎓 EdTech", "Білім беру технологиялары"),
    ("🦾 Робототехника", "Роботтарды бағдарламалау")
]


def show_research_resources():
    st.subheader("🔬 Ғылыми зерттеу кеңістігі")

    tab1, tab2 = st.tabs([
        "🌐 Ғылыми платформалар",
        "🚀 Жоба бағыттары"
    ])

    with tab1:
        for start in range(
            0, len(RESEARCH_PLATFORMS), 3
        ):
            cols = st.columns(3)

            for col, (name, url) in zip(
                cols,
                RESEARCH_PLATFORMS[start:start + 3]
            ):
                with col:
                    with st.container(border=True):
                        st.markdown(f"### {name}")
                        st.link_button(
                            "🌐 Ресми сайт",
                            url,
                            use_container_width=True
                        )

    with tab2:
        for start in range(
            0, len(PROJECT_DIRECTIONS), 3
        ):
            cols = st.columns(3)

            for col, (name, description) in zip(
                cols,
                PROJECT_DIRECTIONS[start:start + 3]
            ):
                with col:
                    with st.container(border=True):
                        st.markdown(f"### {name}")
                        st.write(description)


# =====================================
# HOME PAGE
# =====================================

def show_home(user):
    st.html("""
    <div style="
        background: linear-gradient(
            120deg, #061b46, #1764b5
        );
        border-radius: 22px;
        padding: 42px;
        min-height: 210px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        box-shadow: 0 8px 28px rgba(0,30,80,0.18);
        margin-bottom: 25px;
    ">
        <div style="
            color: #c5dcff;
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 12px;
        ">
            🎓 ENU Opportunity AI
        </div>

        <div style="
            color: white;
            font-size: clamp(26px, 3.5vw, 44px);
            font-weight: 800;
            line-height: 1.2;
            margin-bottom: 14px;
        ">
            БІЗ АЛМАЙТЫН АСУ ЖОҚ!
        </div>

        <div style="
            color: #e1edff;
            font-size: 16px;
            line-height: 1.6;
        ">
            Студент пен ғылыми жетекшіні
            интеллектуалды сәйкестендіру жүйесі
        </div>
    </div>
    """)

    full_name = escape(str(user["full_name"]))

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(
                90deg, #d6f5ed, #dceeff
            );
            padding: 18px 24px;
            border-radius: 14px;
            color: #17644b;
            font-size: 17px;
            font-weight: 600;
        ">
            👋 Қош келдіңіз, {full_name}!
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write(
        "Ғылыми қызығушылықтарыңызға сәйкес "
        "жетекшілерді табыңыз, өтінім жіберіңіз "
        "және ғылыми байланыс орнатыңыз."
    )

    with connect() as conn:
        students_count = conn.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

        teachers_count = conn.execute(
            "SELECT COUNT(*) FROM teachers"
        ).fetchone()[0]

    col1, col2, col3 = st.columns(3)

    col1.metric("🎓 Студенттер", students_count)
    col2.metric("👨‍🏫 Оқытушылар", teachers_count)
    col3.metric("🤖 Сәйкестендіру", "Demo AI")

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


# =====================================
# SIDEBAR
# =====================================

def show_sidebar(user):
    with st.sidebar:
        st.title("🎓 ENU Opportunity AI")
        st.caption("L.N. Gumilyov ENU")
        st.divider()

        st.write(f"👤 **{user['full_name']}**")

        st.caption(
            "Студент" if user["role"] == "student"
            else "Оқытушы"
        )

        pages = ["Басты бет"]

        if user["role"] == "student":
            pages.append("Студент кабинеті")
        else:
            pages.append("Оқытушы кабинеті")

        selected = st.radio(
            "Навигация",
            pages,
            key="enu_sidebar_navigation"
        )

        st.divider()

        if st.button(
            "🚪 Жүйеден шығу",
            use_container_width=True
        ):
            st.session_state.current_user = None
            st.session_state.show_matches = False
            st.session_state.open_teacher_requests = False
            st.session_state.pop(
                "enu_sidebar_navigation", None
            )
            st.rerun()

        st.caption("ENU Opportunity AI | Demo MVP")

    return selected


# =====================================
# MAIN
# =====================================

def main():
    user = st.session_state.current_user

    if user is None:
        show_login()
        return

    page = show_sidebar(user)

    if page == "Басты бет":
        show_home(user)

    elif page == "Студент кабинеті":
        show_student_dashboard(user)

    elif page == "Оқытушы кабинеті":
        show_teacher_dashboard(user)

    st.divider()
    st.caption(
        "ENU Opportunity AI | "
        "Ғылыми жетекшілерді сәйкестендіру "
        "демонстрациялық платформасы"
    )


if __name__ == "__main__":
    main()
