import sqlite3

def init_db():
    conn = sqlite3.connect("accident_system.db")
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            latitude REAL,
            longitude REAL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS accidents (
            id TEXT PRIMARY KEY,
            latitude REAL,
            longitude REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            accepted_by INTEGER,
            FOREIGN KEY (accepted_by) REFERENCES hospitals(id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS accident_hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            accident_id TEXT,
            hospital_id INTEGER,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (accident_id) REFERENCES accidents(id),
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
        )
    ''')

    conn.commit()
    conn.close()

def insert_accident(accident_id, latitude, longitude):
    conn = sqlite3.connect("accident_system.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO accidents (id, latitude, longitude)
        VALUES (?, ?, ?)
    """, (accident_id, latitude, longitude))
    conn.commit()
    conn.close()

def map_accident_to_hospitals(accident_id, hospitals):
    conn = sqlite3.connect("accident_system.db")
    cur = conn.cursor()
    for hospital in hospitals:
        hospital_id = hospital[0]
        cur.execute("""
            INSERT INTO accident_hospitals (accident_id, hospital_id, status)
            VALUES (?, ?, 'pending')
        """, (accident_id, hospital_id))
    conn.commit()
    conn.close()

def accept_case(accident_id, hospital_id):
    conn = sqlite3.connect("accident_system.db")
    cur = conn.cursor()

    cur.execute("SELECT accepted_by FROM accidents WHERE id = ?", (accident_id,))
    result = cur.fetchone()
    if result and result[0] is not None:
        conn.close()
        return False

    cur.execute("""
        UPDATE accidents SET accepted_by = ? WHERE id = ?
    """, (hospital_id, accident_id))

    cur.execute("""
        UPDATE accident_hospitals
        SET status = 'accepted'
        WHERE accident_id = ? AND hospital_id = ?
    """, (accident_id, hospital_id))

    conn.commit()
    conn.close()
    return True

def get_nearest_hospitals(lat, lon, limit=3):
    conn = sqlite3.connect("accident_system.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM hospitals")
    hospitals = cur.fetchall()
    conn.close()

    def distance(h):
        return (lat - h[3]) ** 2 + (lon - h[4]) ** 2

    sorted_hospitals = sorted(hospitals, key=distance)
    return sorted_hospitals[:limit]

def get_pending_hospital_emails(accident_id, accepted_hospital_id):
    conn = sqlite3.connect("accident_system.db")
    cur = conn.cursor()
    cur.execute('''
        SELECT h.email FROM accident_hospitals ah
        JOIN hospitals h ON ah.hospital_id = h.id
        WHERE ah.accident_id = ?
          AND ah.hospital_id != ?
          AND ah.status = 'pending'
    ''', (accident_id, accepted_hospital_id))
    rows = cur.fetchall()
    conn.close()
    return [row[0] for row in rows if row[0]]