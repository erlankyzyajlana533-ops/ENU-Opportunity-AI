
import streamlit as st

from design import apply_design
from teacher_photos import get_teacher_photo

from database import (
    save_student,
    save_teacher,
    get_students,
    get_teachers,
    send_request,
    get_teacher_requests,
    update_request_status,
    create_requests_table,
    create_chat_table,
    get_student_requests,
    send_chat_message,
    get_chat_messages
)

from ai_model import calculate_match, explain_match
from pdf_reader import extract_pdf_text, extract_teacher_info


# ==========================================
# 1. БЕТ ПАРАМЕТРЛЕРІ
# ==========================================

st.set_page_config(
    page_title="ENU Opportunity AI",
    page_icon="🎓",
    layout="wide"
)

apply_design()

create_requests_table()
create_chat_table()


# ==========================================
# 2. КӨМЕКШІ ФУНКЦИЯЛАР
# ==========================================

def get_photo(name):
    """Оқытушы фотосын қауіпсіз алу."""
    if not name:
        return None

    return get_teacher_photo(name)


def show_teacher_header(name, photo=None, number=None):
    """Фото мен аты-жөнін қатар көрсету."""

    col_photo, col_name = st.columns(
        [1, 7],
        vertical_alignment="center"
    )

    with col_photo:
        if photo:
            st.image(photo, width=85)
        else:
            st.markdown("### 👩‍🏫")

    with col_name:
        prefix = f"{number}. " if number else ""
        st.markdown(f"### {prefix}{name}")


# ==========================================
# 3. ЖОБАНЫҢ БАСТЫ БЕТІ
# ==========================================

st.title("🎓 ENU Opportunity AI")

st.subheader(
    "Студент пен ғылыми жетекшіні "
    "интеллектуалды сәйкестендіру жүйесі"
)

st.write(
    "Ғылыми қызығушылықтарға негізделген "
    "ЖИ ұсыныстары және ғылыми жетекшіге "
    "өтінім жіберу платформасы."
)

st.warning(
    "Демонстрациялық MVP: жеке аккаунттар "
    "мен рөлдік авторизация әлі қосылмаған. "
    "Тек тестілік деректерді пайдаланыңыз."
)


# ==========================================
# 4. ЖИ СӘЙКЕСТЕНДІРУ
# ==========================================

def show_student_matches(student_id, skills, interests):

    teachers = get_teachers()

    if not teachers:
        st.warning(
            "Деректер базасында оқытушылар жоқ."
        )
        return

    student_text = f"{interests}. {skills}"

    results = []

    with st.spinner(
        "🤖 ЖИ ғылыми жетекшілерді салыстыруда..."
    ):

        for teacher in teachers:

            teacher_text = (
                f"{teacher['research'] or ''}. "
                f"{teacher['projects'] or ''}. "
                f"{teacher['articles'] or ''}"
            )

            if not teacher_text.strip(" ."):
                continue

            score = calculate_match(
                student_text,
                teacher_text
            )

            explanation = explain_match(
                student_text,
                teacher_text
            )

            results.append({
                "teacher": teacher,
                "score": score,
                "explanation": explanation
            })

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    if not results:
        st.info(
            "Салыстыруға жарамды оқытушылар табылмады."
        )
        return

    st.subheader("🤖 ТОП-3 ғылыми жетекші")

    st.caption(
        "Сіздің ғылыми қызығушылықтарыңызға "
        "ең жақын жетекшілер."
    )

    for index, result in enumerate(
        results[:3],
        start=1
    ):

        teacher = result["teacher"]

        photo = get_photo(
            teacher["name"]
        )

        with st.container(border=True):

            # Фото + аты + сәйкестік
            col_photo, col_info, col_score = st.columns(
                [1, 5, 1.5],
                vertical_alignment="center"
            )

            with col_photo:
                if photo:
                    st.image(photo, width=90)
                else:
                    st.markdown("### 👩‍🏫")

            with col_info:
                st.markdown(
                    f"### {index}. {teacher['name']}"
                )
                st.caption("🎓 Ғылыми жетекші")

            with col_score:
                st.metric(
                    "Сәйкестік",
                    f"{result['score']:.1f}%"
                )

            st.progress(
                max(
                    0.0,
                    min(
                        1.0,
                        result["score"] / 100
                    )
                )
            )

            st.write(
                "**🔬 Ғылыми бағыты:**",
                teacher["research"] or "Көрсетілмеген"
            )

            st.write(
                "**📚 Ғылыми жобалары:**",
                teacher["projects"] or "Көрсетілмеген"
            )

            with st.expander(
                "💡 Неліктен ұсынылды?"
            ):

                st.write(
                    result["explanation"]
                )

                st.caption(
                    "Сәйкестік пайызы мәтіндердің "
                    "мағыналық ұқсастығын көрсетеді. "
                    "Бұл ғылыми жетекшінің жарамдылығына "
                    "кепілдік бермейді."
                )

            message = st.text_area(
                "Ғылыми жетекшіге хабарлама",
                placeholder=(
                    "Сәлеметсіз бе! Сіздің ғылыми "
                    "бағытыңыз бойынша зерттеу "
                    "жүргізгім келеді."
                ),
                key=(
                    f"message_{student_id}_"
                    f"{teacher['id']}"
                )
            )

            if st.button(
                "📨 Өтінім жіберу",
                key=(
                    f"request_{student_id}_"
                    f"{teacher['id']}"
                ),
                type="primary"
            ):

                if not message.strip():

                    st.warning(
                        "Алдымен хабарлама жазыңыз."
                    )

                else:

                    success = send_request(
                        student_id,
                        teacher["id"],
                        message.strip()
                    )

                    if success:

                        st.success(
                            "Өтінім ғылыми жетекшіге "
                            "сәтті жіберілді!"
                        )

                    else:

                        st.info(
                            "Бұл жетекшіге бұрын "
                            "жіберілген өтінім бар."
                        )


