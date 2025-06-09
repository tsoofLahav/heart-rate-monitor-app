from flask import Blueprint, request, jsonify
import pyodbc
import os
import threading
import globals
import json

# --- Setup Blueprint ---
data_bp = Blueprint("data", __name__)
session_id_lock = threading.Lock()

# --- Database connection setup ---
os.environ["DB_CONNECTION_STRING"] = (
    "Driver={ODBC Driver 18 for SQL Server};Server=tcp:heart-monitor-server.privatelink.database.windows.net,"
    "1433;Database=heart-monitor-db;Uid=heart-monitor-server-admin;Pwd=#ass101223;Encrypt=yes;TrustServerCertificate"
    "=yes;Connection Timeout=30;")

def get_db_connection():
    db_conn_str = os.getenv("DB_CONNECTION_STRING")
    if not db_conn_str:
        raise ValueError("DB_CONNECTION_STRING is not set or empty")
    return pyodbc.connect(db_conn_str)

# --- Start Session ---
@data_bp.route('/start_session', methods=['POST'])
def start_session():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get next session ID (highest + 1)
    cursor.execute("SELECT ISNULL(MAX(session_id), 0) + 1 FROM sessions")
    session_id = cursor.fetchone()[0]

    # Insert new session start time
    cursor.execute("INSERT INTO sessions (session_id, start_time) VALUES (?, GETDATE())", (session_id,))
    conn.commit()
    conn.close()

    globals.session_id = session_id
    globals.reset_all()

    return jsonify({"session_id": session_id})

# --- Save prediction peaks per round ---
def save_prediction_to_db(predicted_peaks):
    if not isinstance(predicted_peaks, list):
        raise ValueError("predicted_peaks must be a list")

    session_id = globals.session_id
    round_number = globals.round_count
    peaks_json = json.dumps(predicted_peaks)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO prediction_peaks (session_id, round_number, peaks) VALUES (?, ?, ?)",
        (session_id, round_number, peaks_json)
    )
    conn.commit()
    conn.close()
    print(f"✅ Round {round_number} prediction saved for session {session_id}")

# --- End Session ---
@data_bp.route('/end_session', methods=['POST'])
def end_session():
    session_id = globals.session_id

    conn = get_db_connection()
    cursor = conn.cursor()

    # Update session with end time
    cursor.execute("UPDATE sessions SET end_time = GETDATE() WHERE session_id = ?", (session_id,))

    conn.commit()
    conn.close()
    globals.reset_all()

    return jsonify({"message": "Session ended"})