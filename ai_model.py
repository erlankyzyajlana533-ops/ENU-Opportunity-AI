
import re
from functools import lru_cache
from sentence_transformers import SentenceTransformer, util

# Көптілді ЖИ моделі
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Ғылыми бағыттардың сөздігі
TOPICS = {
    "Жасанды интеллект": [
        "жасанды интеллект", "artificial intelligence", "ai", "ии"
    ],
    "Машиналық оқыту": [
        "машиналық оқыту", "machine learning", "ml"
    ],
    "Python": ["python", "питон"],
    "Робототехника": [
        "робототехника", "robotics", "arduino", "робот"
    ],
    "IoT": [
        "iot", "заттар интернеті", "internet of things", "ақылды үй"
    ],
    "Киберқауіпсіздік": [
        "киберқауіпсіздік", "cybersecurity",
        "ақпараттық қауіпсіздік", "криптография"
    ],
    "Деректерді талдау": [
        "data science", "big data",
        "деректерді талдау", "pandas", "numpy"
    ],
    "Веб-әзірлеу": [
        "html", "css", "javascript", "веб", "web", "сайт"
    ],
    "Білім беру технологиялары": [
        "білім беру", "оқыту", "педагогика",
        "education", "edtech"
    ],
    "Нейрондық желілер": [
        "нейрондық желі", "neural network",
        "deep learning", "tensorflow"
    ],
    "Компьютерлік желілер": [
        "компьютерлік желі", "network", "wireshark"
    ],
    "Виртуалды шындық": [
        "виртуалды шындық", "virtual reality", "vr", "ar"
    ]
}


def normalize(text):
    return re.sub(
        r"\s+", " ", str(text or "").lower()
    ).strip()


@lru_cache(maxsize=1)
def get_model():
    return SentenceTransformer(MODEL_NAME)


def calculate_match(student_text, teacher_text):
    """Мәтіндердің мағыналық ұқсастығын есептеу."""

    if not normalize(student_text) or not normalize(teacher_text):
        return 0.0

    ai = get_model()

    embeddings = ai.encode(
        [student_text, teacher_text],
        convert_to_tensor=True
    )

    similarity = util.cos_sim(
        embeddings[0],
        embeddings[1]
    ).item()

    score = max(
        0.0,
        min(100.0, similarity * 100)
    )

    return round(score, 1)


def find_topics(text):
    """Мәтіндегі белгілі ғылыми бағыттарды табу."""

    normalized = normalize(text)
    found = set()

    for topic, keywords in TOPICS.items():
        for keyword in keywords:
            pattern = (
                r"(?<!\w)"
                + re.escape(keyword)
                + r"(?!\w)"
            )

            if re.search(pattern, normalized):
                found.add(topic)
                break

    return found


def explain_match(student_text, teacher_text):
    """ЖИ сәйкестендіру нәтижесін түсіндіру."""

    student_topics = find_topics(student_text)
    teacher_topics = find_topics(teacher_text)

    common = sorted(
        student_topics & teacher_topics
    )

    missing = sorted(
        student_topics - teacher_topics
    )

    score = calculate_match(
        student_text,
        teacher_text
    )

    explanations = []

    if common:
        explanations.append(
            "✅ Ортақ ғылыми бағыттар: "
            + ", ".join(common) + "."
        )

        explanations.append(
            "Бұл бағыттар студенттің қызығушылығы "
            "мен оқытушының ғылыми қызметінде "
            "қатар кездеседі."
        )

    else:
        explanations.append(
            "ℹ️ Белгілі тақырыптар тізімі бойынша "
            "нақты ортақ бағыт анықталмады. "
            "Мағыналық ұқсастық басқа сөздер "
            "мен контекст арқылы есептелуі мүмкін."
        )

    if missing:
        explanations.append(
            "🔎 Оқытушы сипаттамасында нақты "
            "көрсетілмеген студент қызығушылықтары: "
            + ", ".join(missing) + "."
        )

        explanations.append(
            "Бұл оқытушыда осы бағыттар жоқ "
            "дегенді білдірмейді. "
            "Профилін нақтылау қажет."
        )

    if score >= 80:
        explanations.append(
            "📊 Мәтіндердің мағыналық "
            "ұқсастығы жоғары."
        )

    elif score >= 55:
        explanations.append(
            "📊 Мәтіндердің мағыналық "
            "ұқсастығы орташа."
        )

    else:
        explanations.append(
            "📊 Мәтіндердің мағыналық "
            "ұқсастығы төмен. "
            "Қосымша мәлімет енгізіп, "
            "қайта салыстыруға болады."
        )

    explanations.append(
        "⚠️ Бұл ұпай ғылыми жетекшінің "
        "жарамдылық ықтималдығы емес. "
        "Нақты таңдау үшін жобалар, тәжірибе "
        "және жетекшілік мүмкіндігі "
        "тексерілуі тиіс."
    )

    return "\n\n".join(explanations)
  