# ============================================================
# COLLEGE ENTRY EXIT SYSTEM (HIGH ACCURACY – FACE RECOGNITION)
# ============================================================

import os
import cv2
import sqlite3
import threading
import time
import numpy as np
import pandas as pd
import face_recognition

from flask import Flask, request, render_template
from datetime import datetime

# ---------------- APP ----------------
app = Flask(__name__)

# ---------------- PATHS ----------------
DATA_PATH = "Dataset.csv.xlsx"
IMAGE_DIR = "static/images"
DB_PATH = "EntryExitData.db"

# ---------------- DATABASE ----------------
def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS GateLogs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enrollment TEXT,
        name TEXT,
        department TEXT,
        year TEXT,
        phone TEXT,
        action TEXT,
        timestamp TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS Status(
        enrollment TEXT PRIMARY KEY,
        current_status TEXT,
        last_time TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS Students(
        enrollment TEXT PRIMARY KEY,
        name TEXT,
        department TEXT,
        year TEXT,
        phone TEXT
    )
    """)

    con.commit()
    con.close()

init_db()

# ---------------- DATASET ----------------
df = pd.read_excel(DATA_PATH)
df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]


# ---------------- FACE ENCODING ----------------
def get_face_encoding(img):
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    boxes = face_recognition.face_locations(rgb, model="hog")

    if len(boxes) != 1:
        return None

    return face_recognition.face_encodings(rgb, boxes)[0]


# ---------------- load new student faces----------------
def load_known_faces():
    global known_encodings, known_enrollments

    known_encodings = []
    known_enrollments = []

    print("🔄 Reloading student faces...")

    for _, row in df.iterrows():
        enroll = str(row["ENROLLMENT_NO"])

        for img_name in os.listdir(IMAGE_DIR):
            if img_name.startswith(enroll):
                img = cv2.imread(os.path.join(IMAGE_DIR, img_name))
                if img is None:
                    continue

                enc = get_face_encoding(img)
                if enc is not None:
                    known_encodings.append(enc)
                    known_enrollments.append(enroll)

    print(f"✅ Loaded {len(known_encodings)} face encodings")


# ---------------- LOAD STUDENT FACES ----------------
known_encodings = []
known_enrollments = []

load_known_faces()


# print("🔄 Loading student faces...")

# for _, row in df.iterrows():
#     enroll = str(row["ENROLLMENT_NO"])

#     for img_name in os.listdir(IMAGE_DIR):
#         if img_name.startswith(enroll):
#             img = cv2.imread(os.path.join(IMAGE_DIR, img_name))
#             if img is None:
#                 continue

#             enc = get_face_encoding(img)
#             if enc is not None:
#                 known_encodings.append(enc)
#                 known_enrollments.append(enroll)

# print(f"✅ Loaded {len(known_encodings)} face samples")


# ---------------- FACE MATCH ----------------
def match_face_live(live_encoding, tolerance=0.45):
    matches = face_recognition.compare_faces(
        known_encodings, live_encoding, tolerance
    )

    if True not in matches:
        return None

    distances = face_recognition.face_distance(
        known_encodings, live_encoding
    )

    return known_enrollments[np.argmin(distances)]

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/verify", methods=["POST"])
def verify():

    if "frame" not in request.files:
        return render_template("error.html", msg="❌ No image received")

    file = request.files["frame"]
    if file.filename == "":
        return render_template("error.html", msg="❌ No image selected")

    img = cv2.imdecode(
        np.frombuffer(file.read(), np.uint8), 1
    )

    live_enc = get_face_encoding(img)
    if live_enc is None:
        return render_template(
            "error.html", msg="❌ Exactly ONE face required"
        )

    enroll = match_face_live(live_enc)
    if enroll is None:
        return render_template(
            "error.html", msg="❌ Student not registered"
        )

    s = df[df["ENROLLMENT_NO"].astype(str) == enroll].iloc[0]

    return render_template(
        "result.html",
        enroll=enroll,
        name=s.NAME,
        dept=s.DEPARTMENT,
        year=s.YEAR
    )

@app.route("/mark/<action>/<enroll>")
def mark(action, enroll):
    ts = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    s = df[df["ENROLLMENT_NO"].astype(str) == enroll].iloc[0]

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
    INSERT INTO GateLogs VALUES (NULL,?,?,?,?,?,?,?)
    """, (
        enroll,
        s.NAME,
        s.DEPARTMENT,
        s.YEAR,
        s.STUDENT_PHONE_NO,
        action,
        ts
    ))

    cur.execute("""
    REPLACE INTO Status VALUES (?,?,?)
    """, (
        enroll,
        "OUTSIDE" if action == "EXIT" else "INSIDE",
        ts
    ))

    con.commit()
    con.close()

    return render_template(
        "success.html",
        action=action,
        name=s.NAME,
        time=ts
    )

