
import sqlite3
from pathlib import Path
from datetime import datetime

# ==========================================
# ENU OPPORTUNITY AI
# DATABASE CLEANUP
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "enu_opportunity.db"

TEACHER_ID_TO_DELETE = 1


def cleanup_database():

    if not DB_PATH.exists():
        print("❌ Деректер базасы табылмады!")
        print(DB_PATH)
        return

    # ======================================
    # 1. РЕЗЕРВТІК КӨШІРМЕ
    # ======================================

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    backup_path = BASE_DIR / (
        f"enu_opportunity_backup_{timestamp}.db"
    )

    with sqlite3.connect(DB_PATH) as source:
        with sqlite3.connect(backup_path) as target:
            source.backup(target)

    print("✅ Резервтік көшірме жасалды:")
    print(backup_path)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("PRAGMA foreign_keys = ON")

        # ======================================
        # 2. КЕСТЕЛЕРДІ ТЕКСЕРУ
        # ======================================

        def table_exists(table_name):
            result = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                AND name = ?
                """,
                (table_name,)
            ).fetchone()

            return result is not None

        def get_columns(table_name):
            if not table_exists(table_name):
                return set()

            return {
                row["name"]
                for row in conn.execute(
                    f'PRAGMA table_info("{table_name}")'
                ).fetchall()
            }

        required_tables = [
            "students",
            "teachers",
            "supervision_requests",
            "chat_messages",
            "account_links"
        ]

        print("\n📋 КЕСТЕЛЕРДІ ТЕКСЕРУ")

        for table in required_tables:
            if table_exists(table):
                print(f"✅ {table}")
            else:
                print(f"⚠️ {table} табылмады")

        for table in required_tables:
            if not table_exists(table):
                raise RuntimeError(
                    f"{table} кестесі табылмады. "
                    "Қауіпсіздік үшін тазалау тоқтатылды."
                )

        expected_columns = {
            "students": {"id"},
            "teachers": {"id", "name"},
            "supervision_requests": {
                "id", "student_id", "teacher_id"
            },
            "chat_messages": {"request_id"},
            "account_links": {
                "id", "external_sub", "role", "profile_id"
            }
        }

        for table, required in expected_columns.items():
            missing = required - get_columns(table)

            if missing:
                raise RuntimeError(
                    f"{table} кестесінде бағандар жоқ: "
                    f"{sorted(missing)}"
                )

        # ======================================
        # 3. ҚОСЫМША БАЙЛАНЫСТАР
        # ======================================

        known_tables = set(required_tables)

        all_tables = [
            row["name"]
            for row in conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()
        ]

        for table in all_tables:
            if table in known_tables:
                continue

            safe_name = table.replace('"', '""')

            foreign_keys = conn.execute(
                f'PRAGMA foreign_key_list("{safe_name}")'
            ).fetchall()

            for fk in foreign_keys:
                if fk["table"] in known_tables:
                    raise RuntimeError(
                        "Қосымша байланысты кесте табылды: "
                        f"{table}. Құрылымын тексеру қажет."
                    )

        # ======================================
        # 4. ӨШІРІЛЕТІН ДЕРЕКТЕР
        # ======================================

        teacher = conn.execute(
            """
            SELECT id, name
            FROM teachers
            WHERE id = ?
            """,
            (TEACHER_ID_TO_DELETE,)
        ).fetchone()

        if teacher is None:
            raise RuntimeError(
                f"ID={TEACHER_ID_TO_DELETE} "
                "оқытушы табылмады."
            )

        student_count = conn.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

        teacher_count = conn.execute(
            "SELECT COUNT(*) FROM teachers"
        ).fetchone()[0]

        # Өшірілетін өтінімдер
        request_rows = conn.execute(
            """
            SELECT id
            FROM supervision_requests
            WHERE student_id IN (
                SELECT id FROM students
            )
            OR teacher_id = ?
            """,
            (TEACHER_ID_TO_DELETE,)
        ).fetchall()

        request_ids = [
            row["id"] for row in request_rows
        ]

        # Өшірілетін чаттар саны
        chat_count = 0

        if request_ids:
            placeholders = ",".join(
                "?" for _ in request_ids
            )

            chat_count = conn.execute(
                f"""
                SELECT COUNT(*)
                FROM chat_messages
                WHERE request_id IN ({placeholders})
                """,
                request_ids
            ).fetchone()[0]

        # Өшірілетін аккаунт байланыстары
        account_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM account_links
            WHERE (
                role = 'student'
                AND profile_id IN (
                    SELECT id FROM students
                )
            )
            OR (
                role = 'teacher'
                AND profile_id = ?
            )
            """,
            (TEACHER_ID_TO_DELETE,)
        ).fetchone()[0]

        print("\n" + "=" * 48)
        print("🗑️ ӨШІРІЛЕТІН ДЕРЕКТЕР")
        print("=" * 48)

        print(f"Студенттер: {student_count}")
        print(
            f"Оқытушы: {teacher['name']} "
            f"(ID={TEACHER_ID_TO_DELETE})"
        )
        print(f"Өтінімдер: {len(request_ids)}")
        print(f"Чат хабарламалары: {chat_count}")
        print(f"Аккаунт байланыстары: {account_count}")
        print(f"Қазіргі оқытушылар саны: {teacher_count}")

        # ======================================
        # 5. РАСТАУ
        # ======================================

        print("\n⚠️ НАЗАР АУДАРЫҢЫЗ!")
        print("Бұл әрекет деректерді өшіреді.")
        print("Резервтік көшірме сақталған.")

        confirmation = input(
            "\nЖалғастыру үшін DELETE деп жазыңыз: "
        ).strip()

        if confirmation != "DELETE":
            print("\n❎ Тазалау тоқтатылды.")
            return

        # ======================================
        # 6. ТРАНЗАКЦИЯ
        # ======================================

        conn.execute("BEGIN IMMEDIATE")

        # 6.1. Чат хабарламаларын өшіру
        if request_ids:
            placeholders = ",".join(
                "?" for _ in request_ids
            )

            conn.execute(
                f"""
                DELETE FROM chat_messages
                WHERE request_id IN ({placeholders})
                """,
                request_ids
            )

        # 6.2. Өтінімдерді өшіру
        conn.execute(
            """
            DELETE FROM supervision_requests
            WHERE student_id IN (
                SELECT id FROM students
            )
            OR teacher_id = ?
            """,
            (TEACHER_ID_TO_DELETE,)
        )

        # 6.3. Студент аккаунт байланыстары
        conn.execute(
            """
            DELETE FROM account_links
            WHERE role = 'student'
            AND profile_id IN (
                SELECT id FROM students
            )
            """
        )

        # 6.4. ID=1 оқытушы аккаунт байланысы
        conn.execute(
            """
            DELETE FROM account_links
            WHERE role = 'teacher'
            AND profile_id = ?
            """,
            (TEACHER_ID_TO_DELETE,)
        )

        # 6.5. Барлық студенттерді өшіру
        conn.execute(
            "DELETE FROM students"
        )

        # 6.6. Тек ID=1 оқытушыны өшіру
        conn.execute(
            """
            DELETE FROM teachers
            WHERE id = ?
            """,
            (TEACHER_ID_TO_DELETE,)
        )

        # ======================================
        # 7. ТҰТАСТЫҚТЫ ТЕКСЕРУ
        # ======================================

        violations = conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if violations:
            raise RuntimeError(
                "Сыртқы кілт байланыстары бұзылды: "
                f"{len(violations)} қате"
            )

        # Қалған студенттер
        remaining_students = conn.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

        # Қалған оқытушылар
        remaining_teachers = conn.execute(
            "SELECT COUNT(*) FROM teachers"
        ).fetchone()[0]

        # Өшірілген оқытушының бар-жоғын тексеру
        deleted_teacher = conn.execute(
            """
            SELECT id FROM teachers
            WHERE id = ?
            """,
            (TEACHER_ID_TO_DELETE,)
        ).fetchone()

        if remaining_students != 0:
            raise RuntimeError(
                "Студенттер толық тазаланбады."
            )

        if deleted_teacher is not None:
            raise RuntimeError(
                "ID=1 оқытушы өшірілмеді."
            )

        if remaining_teachers != teacher_count - 1:
            raise RuntimeError(
                "Оқытушылар саны сәйкес емес."
            )

        # ======================================
        # 8. ӨЗГЕРІСТЕРДІ САҚТАУ
        # ======================================

        conn.commit()

        print("\n" + "=" * 48)
        print("✅ ДЕРЕКТЕР БАЗАСЫ ТАЗАЛАНДЫ!")
        print("=" * 48)

        print("✅ Барлық студенттер өшірілді")
        print("✅ ID=1 оқытушы өшірілді")
        print("✅ Байланысты өтінімдер өшірілді")
        print("✅ Байланысты чаттар тазаланды")
        print("✅ Аккаунт байланыстары тазаланды")

        print("\n📊 ҚАЛҒАН ДЕРЕКТЕР")
        print(f"Студенттер: {remaining_students}")
        print(f"Оқытушылар: {remaining_teachers}")

        print("\n💾 Резервтік көшірме:")
        print(backup_path)

    except Exception as error:
        conn.rollback()

        print("\n❌ ҚАТЕ:")
        print(error)
        print("Транзакциядағы өзгерістер қайтарылды.")
        print("Резервтік көшірме:")
        print(backup_path)

    finally:
        conn.close()


if __name__ == "__main__":
    cleanup_database()
