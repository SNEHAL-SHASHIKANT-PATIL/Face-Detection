# app_match.py
import os, cv2, numpy as np, pandas as pd, sqlite3
from flask import Flask, render_template, request, render_template_string
from datetime import datetime
from deepface import DeepFace
from match_face import best_match, match_embedding

app = Flask(__name__)

RAW_FACE_FOLDER = os.path.join('static','fixed_faces')
DB_PATH = 'outpass.db'
DATA_PATH = 'Dataset.csv.xlsx'

# Load student dataset
df = pd.read_excel(DATA_PATH)
df.columns = [c.strip().replace(" ", "_").upper() for c in df.columns]

@app.route('/')
def home():
    return render_template('face_scan.html')

@app.route('/face_scan')
def face_scan():
    return render_template('face_scan.html')

@app.route('/face_verify', methods=['POST'])
def face_verify():
    file = request.files.get('frame')
    if file is None:
        return "No frame received", 400

    data = file.read()
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return "Invalid image", 400

    # Create embedding without forcing detection
    try:
        rep = DeepFace.represent(
            img_path=img,
            model_name='Facenet',
            enforce_detection=False,
            detector_backend='opencv'
        )
    except Exception as e:
        return f"<div style='color:#ffd800;font-weight:bold;'>Embedding failed: {e}</div>"

    # Extract embedding
    try:
        probe_vec = np.array(rep[0]["embedding"], dtype=np.float32)
    except:
        return "<div style='color:#ff6b6b;font-weight:bold;'>Embedding extract error!</div>"

    # Match
    enroll, best_sim, second_sim = best_match(probe_vec, threshold=0.45, gap=0.06)

    if enroll is None:
        return f"<div style='color:#ff6b6b;font-weight:bold;'>No match! best={best_sim:.3f}, second={second_sim:.3f}</div>"

    # Student record
    rec = df.loc[df['ENROLLMENT_NO'].astype(str) == str(enroll)]
    if rec.empty:
        return f"<div style='color:#ff6b6b;font-weight:bold;'>Matched {enroll} but record missing.</div>"

    rec = rec.iloc[0].to_dict()
    photo_rel = "/" + os.path.join(RAW_FACE_FOLDER, f"{enroll}.jpg").replace("\\","/")

    return render_template('face_result.html',
                           enroll=enroll,
                           name=rec.get('NAME','N/A'),
                           dept=rec.get('DEPARTMENT', rec.get('TRADE','N/A')),
                           year=rec.get('YEAR','N/A'),
                           phone=rec.get('MOBILE_NO', rec.get('STUDENT_PHONE_NO','N/A')),
                           parent=rec.get('PARENT_MOBILE', rec.get('PARENTS_PHONE_NO','N/A')),
                           photo=photo_rel)

# Entry / Exit logs
@app.route('/entry/<enroll>', methods=['POST'])
def mark_entry(enroll):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("INSERT INTO GateLogs (enrollment_no, action, timestamp) VALUES (?,?,?)",
              (enroll, 'ENTRY', ts))
    conn.commit(); conn.close()
    return render_template_string(f"<script>alert('ENTRY recorded for {enroll}');window.location.href='/face_scan';</script>")

@app.route('/exit/<enroll>', methods=['POST'])
def mark_exit(enroll):
    ts = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("INSERT INTO GateLogs (enrollment_no, action, timestamp) VALUES (?,?,?)",
              (enroll, 'EXIT', ts))
    conn.commit(); conn.close()
    return render_template_string(f"<script>alert('EXIT recorded for {enroll}');window.location.href='/face_scan';</script>")

if __name__ == "__main__":
    app.run(debug=True)