# ==========================================
# 5. ЖЕКЕ ЧАТ
# ==========================================

def show_chat(
    request_id,
    current_role,
    teacher_name
):

    st.markdown("### 💬 Жеке чат")

    teacher_photo = get_photo(
        teacher_name
    )

    # Чаттың жоғарғы бөлігі
    col_photo, col_info = st.columns(
        [1, 7],
        vertical_alignment="center"
    )

    with col_photo:
        if teacher_photo:
            st.image(
                teacher_photo,
                width=65
            )
        else:
            st.markdown("### 👩‍🏫")

    with col_info:
        st.markdown(
            f"**{teacher_name}**"
        )
        st.caption(
            "Ғылыми жетекшімен жеке байланыс"
        )

    st.caption(
        "Хабарламалар деректер базасында сақталады."
    )

    if st.button(
        "🔄 Хабарламаларды жаңарту",
        key=(
            f"refresh_{current_role}_"
            f"{request_id}"
        )
    ):
        st.rerun()

    messages = get_chat_messages(
        request_id
    )

    # Хабарламаларды көрсету
    with st.container(
        height=400,
        border=True
    ):

        if not messages:

            st.info(
                "Чат ашылды. "
                "Алғашқы хабарламаны жіберіңіз!"
            )

        for msg in messages:

            sender = msg["sender_role"]

            # Хабарлама кімге тиесілі?
            chat_role = (
                "user"
                if sender == current_role
                else "assistant"
            )

            # Аватар таңдау
            if sender == "Оқытушы":

                if teacher_photo:
                    avatar = teacher_photo
                else:
                    avatar = "👩‍🏫"

            else:
                avatar = "👨‍🎓"

            # Хабарламаны көрсету
            with st.chat_message(
                chat_role,
                avatar=avatar
            ):

                st.caption(sender)

                st.write(
                    msg["message"]
                )

                st.caption(
                    str(msg["created_at"])
                )

    # Хабарлама жіберу
    with st.form(
        key=(
            f"chat_form_{current_role}_"
            f"{request_id}"
        ),
        clear_on_submit=True
    ):

        message = st.text_area(
            "Хабарлама",
            placeholder=(
                "Хабарламаңызды жазыңыз..."
            ),
            height=80
        )

        submitted = st.form_submit_button(
            "📤 Жіберу",
            type="primary"
        )

    if submitted:

        if message.strip():

            success = send_chat_message(
                request_id,
                current_role,
                message.strip()
            )

            if success:

                st.rerun()

            else:

                st.error(
                    "Хабарлама жіберілмеді. "
                    "Өтінім мәртебесін тексеріңіз."
                )

        else:

            st.warning(
                "Бос хабарлама жіберуге болмайды."
            )


# ==========================================
# 6. ОҚЫТУШЫҒА КЕЛГЕН ӨТІНІМДЕР
# ==========================================

