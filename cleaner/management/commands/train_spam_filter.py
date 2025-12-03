import os
import pickle
from django.core.management.base import BaseCommand
from django.conf import settings

from cleaner.models import Message

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


MODEL_DIR = os.path.join(settings.BASE_DIR, "cleaner", "model")
MODEL_PATH = os.path.join(MODEL_DIR, "spam_model.pkl")


class Command(BaseCommand):
    help = "Train or retrain spam filter using spam + ham datasets"

    def handle(self, *args, **kwargs):
        os.makedirs(MODEL_DIR, exist_ok=True)

        spam = list(Message.objects.filter(is_spam=True).values_list("text", flat=True))
        ham = list(Message.objects.filter(is_spam=False).values_list("text", flat=True))

        if not spam or not ham:
            self.stdout.write(self.style.ERROR("Need both spam + ham samples."))
            return

        corpus = spam + ham
        labels = [1] * len(spam) + [0] * len(ham)

        russian_stop_words = ['и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она',
                              'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее',
                              'мне', 'было', 'вот', 'от', 'меня', 'еще', 'нет', 'о', 'из', 'ему']

        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words=russian_stop_words,
            ngram_range=(1, 2),
            min_df=1
        )

        X = vectorizer.fit_transform(corpus)
        model = LogisticRegression()
        model.fit(X, labels)

        # save model
        with open(MODEL_PATH, "wb") as f:
            pickle.dump((vectorizer, model), f)

        self.stdout.write(self.style.SUCCESS(
            f"Model trained. Spam: {len(spam)}, Ham: {len(ham)}"
        ))
