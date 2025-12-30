# preprocess_images.py
import os, cv2, numpy as np
import mediapipe as mp

SRC = "static/fixed_faces"
DST = "static/fixed_faces_cleaned"
os.makedirs(DST, exist_ok=True)

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True)

def clahe_rgb(img):
    # apply CLAHE to each channel in LAB or to V in HSV
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l,a,b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    l2 = clahe.apply(l)
    lab2 = cv2.merge((l2,a,b))
    return cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)

def align_by_eyes(img, landmarks):
    # landmarks: mediapipe landmarks list, we use left and right eye centers
    h, w = img.shape[:2]
    # indices for left/right eye approximate (use averaged points)
    left_idxs = [33, 133]   # approximate landmarks around left eye
    right_idxs = [362, 263] # approximate landmarks around right eye
    pts = np.array([[lm.x * w, lm.y * h] for lm in landmarks])
    left_center = pts[left_idxs].mean(axis=0)
    right_center = pts[right_idxs].mean(axis=0)
    # compute angle
    dx = right_center[0] - left_center[0]
    dy = right_center[1] - left_center[1]
    angle = np.degrees(np.arctan2(dy, dx))
    # rotate image to make eyes horizontal
    center = tuple(np.array((w/2, h/2)))
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC)
    return rotated

for fname in os.listdir(SRC):
    if not fname.lower().endswith(('.jpg','.jpeg','.png')):
        continue
    src_path = os.path.join(SRC, fname)
    dst_path = os.path.join(DST, fname)
    img = cv2.imread(src_path)
    if img is None:
        print("SKIP (cannot read):", fname)
        continue
    # 1) convert to RGB-equivalent BGR (OpenCV uses BGR)
    # 2) enhance contrast with CLAHE
    enhanced = clahe_rgb(img)
    # 3) try to align using FaceMesh
    rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)
    if results.multi_face_landmarks:
        lm = results.multi_face_landmarks[0].landmark
        try:
            aligned = align_by_eyes(enhanced, lm)
        except Exception as e:
            aligned = enhanced
    else:
        aligned = enhanced
    # 4) final resize and save as 8-bit JPEG
    final = cv2.resize(aligned, (256, 256))
    cv2.imwrite(dst_path, final, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    print("Saved:", dst_path)
print("Preprocessing done.")