def show_teacher_requests(
    teacher_id,
    teacher_name
):

    requests = get_teacher_requests(
        teacher_id
    )

    st.subheader(
        "📥 Маған келген өтінімдер"
    )

    if not requests:

        st.info(
            "Әзірге өтінімдер жоқ."
        )
        return

    for request in requests:

        with st.container(border=True):

            st.markdown(
                f"### 👨‍🎓 {request['student_name']}"
            )

            st.write(
                "**Мамандығы:**",
                request["major"]
            )

            st.write(
                "**Курс:**",
                request["course"]
            )

            st.write(
                "**Дағдылары:**",
                request["skills"]
            )

            st.write(
                "**Ғылыми қызығушылықтары:**",
                request["interests"]
            )

            st.write(
                "**Хабарлама:**",
                request["message"]
            )

            st.write(
                "**Мәртебесі:**",
                request["status"]
            )

            # Өтінім қабылданған болса
            if request["status"] == "Қабылданды":

                st.success(
                    "✅ Өтінім қабылданды. "
                    "Жеке чат ашық!"
                )

                show_chat(
                    request["id"],
                    "Оқытушы",
                    teacher_name
                )

            # Өтінім күтілуде
            elif request["status"] == "Күтуде":

                col1, col2 = st.columns(2)

                with col1:

                    if st.button(
                        "✅ Қабылдау",
                        key=(
                            f"accept_{request['id']}"
                        )
                    ):

                        update_request_status(
                            request["id"],
                            teacher_id,
                            "Қабылданды"
                        )

                        st.rerun()

                with col2:

                    if st.button(
                        "❌ Қабылдамау",
                        key=(
                            f"reject_{request['id']}"
                        )
                    ):

                        update_request_status(
                            request["id"],
                            teacher_id,
                            "Қабылданбады"
                        )

                        st.rerun()

            else:

                st.error(
                    "Бұл өтінім қабылданбаған."
                )


# ==========================================
# 7. ПАЙДАЛАНУШЫ РӨЛІ
# ==========================================

role = st.radio(
    "Сіз кімсіз?",
    ["Студент", "Оқытушы"],
    horizontal=True
)

st.divider()


# ==========================================
# 8. СТУДЕНТ КАБИНЕТІ
# ==========================================

if role == "Студент":

    st.header(
        "👨‍🎓 Студент кабинеті"
    )

    students = get_students()

    student_options = {
        f"{student['name']} — ID {student['id']}": student
        for student in students
    }

    mode = st.radio(
        "Әрекетті таңдаңыз",
        [
            "Тіркелген студент",
            "Жаңа студент"
        ],
        horizontal=True
    )

    # Жаңа студент
    if mode == "Жаңа студент":

        with st.form("student_form"):

            name = st.text_input(
                "Аты-жөніңіз"
            )

            major = st.text_input(
                "Мамандығыңыз"
            )

            course = st.selectbox(
                "Курс",
                [1, 2, 3, 4]
            )

            skills = st.text_area(
                "Дағдыларыңыз",
                placeholder=(
                    "Python, HTML, Machine Learning"
                )
            )

            interests = st.text_area(
                "Ғылыми қызығушылықтарыңыз",
                placeholder=(
                    "Жасанды интеллект, робототехника"
                )
            )

            submitted = st.form_submit_button(
                "💾 Студентті тіркеу",
                type="primary"
            )

        if submitted:

            if (
                name.strip()
                and major.strip()
                and interests.strip()
            ):

                save_student(
                    name.strip(),
                    major.strip(),
                    course,
                    skills.strip(),
                    interests.strip()
                )

                st.success(
                    "Студент тіркелді! "
                    "Енді тіркелген студенттер "
                    "бөлімінен таңдаңыз."
                )

            else:

                st.warning(
                    "Міндетті өрістерді толтырыңыз."
                )

    # Тіркелген студент
    else:

        if student_options:

            selected = st.selectbox(
                "Студентті таңдаңыз",
                list(student_options.keys())
            )

            student = student_options[selected]

            st.divider()

            st.subheader(
                "📨 Менің өтінімдерім"
            )

            my_requests = get_student_requests(
                student["id"]
            )

            if not my_requests:

                st.info(
                    "Сіз әлі өтінім жібермедіңіз."
                )

            for req in my_requests:

                with st.container(border=True):

                    teacher_name = req["teacher_name"]

                    photo = get_photo(
                        teacher_name
                    )

                    # Оқытушы фотосы және аты
                    show_teacher_header(
                        teacher_name,
                        photo
                    )

                    st.write(
                        "**Ғылыми бағыты:**",
                        req["teacher_research"]
                    )

                    st.write(
                        "**Өтінім мәртебесі:**",
                        req["status"]
                    )

                    if req["status"] == "Қабылданды":

                        st.success(
                            "🎉 Ғылыми жетекші "
                            "өтініміңізді қабылдады!"
                        )

                        show_chat(
                            req["id"],
                            "Студент",
                            teacher_name
                        )

                    elif req["status"] == "Күтуде":

                        st.warning(
                            "⏳ Оқытушының жауабын күтіңіз."
                        )

                    else:

                        st.error(
                            "Өтінім қабылданбады."
                        )

            st.divider()

            st.subheader(
                "📋 Менің профилім"
            )

            st.write(
                "**Мамандығы:**",
                student["major"]
            )

            st.write(
                "**Курс:**",
                student["course"]
            )

            st.write(
                "**Дағдылары:**",
                student["skills"]
            )

            st.write(
                "**Ғылыми қызығушылықтары:**",
                student["interests"]
            )

            if st.button(
                "🔍 Ғылыми жетекшілерді табу",
                type="primary"
            ):

                st.session_state[
                    "match_student_id"
                ] = student["id"]

            if (
                st.session_state.get(
                    "match_student_id"
                )
                == student["id"]
            ):

                show_student_matches(
                    student["id"],
                    student["skills"] or "",
                    student["interests"] or ""
                )

        else:

            st.info(
                "Алдымен студент тіркеңіз."
            )


