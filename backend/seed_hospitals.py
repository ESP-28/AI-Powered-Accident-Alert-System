import sqlite3

hospitals = [
    ("Apollo Hospital", "ps2856@srmist.edu.in", 17.3850, 78.4867),
    ("Rainbow Hospital", "sasanksubudhi2004@gmail.com", 17.4100, 78.4786),
    ("KIMS Hospital", "kims@example.com", 17.4320, 78.4480),
    ("Care Hospital", "vf1840@srmist.edu.in", 17.4000, 78.4600),
    ("Yashoda Hospital", "amrin2288@gmail.com", 17.3700, 78.4800)
]

conn = sqlite3.connect("accident_system.db")
cur = conn.cursor()

# Optional: Clear old hospital entries (if re-seeding)
cur.execute("DELETE FROM hospitals")

for name, email, latitude, longitude in hospitals:
    cur.execute(
        "INSERT INTO hospitals (name, email, latitude, longitude) VALUES (?, ?, ?, ?)",
        (name, email, latitude, longitude)
    )

conn.commit()
conn.close()

print("✅ Hospitals inserted successfully.")
