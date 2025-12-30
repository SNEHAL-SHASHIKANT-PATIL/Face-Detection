# new.py  (FaceMesh embeddings matcher)
import os, cv2, numpy as np, pandas as pd, sqlite3
from flask import Flask, render_template, request, render_template_string
from datetime import datetime
import mediapipe as mp

app = Flask(__name__)
RAW_FACE_FOLDER = os.path.join('static','fixed_faces_cleaned')  # use cleaned images for display
DB_PATH = 'outpass.db'
DATA_PATH = 'Dataset.csv.xlsx'
EMB_FILE = 'embeddings_facemesh.npz'

# load student csv
df = pd.read_excel(DATA_PATH)
df.columns = [c.strip().replace(" ", "_").upper() for c in df.columns]

# load embeddings
npz = np.load(EMB_FILE, allow_pickle=True)
known_embeddings = {k: npz[k] for k in npz.files}
print("Loaded embeddings:", len(known_embeddings))

# mediapipe face mesh (for live frame)
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5)

def extract_embedding_from_frame(img):
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)
    if not results.multi_face_landmarks:
        return None
    lms = results.multi_face_landmarks[0].landmark
    h,w,_ = img.shape
    pts = np.array([[lm.x * w, lm.y * h, lm.z * w] for lm in lms], dtype=np.float32)
    pts -= pts.mean(axis=0)
    norm = np.linalg.norm(pts)
    if norm == 0:
        return None
    return (pts / norm).flatten()

def match_embedding(emb, threshold=0.50):
    # using cosine similarity
    best = None
    best_sim = -1.0
    for enroll, ref in known_embeddings.items():
        sim = np.dot(emb, ref) / (np.linalg.norm(emb) * np.linalg.norm(ref))
        if sim > best_sim:
            best_sim = sim
            best = enroll
    print("Best sim", best_sim, "best", best)
    if best_sim >= threshold:
        return best, float(best_sim)
    return None, float(best_sim)

@app.route('/')
def home():
    return render_template('face_scan.html')

@app.route('/face_scan')
def face_scan_page():
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
    emb = extract_embedding_from_frame(img)
    if emb is None:
        return "<div style='color:#ffd800;font-weight:bold;'>No face detected in frame.</div>"
    enroll, sim = match_embedding(emb, threshold=0.75)   # tweak threshold
    if enroll is None:
        return f"<div style='color:#ff6b6b;font-weight:bold;'>No matching student found. Best sim={sim:.3f}</div>"
    student = df.loc[df['ENROLLMENT_NO'].astype(str) == str(enroll)]
    if student.empty:
        return f"<div style='color:#ff6b6b;font-weight:bold;'>Matched {enroll} but student record missing.</div>"
    rec = student.iloc[0].to_dict()
    photo_rel = "/" + os.path.join(RAW_FACE_FOLDER, f"{enroll}.jpg").replace("\\","/")
    return render_template('face_result.html',
                           enroll=enroll,
                           name=rec.get('NAME','N/A'),
                           dept=rec.get('DEPARTMENT', rec.get('TRADE','N/A')),
                           year=rec.get('YEAR','N/A'),
                           phone=rec.get('MOBILE_NO', rec.get('STUDENT_PHONE_NO','N/A')),
                           parent=rec.get('PARENT_MOBILE', rec.get('PARENTS_PHONE_NO','N/A')),
                           photo=photo_rel)

# entry/exit same as before...
@app.route('/entry/<enroll>', methods=['POST'])
def mark_entry(enroll):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("INSERT INTO GateLogs (enrollment_no, action, timestamp) VALUES (?,?,?)", (enroll, 'ENTRY', ts))
    conn.commit(); conn.close()
    return render_template_string(f"<script>alert('ENTRY recorded for {enroll}');window.location.href='/face_scan';</script>")

@app.route('/exit/<enroll>', methods=['POST'])
def mark_exit(enroll):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("INSERT INTO GateLogs (enrollment_no, action, timestamp) VALUES (?,?,?)", (enroll, 'EXIT', ts))
    conn.commit(); conn.close()
    return render_template_string(f"<script>alert('EXIT recorded for {enroll}');window.location.href='/face_scan';</script>")

if __name__ == "__main__":
    app.run(debug=True)