# ==========================================
# 9. ОҚЫТУШЫ КАБИНЕТІ
# ==========================================

else:

    st.header(
        "👩‍🏫 Оқытушы кабинеті"
    )

    mode = st.radio(
        "Әрекетті таңдаңыз",
        [
            "Тіркелген оқытушы",
            "Жаңа оқытушы"
        ],
        horizontal=True
    )

    # Жаңа оқытушы
    if mode == "Жаңа оқытушы":

        st.subheader(
            "📄 PDF арқылы тіркеу"
        )

        uploaded_pdf = st.file_uploader(
            "Оқытушының PDF құжатын жүктеңіз",
            type=["pdf"]
        )

        if uploaded_pdf is not None:

            signature = (
                uploaded_pdf.name,
                uploaded_pdf.size,
                uploaded_pdf.getvalue()[:100]
            )

            if (
                st.session_state.get(
                    "pdf_signature"
                )
                != signature
            ):

                try:

                    pdf_text = extract_pdf_text(
                        uploaded_pdf
                    )

                    info = extract_teacher_info(
                        pdf_text
                    )

                    st.session_state[
                        "teacher_name"
                    ] = info["name"]

                    st.session_state[
                        "teacher_research"
                    ] = info["research"]

                    st.session_state[
                        "teacher_articles"
                    ] = info["articles"]

                    st.session_state[
                        "teacher_projects"
                    ] = info["projects"]

                    st.session_state[
                        "pdf_signature"
                    ] = signature

                    st.session_state[
                        "pdf_text"
                    ] = pdf_text

                    st.success(
                        "PDF құжаты оқылды!"
                    )

                except Exception as error:

                    st.error(
                        f"PDF оқу қатесі: {error}"
                    )

            with st.expander(
                "📄 PDF мәтінін көру"
            ):

                st.text_area(
                    "Алынған мәтін",
                    value=st.session_state.get(
                        "pdf_text",
                        ""
                    ),
                    height=300,
                    disabled=True
                )

        with st.form("teacher_form"):

            name = st.text_input(
                "Аты-жөні",
                key="teacher_name"
            )

            research = st.text_area(
                "Ғылыми бағыты",
                key="teacher_research"
            )

            articles = st.text_area(
                "Ғылыми мақалалары",
                key="teacher_articles"
            )

            projects = st.text_area(
                "Ғылыми жобалары",
                key="teacher_projects"
            )

            submitted = st.form_submit_button(
                "💾 Оқытушыны тіркеу",
                type="primary"
            )

        if submitted:

            if name.strip() and research.strip():

                existing = get_teachers()

                duplicate = any(
                    teacher["name"].strip().casefold()
                    == name.strip().casefold()
                    for teacher in existing
                )

                if duplicate:

                    st.warning(
                        "Бұл оқытушы бұрын тіркелген."
                    )

                else:

                    save_teacher(
                        name.strip(),
                        research.strip(),
                        articles.strip(),
                        projects.strip()
                    )

                    st.success(
                        "Оқытушы базаға сақталды!"
                    )

            else:

                st.warning(
                    "Аты-жөні мен ғылыми "
                    "бағытын толтырыңыз."
                )

    # Тіркелген оқытушы
    else:

        teachers = get_teachers()

        if teachers:

            teacher_options = {
                f"{teacher['name']} — ID {teacher['id']}": teacher
                for teacher in teachers
            }

            selected = st.selectbox(
                "Оқытушыны таңдаңыз",
                list(teacher_options.keys())
            )

            teacher = teacher_options[selected]

            photo = get_photo(
                teacher["name"]
            )

            show_teacher_header(
                teacher["name"],
                photo
            )

            st.write(
                "**🔬 Ғылыми бағыты:**",
                teacher["research"]
            )

            st.write(
                "**📚 Ғылыми жобалары:**",
                teacher["projects"]
            )

            st.divider()

            show_teacher_requests(
                teacher["id"],
                teacher["name"]
            )

        else:

            st.info(
                "Алдымен оқытушы тіркеңіз."
            )


# ==========================================
# 10. ТӨМЕНГІ АҚПАРАТ
# ==========================================

st.divider()

st.caption(
    "ENU Opportunity AI | "
    "ЖИ негізіндегі ғылыми сәйкестендіру "
    "және өтінімдерді басқару жүйесі | MVP"
)
