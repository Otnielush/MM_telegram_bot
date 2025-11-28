from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import List, Tuple


class SpamDetector:
    def __init__(self, threshold: float = 0.8):
        """
        Initialize spam detector with similarity threshold

        Args:
            threshold: Cosine similarity threshold above which messages are considered similar
        """
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words='english',
            min_df=1,  # Include terms that appear in at least 1 document
            max_df=0.9  # Exclude terms that appear in more than 90% of documents
        )
        self.threshold = threshold
        self.message_vectors = None
        self.messages = []

    def add_known_spam_messages(self, spam_messages: List[str]) -> None:
        """
        Add known spam messages to the detector's database

        Args:
            spam_messages: List of known spam message texts
        """
        self.messages = spam_messages
        self.message_vectors = self.vectorizer.fit_transform(spam_messages)

    def check_message(self, new_message: str) -> Tuple[bool, float, int]:
        """
        Check if a new message is similar to known spam messages

        Args:
            new_message: Text of the message to check

        Returns:
            Tuple containing:
            - is_spam: Boolean indicating if message is considered spam
            - max_similarity: Highest similarity score found
            - similar_message_idx: Index of the most similar spam message (-1 if none)
        """
        if not self.messages:
            return False, 0.0, -1

        # Transform new message using existing vocabulary
        new_vector = self.vectorizer.transform([new_message])

        # Calculate cosine similarity between new message and all spam messages
        similarities = cosine_similarity(new_vector, self.message_vectors).flatten()

        # Find highest similarity score and its index
        max_similarity = similarities.max()
        similar_message_idx = similarities.argmax()

        is_spam = max_similarity >= self.threshold

        return is_spam, max_similarity, similar_message_idx if is_spam else -1

    def get_similar_message(self, index: int) -> str:
        """
        Get the text of a spam message by index

        Args:
            index: Index of the spam message to retrieve

        Returns:
            Text of the requested spam message
        """
        if 0 <= index < len(self.messages):
            return self.messages[index]
        return ""