@app.route("/add_student")
def add_student():
    return render_template("add_student.html")


@app.route("/dashboard")
def dashboard():

    # 🔹 1. calendar & search input घ्या
    selected_date = request.args.get("date")
    search = request.args.get("search", "").strip()

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    # 🔹 2. base query
    query = """
    SELECT g.*, s.current_status
    FROM GateLogs g
    LEFT JOIN Status s ON g.enrollment = s.enrollment
    WHERE 1=1
    """
    params = []

    # 🔹 3. date filter (calendar)
    if selected_date:
        d = datetime.strptime(selected_date, "%Y-%m-%d").strftime("%d-%m-%Y")
        query += " AND g.timestamp LIKE ?"
        params.append(f"{d}%")

    # 🔹 4. student search (name / enrollment / phone)
    if search:
        query += """
        AND (
            g.enrollment LIKE ?
            OR g.name LIKE ?
            OR g.phone LIKE ?
        )
        """
        params.extend([
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ])

    query += " ORDER BY g.id DESC"

    logs = con.execute(query, params).fetchall()
    con.close()

    return render_template(
        "dashboard.html",
        logs=logs,
        selected_date=selected_date
    )

@app.route('/student/<enroll>')
def student_info(enroll):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name, department, year FROM Students WHERE enrollment=?",
        (enroll,)
    )
    student = cursor.fetchone()

    conn.close()

    if not student:
        return "Student not found"

    name, dept, year = student

    # student photos path
    image_folder = f"static/dataset/{enroll}"
    images = []

    if os.path.exists(image_folder):
        images = os.listdir(image_folder)

    return render_template(
        "student_info.html",
        name=name,
        department=dept,
        year=year,
        images=images,
        enroll=enroll
    )

import base64
from flask import jsonify

# @app.route("/save_student_camera", methods=["POST"])
# def save_student_camera():

#     data = request.get_json(force=True)

#     enroll = data["enroll"]
#     name = data["name"]
#     dept = data["dept"]
#     year = data["year"]
#     phone = data["phone"]
#     images = data["images"]

#     # Save images
#     for i, img_data in enumerate(images):
#         img_bytes = base64.b64decode(img_data.split(",")[1])
#         filename = f"{enroll}_{i+1}.jpg"
#         with open(os.path.join(IMAGE_DIR, filename), "wb") as f:
#             f.write(img_bytes)

#     # Save student info to dataset
#     new_row = {
#         "ENROLLMENT_NO": enroll,
#         "NAME": name,
#         "DEPARTMENT": dept,
#         "YEAR": year,
#         "STUDENT_PHONE_NO": phone
#     }

#     global df
#     df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
#     df.to_excel(DATA_PATH, index=False)

#     load_known_faces()   # 👈 ही line ADD कर

#     return jsonify({"msg": "✅ Student added successfully"})

@app.route("/save_student_camera", methods=["POST"])
def save_student_camera():
    try:
        data = request.get_json(force=True)

        enroll = data.get("enroll")
        name   = data.get("name")
        dept   = data.get("dept")
        year   = data.get("year")
        phone  = data.get("phone")
        images = data.get("images", [])

        # 🔒 Basic validation
        if not all([enroll, name, dept, year, phone]) or len(images) == 0:
            return jsonify({
                "status": "error",
                "msg": "❌ Missing student data or images"
            }), 400

        # 1️⃣ Save images
        for i, img_data in enumerate(images):
            img_bytes = base64.b64decode(img_data.split(",")[1])
            filename = f"{enroll}_{i+1}.jpg"
            with open(os.path.join(IMAGE_DIR, filename), "wb") as f:
                f.write(img_bytes)

        # 2️⃣ Save student to DATABASE
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()

        cur.execute("""
            INSERT OR REPLACE INTO Students
            (enrollment, name, department, year, phone)
            VALUES (?,?,?,?,?)
        """, (enroll, name, dept, year, phone))

        con.commit()
        con.close()

        # 3️⃣ Save student to Excel
        new_row = {
            "ENROLLMENT_NO": enroll,
            "NAME": name,
            "DEPARTMENT": dept,
            "YEAR": year,
            "STUDENT_PHONE_NO": phone
        }

        global df
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_excel(DATA_PATH, index=False)

        # 4️⃣ Reload face encodings
        load_known_faces()

        # ✅ SUCCESS RESPONSE
        return jsonify({
            "status": "success",
            "msg": "✅ Student added successfully"
        })

    except Exception as e:
        print("❌ ERROR saving student:", e)
        return jsonify({
            "status": "error",
            "msg": "❌ Error saving student"
        }), 500

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)