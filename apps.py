#!/usr/bin/env python
# coding: utf-8

# In[5]:


# ============================================================
# COLLEGE ENTRY EXIT SYSTEM (FINAL STABLE – HIGH ACCURACY)
# ============================================================

import os, cv2, sqlite3, threading, time
import numpy as np
import pandas as pd
from flask import Flask, request, render_template
from datetime import datetime
import mediapipe as mp

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

    con.commit()
    con.close()

init_db()

# ---------------- DATASET ----------------
df = pd.read_excel(DATA_PATH)
df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]

# ---------------- MEDIAPIPE FACE ----------------
mp_face = mp.solutions.face_mesh
face_mesh = mp_face.FaceMesh(refine_landmarks=True)

# ---------------- LAST SEEN CACHE ----------------
last_seen = {}  # To prevent duplicate IN/OUT marking in short interval

# ---------------- EMBEDDING EXTRACTION ----------------
def extract_embedding(img):
    # Resize to standard
    img = cv2.resize(img, (224, 224))
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    res = face_mesh.process(rgb)

    if not res.multi_face_landmarks:
        return None

    landmarks = res.multi_face_landmarks[0].landmark
    if len(landmarks) < 468:
        return None

    h, w, _ = img.shape
    pts = np.array([[lm.x * w, lm.y * h, lm.z * w] for lm in landmarks])
    pts -= pts.mean(axis=0)

    norm = np.linalg.norm(pts)
    if norm == 0:
        return None

    return pts.flatten() / norm

# ---------------- COSINE SIMILARITY ----------------
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# ---------------- FACE MATCH (MULTI IMAGE, HIGH ACCURACY) ----------------
def match_face(embedding, threshold=0.85):
    best_enroll = None
    best_score = -1

    for _, row in df.iterrows():
        enroll = str(row["ENROLLMENT_NO"])
        max_score_student = -1

        # Compare with all images of this student
        for img_name in os.listdir(IMAGE_DIR):
            if img_name.startswith(enroll):
                img_path = os.path.join(IMAGE_DIR, img_name)
                img = cv2.imread(img_path)
                if img is None:
                    continue

                ref_emb = extract_embedding(img)
                if ref_emb is None:
                    continue

                score = cosine_similarity(embedding, ref_emb)
                max_score_student = max(max_score_student, score)

        if max_score_student > best_score:
            best_score = max_score_student
            best_enroll = enroll

    return best_enroll if best_score >= threshold else None

# ---------------- SMS REMINDER (DUMMY) ----------------
def send_sms(phone, msg):
    print(f"📩 SMS to {phone}: {msg}")

def reminder_thread(enroll):
    time.sleep(1800)  # 30 minutes
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT current_status FROM Status WHERE enrollment=?", (enroll,))
    row = cur.fetchone()
    con.close()

    if row and row[0] == "OUTSIDE":
        matching_rows = df[df["ENROLLMENT_NO"].astype(str) == enroll]
        if not matching_rows.empty:
            s = matching_rows.iloc[0]
            send_sms(s.STUDENT_PHONE_NO, f"Reminder: {s.NAME}, please return to college.")

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/verify", methods=["POST"])
def verify():
    img = cv2.imdecode(np.frombuffer(request.files["frame"].read(), np.uint8), 1)
    emb = extract_embedding(img)

    if emb is None:
        return render_template("error.html", msg="❌ Face not detected. Please look straight at the camera.")

    enroll = match_face(emb)
    if enroll is None:
        return render_template("error.html", msg="❌ Student is not present in this college")

    matching_rows = df[df["ENROLLMENT_NO"].astype(str) == enroll]
    if matching_rows.empty:
        return render_template("error.html", msg=f"❌ Enrollment {enroll} not found in dataset")

    s = matching_rows.iloc[0]

    return render_template("result.html", enroll=enroll, name=s.NAME, dept=s.DEPARTMENT, year=s.YEAR)

@app.route("/mark/<action>/<enroll>")
def mark(action, enroll):
    # Prevent duplicate marks in <5 seconds
    now = time.time()
    if enroll in last_seen and now - last_seen[enroll] < 5:
        return render_template("error.html", msg="❌ Duplicate scan detected. Try again later.")
    last_seen[enroll] = now

    ts = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    matching_rows = df[df["ENROLLMENT_NO"].astype(str) == enroll]
    if matching_rows.empty:
        return render_template("error.html", msg=f"❌ Enrollment {enroll} not found in dataset")
    s = matching_rows.iloc[0]

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
        INSERT INTO GateLogs (enrollment, name, department, year, phone, action, timestamp)
        VALUES (?,?,?,?,?,?,?)
    """, (enroll, s.NAME, s.DEPARTMENT, s.YEAR, s.STUDENT_PHONE_NO, action, ts))

    cur.execute("""
        REPLACE INTO Status VALUES (?,?,?)
    """, (enroll, "OUTSIDE" if action == "EXIT" else "INSIDE", ts))

    con.commit()
    con.close()

    if action == "EXIT":
        threading.Thread(target=reminder_thread, args=(enroll,), daemon=True).start()

    return render_template("success.html", action=action, name=s.NAME, time=ts)

@app.route("/dashboard")
def dashboard():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    logs = con.execute("""
        SELECT g.*, s.current_status
        FROM GateLogs g
        LEFT JOIN Status s ON g.enrollment = s.enrollment
        ORDER BY g.id DESC
    """).fetchall()
    con.close()
    return render_template("dashboard.html", logs=logs)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)


# In[ ]:




