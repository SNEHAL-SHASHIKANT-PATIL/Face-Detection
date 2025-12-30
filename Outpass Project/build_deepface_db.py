import os
import cv2
import pickle
from deepface import DeepFace

# Folder path where student images stored
IMAGE_FOLDER = "static/fixed_faces"

embeddings = []

for filename in os.listdir(IMAGE_FOLDER):
    if filename.lower().endswith((".jpg", ".jpeg", ".png")):

        roll = filename.split(".")[0]   # Extract roll no from filename
        img_path = os.path.join(IMAGE_FOLDER, filename)

        try:
            rep = DeepFace.represent(img_path=img_path, model_name="Facenet")

            if isinstance(rep, list) and len(rep) > 0:
                embeddings.append({
                    "roll": roll,
                    "embedding": rep[0]["embedding"]
                })
                print(f"OK {roll}")

        except Exception as e:
            print(f"SKIP {roll} error: {e}")

# Save embeddings
with open("embeddings.pkl", "wb") as f:
    pickle.dump(embeddings, f)

print("\n🎉 Face DB Saved Successfully!")
print(f"Total embeddings: {len(embeddings)}")
