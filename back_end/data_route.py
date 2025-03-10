from flask import Blueprint, request, jsonify
import pyodbc
import os
import threading

data_bp = Blueprint("data", __name__)
session_id_lock = threading.Lock()
current_session_id = None

# Database connection string
DB_CONNECTION_STRING = os.getenv("AZURE_SQL_CONNECTION_STRING")


def get_db_connection():
    return pyodbc.connect(DB_CONNECTION_STRING)


@data_bp.route('/start_session', methods=['POST'])
def start_session():
    global current_session_id

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sessions (start_time) OUTPUT INSERTED.session_id VALUES (GETDATE())")
    session_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    # Store the session ID in a global variable
    with session_id_lock:
        current_session_id = session_id

    return jsonify({"session_id": session_id})


# 2. Store BPM & HRV measurement (can be called from inside Flask)
def store_measurement_internal(session_id, bpm, hrv):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO measurements (session_id, timestamp, bpm, hrv) VALUES (?, GETDATE(), ?, ?)", session_id,
                   bpm, hrv)
    conn.commit()
    conn.close()


# API endpoint (optional if you want external calls)
@data_bp.route('/store_measurement', methods=['POST'])
def store_measurement():
    data = request.json
    store_measurement_internal(data["session_id"], data["bpm"], data["hrv"])
    return jsonify({"message": "Measurement stored"})


# 3. End session & calculate real BPM
@data_bp.route('/end_session', methods=['POST'])
def end_session():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    # Calculate real BPM (average BPM during session)
    cursor.execute("SELECT AVG(bpm) FROM measurements WHERE session_id = ?", data["session_id"])
    real_bpm = cursor.fetchone()[0] or 0

    # Update session with guessed BPM and calculated real BPM
    cursor.execute("UPDATE sessions SET guessed_bpm = ?, real_bpm = ?, end_time = GETDATE() WHERE session_id = ?",
                   data["guessed_bpm"], real_bpm, data["session_id"])

    conn.commit()
    conn.close()
    return jsonify({"message": "Session ended", "real_bpm": real_bpm})


# 4. Get list of all sessions (Only summary: ID, date, guessed BPM, real BPM)
@data_bp.route('/get_sessions', methods=['GET'])
def get_sessions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT session_id, start_time, end_time, guessed_bpm, real_bpm FROM sessions ORDER BY start_time DESC")

    sessions = [
        {
            "session_id": row[0],
            "start_time": row[1],
            "end_time": row[2],
            "guessed_bpm": row[3],
            "real_bpm": row[4]
        } for row in cursor.fetchall()
    ]

    conn.close()
    return jsonify(sessions)


# 5. Get detailed BPM & HRV data for a selected session
@data_bp.route('/get_session_details', methods=['GET'])
def get_session_details():
    session_id = request.args.get("session_id")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, bpm, hrv FROM measurements WHERE session_id = ? ORDER BY timestamp", session_id)

    measurements = [{"timestamp": row[0], "bpm": row[1], "hrv": row[2]} for row in cursor.fetchall()]

    conn.close()
    return jsonify(measurements)
