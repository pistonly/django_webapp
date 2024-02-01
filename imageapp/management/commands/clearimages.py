from django.core.management.base import BaseCommand
from imageapp.models import Image

class Command(BaseCommand):
    help = 'clear image database'

    def handle(self, *args, **kwargs):
        Image.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Successfully clear images database'))

