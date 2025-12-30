# generate_embeddings_facemesh.py
import os, cv2, numpy as np
import mediapipe as mp

SRC = "static/fixed_faces_cleaned"   # output of previous step
OUT = "embeddings_facemesh.npz"

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5)

embs = {}
for fname in os.listdir(SRC):
    if not fname.lower().endswith(('.jpg','.jpeg','.png')):
        continue
    enroll = os.path.splitext(fname)[0]
    path = os.path.join(SRC, fname)
    img = cv2.imread(path)
    if img is None:
        print("SKIP:", fname)
        continue
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)
    if not results.multi_face_landmarks:
        print("NO FACE:", fname)
        continue
    lms = results.multi_face_landmarks[0].landmark
    h,w,_ = img.shape
    pts = np.array([[lm.x * w, lm.y * h, lm.z * w] for lm in lms], dtype=np.float32)  # shape (468,3)
    pts -= pts.mean(axis=0)
    norm = np.linalg.norm(pts)
    if norm == 0:
        print("BAD NORM:", fname)
        continue
    vec = (pts / norm).flatten()   # length 468*3 = 1404
    embs[enroll] = vec
    print("Embed:", enroll)

if len(embs)==0:
    raise SystemExit("No embeddings generated. Check cleaned images and FaceMesh availability.")

# Save
np.savez_compressed(OUT, **embs)
print("Saved embeddings to", OUT)
