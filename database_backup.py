
import sqlite3

DB_NAME = "enu_opportunity.db"


def create_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            major TEXT,
            course INTEGER,
            skills TEXT,
            interests TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            research TEXT,
            articles TEXT,
            projects TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_student(name, major, course, skills, interests):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO students
        (name, major, course, skills, interests)
        VALUES (?, ?, ?, ?, ?)
    """, (name, major, course, skills, interests))

    conn.commit()
    conn.close()


def save_teacher(name, research, articles, projects):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO teachers
        (name, research, articles, projects)
        VALUES (?, ?, ?, ?)
    """, (name, research, articles, projects))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_database()
    
def get_students():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students")
    students = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return students


def get_teachers():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM teachers")
    teachers = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return teachers

def create_requests_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supervision_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            teacher_id INTEGER NOT NULL,
            message TEXT,
            status TEXT NOT NULL DEFAULT 'Күтуде',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (teacher_id) REFERENCES teachers(id)
        )
    """)

    conn.commit()
    conn.close()


def send_request(student_id, teacher_id, message):
    create_requests_table()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM supervision_requests
        WHERE student_id = ? AND teacher_id = ?
        AND status = 'Күтуде'
    """, (student_id, teacher_id))

    if cursor.fetchone():
        conn.close()
        return False

    cursor.execute("""
        INSERT INTO supervision_requests
        (student_id, teacher_id, message)
        VALUES (?, ?, ?)
    """, (student_id, teacher_id, message))

    conn.commit()
    conn.close()
    return True


def get_teacher_requests(teacher_id):
    create_requests_table()

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.*, s.name AS student_name,
               s.major, s.course, s.skills, s.interests
        FROM supervision_requests r
        JOIN students s ON s.id = r.student_id
        WHERE r.teacher_id = ?
        ORDER BY r.created_at DESC, r.id DESC
    """, (teacher_id,))

    results = [
        dict(row) for row in cursor.fetchall()
    ]

    conn.close()
    return results


def update_request_status(request_id, teacher_id, status):
    if status not in ("Қабылданды", "Қабылданбады"):
        raise ValueError("Белгісіз мәртебе")

    create_requests_table()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE supervision_requests
        SET status = ?
        WHERE id = ? AND teacher_id = ?
        AND status = 'Күтуде'
    """, (status, request_id, teacher_id))

    updated = cursor.rowcount > 0

    conn.commit()
    conn.close()
    return updated
  
# =====================================
# ЖЕКЕ ЧАТ ЖҮЙЕСІ
# =====================================

def create_chat_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            sender_role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (request_id)
                REFERENCES supervision_requests(id)
        )
    """)

    conn.commit()
    conn.close()


def get_student_requests(student_id):
    create_requests_table()

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.*, t.name AS teacher_name,
               t.research AS teacher_research
        FROM supervision_requests r
        JOIN teachers t ON t.id = r.teacher_id
        WHERE r.student_id = ?
        ORDER BY r.id DESC
    """, (student_id,))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def send_chat_message(request_id, sender_role, message):
    if sender_role not in ("Студент", "Оқытушы"):
        return False

    if not message or not message.strip():
        return False

    create_chat_table()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT status
        FROM supervision_requests
        WHERE id = ?
    """, (request_id,))

    request = cursor.fetchone()

    if not request or request[0] != "Қабылданды":
        conn.close()
        return False

    cursor.execute("""
        INSERT INTO chat_messages
        (request_id, sender_role, message)
        VALUES (?, ?, ?)
    """, (request_id, sender_role, message.strip()))

    conn.commit()
    conn.close()
    return True


def get_chat_messages(request_id):
    create_chat_table()

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, sender_role, message, created_at
        FROM chat_messages
        WHERE request_id = ?
          AND EXISTS (
              SELECT 1
              FROM supervision_requests
              WHERE id = ?
                AND status = 'Қабылданды'
          )
        ORDER BY id ASC
    """, (request_id, request_id))

    messages = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return messages

    print("Деректер базасы сәтті құрылды!")
