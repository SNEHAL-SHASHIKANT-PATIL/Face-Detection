# app.py - Face Verification (FaceMesh Only)
import os, cv2, numpy as np, pandas as pd, sqlite3
from flask import Flask, render_template, request
from datetime import datetime
import mediapipe as mp

app = Flask(__name__)

# -----------------------------
# PATHS
# -----------------------------
RAW_FACE_FOLDER = os.path.join('static', 'fixed_faces_cleaned')
DB_PATH = 'EntryExitData.db'
DATA_PATH = 'Dataset.csv.xlsx'

# -----------------------------
# DATABASE INIT
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS GateLogs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enrollment_no TEXT,
            name TEXT,
            department TEXT,
            year TEXT,
            action TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# LOAD DATASET
# -----------------------------
df = pd.read_excel(DATA_PATH)
df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]

# -----------------------------
# FACE MESH MODEL
# -----------------------------
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.75,
    min_tracking_confidence=0.75
)

# -----------------------------
# EXTRACT FACEMESH EMBEDDING
# -----------------------------
def extract_embedding_from_frame(img):
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)
    if not results.multi_face_landmarks:
        return None
    lms = results.multi_face_landmarks[0].landmark
    h, w, _ = img.shape
    pts = np.array([[lm.x*w, lm.y*h, lm.z*w] for lm in lms], dtype=np.float32)
    pts = pts - pts.mean(axis=0)
    norm = np.linalg.norm(pts)
    if norm==0:
        return None
    return pts.flatten()/norm

# -----------------------------
# MATCH FACE
# -----------------------------
def match_person(facemesh_emb, threshold=0.82):
    best_enroll = None
    best_score = -1
    for idx, row in df.iterrows():
        enroll = str(row["ENROLLMENT_NO"])
        img_path = os.path.join(RAW_FACE_FOLDER, f"{enroll}.jpg")
        if not os.path.exists(img_path):
            continue
        mesh_ref = extract_embedding_from_frame(cv2.imread(img_path))
        if mesh_ref is None:
            continue
        sim = np.dot(facemesh_emb, mesh_ref)/(np.linalg.norm(facemesh_emb)*np.linalg.norm(mesh_ref))
        if sim > best_score:
            best_score = sim
            best_enroll = enroll
    if best_score >= threshold:
        return best_enroll, best_score
    return None, best_score

# -----------------------------
# ROUTES
# -----------------------------
@app.route('/')
def home():
    return render_template("face_scan.html")

@app.route('/face_verify', methods=['POST'])
def face_verify():
    file = request.files.get("frame")
    if file is None:
        return "<h3>No frame received</h3>"

    arr = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    # --------------------------
    # EXTRACT EMBEDDING
    # --------------------------
    facemesh_emb = extract_embedding_from_frame(img)
    if facemesh_emb is None:
        return "<h3 style='color:#ffd800'>❌ No face detected</h3>"

    enroll, score = match_person(facemesh_emb)
    if enroll is None:
        return "<h3 style='color:red'>❌ You are NOT a registered member</h3>"

    student = df.loc[df["ENROLLMENT_NO"].astype(str) == str(enroll)].iloc[0]
    photo_rel = "/" + os.path.join(RAW_FACE_FOLDER, f"{enroll}.jpg").replace("\\","/")

    return render_template( "face_result.html",
        enroll=enroll,
        name=student.get("NAME","N/A"),
        dept=student.get("DEPARTMENT","N/A"),
        year=student.get("YEAR","N/A"),
        phone=student.get("STUDENT_PHONE_NO","N/A"),
        parent=student.get("PARENTS_PHONE_NO","N/A"),
        photo=photo_rel
    )

# -----------------------------
# ENTRY/EXIT
# -----------------------------
@app.route('/entry/<enroll>', methods=['POST'])
def mark_entry(enroll):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    student = df.loc[df["ENROLLMENT_NO"].astype(str) == str(enroll)].iloc[0]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO GateLogs(enrollment_no,name,department,year,action,timestamp)
                 VALUES (?,?,?,?,?,?)""",
              (enroll, student["NAME"], student["DEPARTMENT"], student["YEAR"], "ENTRY", ts))
    conn.commit()
    conn.close()
    return render_template("success.html", action="Entry", name=student["NAME"], enroll=enroll, timestamp=ts)

@app.route('/exit/<enroll>', methods=['POST'])
def mark_exit(enroll):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    student = df.loc[df["ENROLLMENT_NO"].astype(str) == str(enroll)].iloc[0]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO GateLogs(enrollment_no,name,department,year,action,timestamp)
                 VALUES (?,?,?,?,?,?)""",
              (enroll, student["NAME"], student["DEPARTMENT"], student["YEAR"], "EXIT", ts))
    conn.commit()
    conn.close()
    return render_template("success.html", action="Exit", name=student["NAME"], enroll=enroll, timestamp=ts)

# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
