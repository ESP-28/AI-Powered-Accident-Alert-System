from flask import Flask, request, jsonify, redirect, render_template_string
from flask_cors import CORS
from datetime import datetime
import uuid
import smtplib
from email.message import EmailMessage
import sqlite3
from collections import defaultdict

from database import (
    init_db, insert_accident, get_nearest_hospitals,
    map_accident_to_hospitals, accept_case, get_pending_hospital_emails
)

app = Flask(__name__)
CORS(app)

init_db()

EMAIL_ADDRESS = "akashbro310@gmail.com"
EMAIL_PASSWORD = "bhqa rkxx uvim kbiw"
GUARDIAN_EMAIL = "dm9547@srmist.edu.in"

@app.route('/report-accident', methods=['POST'])
def report_accident():
    data = request.get_json()
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if latitude is None or longitude is None:
        return jsonify({"error": "Missing location data"}), 400

    accident_id = str(uuid.uuid4())
    insert_accident(accident_id, latitude, longitude)

    hospitals = get_nearest_hospitals(latitude, longitude)
    map_accident_to_hospitals(accident_id, hospitals)

    for hospital in hospitals:
        hospital_id = hospital[0]
        email = hospital[2]
        name = hospital[1]

        subject = "🚨 Accident Alert: Immediate Response Required"
        body = f"""
An accident was detected at:

📍 Latitude: {latitude}
📍 Longitude: {longitude}
🕒 Time: {timestamp}

Please respond using the link below:

✅ Accept Case: http://192.168.1.16:5000/accept/{accident_id}?hospital_id={hospital_id}
"""
        send_email([email], subject, body)

    send_email(
        [GUARDIAN_EMAIL],
        "🚨 Guardian Alert",
        f"An accident occurred at:\nLat: {latitude}, Lon: {longitude}\nTime: {timestamp}"
    )

    return jsonify({
        "status": "success",
        "message": "Accident reported and alerts sent.",
        "accident_id": accident_id
    }), 200

@app.route('/accept/<accident_id>', methods=['GET', 'POST'])
def accept_response(accident_id):
    hospital_id = request.args.get('hospital_id')

    if not hospital_id:
        return "Invalid link (missing hospital ID)", 400

    conn = sqlite3.connect("accident_system.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM hospitals WHERE id = ?", (hospital_id,))
    row = cur.fetchone()
    hospital_name = row[0] if row else f"Hospital ID {hospital_id}"
    conn.close()

    if request.method == 'GET':
        return f"""
            <html>
            <body style='font-family: sans-serif; text-align: center; padding-top: 100px;'>
                <h2>🚨 Accident Response Required</h2>
                <form method='POST'>
                    <input type='submit' name='action' value='Accept' style='padding:10px 20px; font-size:16px; margin-right: 20px;'>
                    <input type='submit' name='action' value='Reject' style='padding:10px 20px; font-size:16px;'>
                </form>
            </body>
            </html>
        """

    action = request.form.get('action')

    if action == 'Reject':
        conn = sqlite3.connect("accident_system.db")
        cur = conn.cursor()
        cur.execute("""
            UPDATE accident_hospitals
            SET status = 'rejected'
            WHERE accident_id = ? AND hospital_id = ?
        """, (accident_id, hospital_id))
        conn.commit()
        conn.close()
        return f"<h2>❌ {hospital_name} has rejected the case.</h2>"

    if action == 'Accept':
        accepted = accept_case(accident_id, hospital_id)

        if not accepted:
            conn = sqlite3.connect("accident_system.db")
            cur = conn.cursor()
            cur.execute("""
                SELECT h.name FROM accidents a
                JOIN hospitals h ON a.accepted_by = h.id
                WHERE a.id = ?
            """, (accident_id,))
            row = cur.fetchone()
            accepted_by = row[0] if row else "another hospital"
            conn.close()
            return f"<h2>❌ This case has already been accepted by <strong>{accepted_by}</strong>.</h2>"

        other_emails = get_pending_hospital_emails(accident_id, int(hospital_id))
        followup_subject = "🚑 Stand Down: Case Accepted"
        followup_body = f"""
Another hospital ({hospital_name}) has accepted the case.
No further action is required on your end.
"""
        send_email(other_emails, followup_subject, followup_body)

        return f"<h2>✅ Thank you. <strong>{hospital_name}</strong> has accepted the case.</h2>"

    return "<h3>⚠️ Invalid action submitted.</h3>"

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect("accident_system.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            a.id AS accident_id,
            a.latitude, a.longitude,
            a.timestamp,
            h.name AS accepted_hospital,
            h.latitude AS hosp_lat,
            h.longitude AS hosp_lon
        FROM accidents a
        LEFT JOIN hospitals h ON a.accepted_by = h.id
    """)
    accident_rows = cur.fetchall()

    cur.execute("""
        SELECT accident_id, status
        FROM accident_hospitals
    """)
    status_data = cur.fetchall()
    conn.close()

    status_map = defaultdict(list)
    for acc_id, status in status_data:
        status_map[acc_id].append(status)

    html = """
    <html>
    <head>
        <title>Accident Dashboard</title>
        <style>
            table { width: 90%; margin: 30px auto; border-collapse: collapse; }
            th, td { padding: 10px; border: 1px solid #ccc; text-align: center; }
            th { background-color: #333; color: white; }
            .accepted { color: green; font-weight: bold; }
            .rejected { color: red; font-weight: bold; }
            .pending { color: orange; font-weight: bold; }
        </style>
    </head>
    <body>
        <h2 style='text-align:center;'>🚑 Accident Alert Dashboard</h2>
        <table>
            <tr>
                <th>Accident ID</th>
                <th>Status</th>
                <th>Hospital</th>
                <th>Time</th>
                <th>Location</th>
                <th>Map</th>
                <th>Route</th>
            </tr>
            {% for acc in accidents %}
            <tr>
                <td>{{ acc.id }}</td>
                <td>
                    {% if acc.hospital %}
                        <span class='accepted'>Accepted</span>
                    {% elif 'rejected' in acc.statuses and 'pending' not in acc.statuses %}
                        <span class='rejected'>Rejected</span>
                    {% else %}
                        <span class='pending'>Pending</span>
                    {% endif %}
                </td>
                <td>{{ acc.hospital or '—' }}</td>
                <td>{{ acc.time }}</td>
                <td>{{ acc.lat }}, {{ acc.lon }}</td>
                <td><a href="https://maps.google.com/?q={{ acc.lat }},{{ acc.lon }}" target="_blank">🌍 View</a></td>
                <td>
                    {% if acc.hosp_lat and acc.hosp_lon %}
                    <a href="https://www.google.com/maps/dir/{{ acc.lat }},{{ acc.lon }}/{{ acc.hosp_lat }},{{ acc.hosp_lon }}" target="_blank">🧭 Route</a>
                    {% else %}-{% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """

    accidents = []
    for row in accident_rows:
        acc_id, lat, lon, time, hospital, hosp_lat, hosp_lon = row
        status_list = status_map.get(acc_id, [])
        accidents.append({
            'id': acc_id,
            'lat': lat,
            'lon': lon,
            'time': time,
            'hospital': hospital,
            'statuses': status_list,
            'hosp_lat': hosp_lat,
            'hosp_lon': hosp_lon
        })

    return render_template_string(html, accidents=accidents)

def send_email(to_list, subject, body):
    if not to_list or not any(to_list):
        print("⚠️ No valid recipients. Skipping email.")
        return

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = ', '.join(to_list)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            print(f"✅ Email sent to: {to_list}")
    except Exception as e:
        print(f"❌ Email failed to: {to_list} — {e}")

@app.route('/')
def home():
    return "🚑 Accident Alert Backend is Running!"

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
