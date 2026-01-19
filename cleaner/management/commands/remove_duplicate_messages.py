from django.core.management.base import BaseCommand
from django.db.models import Count, Min
from cleaner.models import Message

class Command(BaseCommand):
    help = 'Delete messages with duplicated text, keeping only the first one'

    def handle(self, *args, **options):
        # Find texts that appear more than once
        duplicates = (
            Message.objects.values('text')
            .annotate(text_count=Count('id'), min_id=Min('id'))
            .filter(text_count__gt=1)
        )

        total_deleted = 0
        for entry in duplicates:
            text_value = entry['text']
            keep_id = entry['min_id']

            # Delete all messages with this text except the one we want to keep
            deleted_count, _ = Message.objects.filter(text=text_value).exclude(id=keep_id).delete()
            total_deleted += deleted_count

        if total_deleted > 0:
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted {total_deleted} duplicate messages'))
        else:
            self.stdout.write(self.style.SUCCESS('No duplicates found'))
