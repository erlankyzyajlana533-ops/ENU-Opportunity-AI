
import re
import fitz


def extract_pdf_text(uploaded_file):
    """PDF құжатындағы мәтінді оқу."""

    pdf_bytes = uploaded_file.getvalue()
    pages = []

    with fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    ) as document:

        for page in document:
            pages.append(page.get_text("text"))

    return "\n".join(pages).strip()


def extract_teacher_info(text):
    """
    PDF мәтінінен оқытушы мәліметтерін
    бастапқы ережелер арқылы анықтау.
    """

    result = {
        "name": "",
        "research": "",
        "articles": "",
        "projects": ""
    }

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return result

    # Аты-жөнін іздеу
    name_patterns = [
        r"(?:Аты-жөні|ФИО|Full name)\s*[:：]\s*(.+)",
        r"(?:Тегі,\s*аты,\s*әкесінің аты)\s*[:：]\s*(.+)"
    ]

    for pattern in name_patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:
            result["name"] = match.group(1).strip()
            break

    # Ғылыми бағытты анықтау
    research_keywords = [
        "ғылыми қызығушылық",
        "ғылыми бағыт",
        "research interests",
        "research area",
        "область научных интересов",
        "научные интересы"
    ]

    # Мақалаларды анықтау
    article_keywords = [
        "мақала",
        "жарияланым",
        "publication",
        "article",
        "scopus",
        "web of science",
        "doi",
        "журнал"
    ]

    # Жобаларды анықтау
    project_keywords = [
        "ғылыми жоба",
        "грант",
        "жоба жетекшісі",
        "project",
        "grant",
        "проект",
        "грантовое финансирование"
    ]

    research = []
    articles = []
    projects = []

    for index, line in enumerate(lines):

        lower_line = line.lower()

        if any(
            word in lower_line
            for word in research_keywords
        ):
            research.append(line)

            # Тақырып бөлек жолда болса
            if (
                line.endswith(":")
                and index + 1 < len(lines)
            ):
                research.append(lines[index + 1])

        if any(
            word in lower_line
            for word in article_keywords
        ):
            articles.append(line)

        if any(
            word in lower_line
            for word in project_keywords
        ):
            projects.append(line)

    result["research"] = "\n".join(
        dict.fromkeys(research)
    )

    result["articles"] = "\n".join(
        dict.fromkeys(articles)
    )

    result["projects"] = "\n".join(
        dict.fromkeys(projects)
    )

    return result
