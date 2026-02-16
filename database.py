import os
import sqlite3
from contextlib import contextmanager

# Use .env / environment variables if present.
# This keeps Windows + Linux behavior consistent and prevents "profile not saved" bugs
# caused by mismatched DB filenames.
def _resolve_db_path() -> str:
    p = os.getenv("DATABASE_PATH")
    if p:
        return p
    url = os.getenv("DATABASE_URL") or os.getenv("DATABASE_URI")
    if url and url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "", 1)
    return "nutrivision.db"


DATABASE_PATH = _resolve_db_path()

def init_database():
    """Initialize the database with required tables."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    

    # Users table (email/password auth)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # User profiles table (latest row per user is active)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER,
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            age INTEGER,
            gender TEXT,
            height REAL,
            weight REAL,
            conditions TEXT,
            goals TEXT,
            activity_level TEXT,
            calorie_target REAL,
            protein_target REAL,
            carb_target REAL,
            fat_target REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # NOTE: do not ALTER user_profiles.user_id; it already exists in the schema above.

    # Food logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            date TEXT,
            product_name TEXT,
            calories REAL,
            protein REAL,
            carbs REAL,
            fat REAL,
            sugar REAL,
            sodium REAL,
            fiber REAL,
            additives_count INTEGER DEFAULT 0,
            nova_group INTEGER,
            nutri_score TEXT,
            score INTEGER,
            source TEXT DEFAULT 'manual',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Lightweight migration for older DBs
    try:
        cursor.execute("ALTER TABLE food_logs ADD COLUMN source TEXT DEFAULT 'manual'")
    except Exception:
        pass

    # More lightweight migrations
    for stmt in [
        "ALTER TABLE food_logs ADD COLUMN nova_group INTEGER",
        "ALTER TABLE food_logs ADD COLUMN nutri_score TEXT",
    ]:
        try:
            cursor.execute(stmt)
        except Exception:
            pass

    # Water logs table (separate from food logs for clean tracking)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS water_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            date TEXT,
            amount_ml INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Products cache table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products_cache (
            barcode TEXT PRIMARY KEY,
            name TEXT,
            brand TEXT,
            nutri_score TEXT,
            nova_group INTEGER,
            eco_score TEXT,
            calories REAL,
            protein REAL,
            carbs REAL,
            fat REAL,
            sugar REAL,
            sodium REAL,
            fiber REAL,
            additives TEXT,
            allergens TEXT,
            vegan INTEGER,
            vegetarian INTEGER,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Additive concerns cache (for Tavily/Groq enrichment)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS additive_cache (
            code TEXT PRIMARY KEY,
            name TEXT,
            risk TEXT,
            concerns TEXT,
            sources_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    
    
    # Grocery scan sessions (cart mode)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grocery_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            title TEXT DEFAULT 'Grocery Session',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grocery_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            barcode TEXT,
            name TEXT,
            score INTEGER,
            nova_group INTEGER,
            sugar REAL,
            sodium REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES grocery_sessions(id)
        )
    """)

    # Weekly reports cache (optional)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            week_start TEXT,
            pdf_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_user_profile(user_id: int):
    """Get latest user profile for a given auth user_id."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM user_profiles WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def save_user_profile(data, user_id=None):
    """Save or update user profile."""
    with get_db() as conn:
        cursor = conn.cursor()
        uid = int(user_id or data.get("user_id") or 1)
        cursor.execute("""
            INSERT INTO user_profiles (
                user_id, age, gender, height, weight, conditions, goals, 
                activity_level, calorie_target, protein_target, 
                carb_target, fat_target
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uid,
            data['age'], data['gender'], data['height'], data['weight'],
            data.get('conditions', ''), data.get('goals', ''), data.get('activity_level', ''),
            data.get('calorie_target', 0), data.get('protein_target', 0),
            data.get('carb_target', 0), data.get('fat_target', 0)
        ))
        conn.commit()
        return cursor.lastrowid

