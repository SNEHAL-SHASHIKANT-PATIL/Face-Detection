# match_face.py
import pickle
import numpy as np
import os

# Path to embeddings file
EMB_FILE = "embeddings.pkl"

# Load embeddings list: expected format -> list of {"enroll": "242102...", "embedding": [ ... ] }
with open(EMB_FILE, "rb") as f:
    db = pickle.load(f)

# Normalize embeddings and prepare arrays for fast compare
enrollments = []
emb_matrix = []

for item in db:
    # adapt key name if different: use 'enroll' or 'roll' or 'ENROLLMENT_NO'
    enroll = item.get("enroll") or item.get("roll") or item.get("ENROLLMENT_NO")
    vec = np.array(item["embedding"], dtype=np.float32)
    # normalize vector (cosine similarity works better if vectors normalized)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
        enrollments.append(str(enroll))
        emb_matrix.append(vec)

if len(emb_matrix) == 0:
    raise SystemExit("No embeddings loaded from embeddings.pkl")

emb_matrix = np.vstack(emb_matrix)  # shape (N, D)

def match_embedding(probe_vec, top_k=5):
    """
    probe_vec: numpy array (un-normalized) or list
    returns: list of (enroll, sim) sorted desc
    """
    v = np.array(probe_vec, dtype=np.float32)
    nv = np.linalg.norm(v)
    if nv == 0:
        return []
    v = v / nv
    # compute cosine similarity = dot product because both normalized
    sims = emb_matrix.dot(v)  # shape (N,)
    # get top_k indices
    idx = np.argsort(-sims)[:top_k]
    return [(enrollments[i], float(sims[i])) for i in idx]

def best_match(probe_vec, threshold=0.45, gap=0.06):
    """
    returns (enroll, best_sim, second_sim) or (None, best_sim, second_sim) if no clear match
    threshold: min average similarity to accept
    gap: minimum difference between best and second
    """
    res = match_embedding(probe_vec, top_k=5)
    if not res:
        return None, 0.0, 0.0
    best_enroll, best_sim = res[0]
    second_sim = res[1][1] if len(res) > 1 else 0.0
    if best_sim >= threshold and (best_sim - second_sim) >= gap:
        return best_enroll, best_sim, second_sim
    return None, best_sim, second_sim
