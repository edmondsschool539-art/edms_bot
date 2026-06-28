import aiosqlite

DB_PATH = "edmonds.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                subject TEXT NOT NULL,
                levels TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                full_name TEXT,
                age_or_class TEXT,
                subject TEXT,
                level TEXT,
                teacher_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                telegram_id INTEGER PRIMARY KEY
            )
        """)
        await db.commit()

# ========== TEACHERS ==========
async def add_teacher(name, subject, levels):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO teachers (name, subject, levels) VALUES (?, ?, ?)", (name, subject, levels))
        await db.commit()

async def get_teachers():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM teachers") as cursor:
            return await cursor.fetchall()

async def get_teacher(teacher_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM teachers WHERE id=?", (teacher_id,)) as cursor:
            return await cursor.fetchone()

async def delete_teacher(teacher_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM teachers WHERE id=?", (teacher_id,))
        await db.commit()

# ========== STUDENTS ==========
async def add_student(telegram_id, full_name, age_or_class, subject, level, teacher_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO students (telegram_id, full_name, age_or_class, subject, level, teacher_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (telegram_id, full_name, age_or_class, subject, level, teacher_id))
        await db.commit()

async def get_student(telegram_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM students WHERE telegram_id=?", (telegram_id,)) as cursor:
            return await cursor.fetchone()

async def get_all_students():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT s.full_name, s.age_or_class, s.subject, s.level, t.name, s.created_at
            FROM students s
            LEFT JOIN teachers t ON s.teacher_id = t.id
            ORDER BY s.created_at DESC
        """) as cursor:
            return await cursor.fetchall()

async def get_all_student_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT telegram_id FROM students") as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

async def count_students():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM students") as cursor:
            row = await cursor.fetchone()
            return row[0]

# ========== ADMINS ==========
async def add_admin(telegram_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO admins (telegram_id) VALUES (?)", (telegram_id,))
        await db.commit()

async def is_admin(telegram_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM admins WHERE telegram_id=?", (telegram_id,)) as cursor:
            return await cursor.fetchone() is not None
