from flask import Blueprint, request, jsonify
import pyodbc
import os
import threading
import globals
import json

data_bp = Blueprint("data", __name__)
session_id_lock = threading.Lock()
current_session_id = 1

current_source = None

# Database connection string
os.environ["DB_CONNECTION_STRING"] = (
    "Driver={ODBC Driver 18 for SQL Server};Server=tcp:heart-monitor-server.privatelink.database.windows.net,"
    "1433;Database=heart-monitor-db;Uid=heart-monitor-server-admin;Pwd=#ass101223;Encrypt=yes;TrustServerCertificate"
    "=yes;Connection Timeout=30;")


def start_over():
    globals.concatenated_intensities = []
    globals.round_count = 0
    globals.past_intervals = []


def get_current_session_id():
    with session_id_lock:
        return current_session_id


def get_db_connection():
    db_conn_str = os.getenv("DB_CONNECTION_STRING")
    if not db_conn_str:
        raise ValueError("DB_CONNECTION_STRING is not set or empty")
    return pyodbc.connect(db_conn_str)


@data_bp.route('/start_session', methods=['POST'])
def start_session():
    global current_session_id, current_source

    data = request.get_json()
    source = data.get('source')

    if not isinstance(source, str):
        return jsonify({"error": "Source must be a string"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sessions (start_time) OUTPUT INSERTED.session_id VALUES (GETDATE())")
    session_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    start_over()

    with session_id_lock:
        current_session_id = session_id
        current_source = source  # Save the source globally

    return jsonify({"session_id": session_id})


# 2. Store BPM & HRV measurement (can be called from inside Flask).
def store_measurement_internal(session_id, bpm, hrv):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO measurements (session_id, timestamp, bpm, hrv) VALUES (?, GETDATE(), ?, ?)",
            session_id, bpm, hrv
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Insert Error: {e}")


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

def save_prediction_to_db(prediction_lengths):
    global current_source
    source = current_source
    if not isinstance(prediction_lengths, list):
        raise ValueError("prediction_lengths must be a list")
    if not source:
        raise ValueError("No source provided")

    conn = get_db_connection()
    cursor = conn.cursor()

    prediction_json = json.dumps(prediction_lengths)
    cursor.execute("""
        INSERT INTO predictions (prediction_lengths, source)
        VALUES (?, ?)
    """, (prediction_json, source))

    conn.commit()
    conn.close()
    print("✅ Prediction saved successfully")


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