def get_food_logs(user_id=1, date=None):
    """Get food logs for a user, optionally filtered by date."""
    with get_db() as conn:
        cursor = conn.cursor()
        if date:
            cursor.execute(
                "SELECT * FROM food_logs WHERE user_id = ? AND date = ? ORDER BY created_at DESC",
                (user_id, date)
            )
        else:
            cursor.execute(
                "SELECT * FROM food_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
                (user_id,)
            )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def save_food_log(data):
    """Save a food log entry."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO food_logs (
                user_id, date, product_name, calories, protein, carbs, 
                fat, sugar, sodium, fiber, additives_count, nova_group, nutri_score, score, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('user_id', 1), data['date'], data['product_name'],
            data['calories'], data['protein'], data['carbs'], data['fat'],
            data['sugar'], data['sodium'], data.get('fiber', 0),
            data.get('additives_count', 0), data.get('nova_group'), data.get('nutri_score'),
            data.get('score', 0), data.get('source', 'manual')
        ))
        conn.commit()
        return cursor.lastrowid


def save_water_log(user_id: int, date: str, amount_ml: int) -> int:
    """Save water intake log."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO water_logs (user_id, date, amount_ml) VALUES (?, ?, ?)",
            (user_id, date, amount_ml),
        )
        conn.commit()
        return cursor.lastrowid


def get_water_logs(user_id: int = 1, date: str | None = None):
    """Get water logs; by date or recent."""
    with get_db() as conn:
        cursor = conn.cursor()
        if date:
            cursor.execute(
                "SELECT * FROM water_logs WHERE user_id = ? AND date = ? ORDER BY created_at DESC",
                (user_id, date),
            )
        else:
            cursor.execute(
                "SELECT * FROM water_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
                (user_id,),
            )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_day_totals(user_id: int, date: str) -> dict:
    """Compute totals for calories/macros + water for a day."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT 
              COALESCE(SUM(calories),0) as calories,
              COALESCE(SUM(protein),0) as protein,
              COALESCE(SUM(carbs),0) as carbs,
              COALESCE(SUM(fat),0) as fat
            FROM food_logs WHERE user_id=? AND date=?
            """,
            (user_id, date),
        )
        food = dict(c.fetchone())
        c.execute(
            "SELECT COALESCE(SUM(amount_ml),0) as water_ml FROM water_logs WHERE user_id=? AND date=?",
            (user_id, date),
        )
        water = dict(c.fetchone())
        return {**food, **water}

def get_cached_product(barcode):
    """Get product from cache."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products_cache WHERE barcode = ?", (barcode,))
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None

def cache_product(barcode, data):
    """Cache product data."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO products_cache (
                barcode, name, brand, nutri_score, nova_group, eco_score,
                calories, protein, carbs, fat, sugar, sodium, fiber,
                additives, allergens, vegan, vegetarian
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            barcode, data.get('name'), data.get('brand'),
            data.get('nutri_score'), data.get('nova_group'), data.get('eco_score'),
            data.get('calories'), data.get('protein'), data.get('carbs'),
            data.get('fat'), data.get('sugar'), data.get('sodium'),
            data.get('fiber'), data.get('additives'), data.get('allergens'),
            data.get('vegan', 0), data.get('vegetarian', 0)
        ))
        conn.commit()


def get_cached_additive(code: str):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM additive_cache WHERE code = ?", (code.upper(),))
        row = c.fetchone()
        return dict(row) if row else None


def cache_additive(code: str, name: str, risk: str, concerns: str, sources_json: str):
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT OR REPLACE INTO additive_cache (code, name, risk, concerns, sources_json, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (code.upper(), name, risk, concerns, sources_json),
        )
        conn.commit()


def create_user(email: str, password_hash: str) -> int:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email.lower().strip(), password_hash))
        conn.commit()
        return cur.lastrowid

def get_user_by_email(email: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
        row = cur.fetchone()
        return dict(row) if row else None

def get_user_by_id(user_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_grocery_session(user_id: int, title: str = "Grocery Session") -> int:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO grocery_sessions(user_id, title) VALUES (?,?)", (user_id, title))
        conn.commit()
        return cur.lastrowid

def add_grocery_item(session_id: int, product: dict, score: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO grocery_items(session_id, barcode, name, score, nova_group, sugar, sodium)
               VALUES (?,?,?,?,?,?,?)""",
            (
                session_id,
                product.get("barcode") or product.get("code") or "",
                product.get("name") or product.get("product_name") or "Unknown",
                int(score or 0),
                int(product.get("nova_group") or product.get("nova_group") or 0),
                float(product.get("sugar") or 0),
                float(product.get("sodium") or 0),
            ),
        )
        conn.commit()

def get_grocery_items(session_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM grocery_items WHERE session_id=? ORDER BY created_at DESC", (session_id,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]

def end_grocery_session(session_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE grocery_sessions SET ended_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
        conn.commit()
