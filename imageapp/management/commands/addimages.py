from django.core.management.base import BaseCommand
from imageapp.scripts import add_images_to_database  # 导入上面的函数


class Command(BaseCommand):
    help = "Add images from a folder to the Image model"

    def handle(self, *args, **kwargs):
        add_images_to_database()
        self.stdout.write(self.style.SUCCESS("Successfully added images to database"))
