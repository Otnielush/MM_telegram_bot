from django.test import TestCase
from django.utils import timezone
from .models import Message
from .spam_detection import SpamDetector
import datetime


class SpamDetectionTest(TestCase):
    def setUp(self):
        # Create some sample spam messages
        self.spam_messages = [
            Message.objects.create(
                message_id=1,
                user_id=123,
                time_sent=timezone.now(),
                text="Buy cheap watches here! Best prices guaranteed www.spam.com"
            ),
            Message.objects.create(
                message_id=2,
                user_id=124,
                time_sent=timezone.now(),
                text="Make money fast! Work from home www.scam.com"
            ),
            Message.objects.create(
                message_id=3,
                user_id=125,
                time_sent=timezone.now(),
                text="Get rich quick! Investment opportunity www.fraud.com"
            )
        ]

        # Initialize spam detector with messages from database
        self.spam_detector = SpamDetector(threshold=0.7)
        spam_texts = list(Message.objects.values_list('text', flat=True))
        self.spam_detector.add_known_spam_messages(spam_texts)

    def test_similar_spam_detection(self):
        # Test message very similar to existing spam
        test_message = "Buy cheap watches here! Amazing prices www.spam.net"
        is_spam, similarity, spam_idx = self.spam_detector.check_message(test_message)

        self.assertTrue(is_spam)
        self.assertGreater(similarity, 0.7)
        self.assertEqual(self.spam_detector.get_similar_message(spam_idx),
                         self.spam_messages[0].text)

    def test_different_message_not_spam(self):
        # Test completely different message
        test_message = "When is the next Torah study session?"
        is_spam, similarity, spam_idx = self.spam_detector.check_message(test_message)

        self.assertFalse(is_spam)
        self.assertLess(similarity, 0.7)
        self.assertEqual(spam_idx, -1)

    def test_partially_similar_message(self):
        # Test message with some spam-like content but not exact match
        test_message = "Looking for work opportunities in programming"
        is_spam, similarity, spam_idx = self.spam_detector.check_message(test_message)

        self.assertFalse(is_spam)
        self.assertLess(similarity, 0.7)

    def test_empty_message(self):
        # Test empty message
        test_message = ""
        is_spam, similarity, spam_idx = self.spam_detector.check_message(test_message)

        self.assertFalse(is_spam)
        self.assertEqual(spam_idx, -1)

    def test_different_thresholds(self):
        # Test same message with different thresholds
        test_message = "Buy watches online! Great deals www.watches.com"

        # Strict threshold
        strict_detector = SpamDetector(threshold=0.9)
        strict_detector.add_known_spam_messages(list(Message.objects.values_list('text', flat=True)))
        is_spam_strict, similarity_strict, _ = strict_detector.check_message(test_message)

        # Lenient threshold
        lenient_detector = SpamDetector(threshold=0.5)
        lenient_detector.add_known_spam_messages(list(Message.objects.values_list('text', flat=True)))
        is_spam_lenient, similarity_lenient, _ = lenient_detector.check_message(test_message)

        # Lenient should detect more spam than strict
        self.assertGreaterEqual(similarity_lenient, similarity_strict)
        # Same similarity score for both detectors
        self.assertEqual(similarity_lenient, similarity_strict)

    def test_real_spam_messages(self):
        # Get real spam messages from the last 24 hours
        yesterday = timezone.now() - datetime.timedelta(days=1)
        recent_messages = Message.objects.filter(
            time_sent__gte=yesterday
        ).values_list('text', flat=True)

        if recent_messages.exists():
            # Create new detector with recent messages
            recent_detector = SpamDetector(threshold=0.7)
            recent_detector.add_known_spam_messages(list(recent_messages))

            # Test with a new similar message
            test_message = recent_messages[0].replace('www', 'wwww')
            is_spam, similarity, spam_idx = recent_detector.check_message(test_message)

            self.assertTrue(is_spam)
            self.assertGreater(similarity, 0.7)