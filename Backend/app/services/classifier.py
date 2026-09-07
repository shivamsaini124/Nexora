import joblib
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

class Classifier:
    def __init__(self, model_path: str, encoder: SentenceTransformer):
        self.model = joblib.load(Path(model_path).expanduser())
        self.encoder = encoder

    def classify(self, userPrompt: str):
        embedding = self.encoder.encode(
            [userPrompt], normalize_embeddings=True
        )
        embedding = np.asarray(embedding)
        probabilities = self.model.predict_proba(embedding)[0]

        best_index = probabilities.argmax()

        return {
            "intent": self.model.classes_[best_index],
            "confidence": float(probabilities[best_index])
        }
