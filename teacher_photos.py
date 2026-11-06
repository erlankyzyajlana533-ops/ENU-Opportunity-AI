
from pathlib import Path
import unicodedata

PHOTO_DIR = Path(__file__).parent / "assets" / "teachers"

TEACHER_PHOTOS = {
    "серік меруерт": "serik_meruert.jpg",
    "альжанов айтуған": "alzhanov_aitugan.jpg",
    "омарбеков еркін": "omarbekov_erkin.jpg",
    "зұлпыхар жандос": "zulpykhar_zhandos.jpg",
}


def get_teacher_photo(name):
    if not name:
        return None

    normalized = unicodedata.normalize(
        "NFKC", str(name)
    ).casefold().strip()

    normalized = " ".join(normalized.split())

    for teacher_name, filename in TEACHER_PHOTOS.items():
        if teacher_name in normalized:
            photo_path = PHOTO_DIR / filename

            if photo_path.is_file():
                return str(photo_path)

    return None
