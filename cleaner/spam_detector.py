import os
import pickle
from django.conf import settings

MODEL_PATH = os.path.join(settings.BASE_DIR, "cleaner", "model", "spam_model.pkl")


class SpamDetector:
    def __init__(self):
        self.vectorizer = None
        self.model = None
        self.loaded = False
        self.load()

    def load(self):
        if not os.path.exists(MODEL_PATH):
            return
        with open(MODEL_PATH, "rb") as f:
            self.vectorizer, self.model = pickle.load(f)
        self.loaded = True

    def predict(self, text: str) -> dict:
        """
        Returns:
            {
                "is_spam": bool,
                "prob_spam": float,
                "prob_ham": float
            }
        """
        if not self.loaded:
            print("Model not loaded. Skipping prediction.")
            return {"is_spam": False, "prob_spam": 0.0, "prob_ham": 1.0}

        X = self.vectorizer.transform([text])
        proba = self.model.predict_proba(X)[0]
        return {
            "is_spam": bool(self.model.predict(X)[0]),
            "prob_spam": float(proba[1]),
            "prob_ham": float(proba[0])
        }


spam_detector = SpamDetector()
