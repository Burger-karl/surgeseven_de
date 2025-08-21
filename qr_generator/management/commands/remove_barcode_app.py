# management/commands/remove_barcode_app.py
from django.core.management.base import BaseCommand
from django.db import connection
import os
import shutil

class Command(BaseCommand):
    help = 'Completely removes the barcode app from the project'
    
    def handle(self, *args, **options):
        # Remove from INSTALLED_APPS (you'll need to do this manually)
        self.stdout.write("Please remove 'barcode_app' from INSTALLED_APPS in settings.py")
        
        # Remove URLs (you'll need to do this manually)
        self.stdout.write("Please remove barcode URLs from urls.py")
        
        # Drop database tables
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS barcode_app_barcode")
        
        # Remove migration records
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM django_migrations WHERE app = 'barcode_app'")
        
        # Remove app directory
        app_path = os.path.join(os.getcwd(), 'barcode_app')
        if os.path.exists(app_path):
            shutil.rmtree(app_path)
            self.stdout.write(self.style.SUCCESS('Removed barcode_app directory'))
        else:
            self.stdout.write(self.style.WARNING('barcode_app directory not found'))
        
        # Remove media files
        media_path = os.path.join(os.getcwd(), 'media', 'barcodes')
        if os.path.exists(media_path):
            shutil.rmtree(media_path)
            self.stdout.write(self.style.SUCCESS('Removed barcode media files'))
        else:
            self.stdout.write(self.style.WARNING('Barcode media directory not found'))
        
        self.stdout.write(self.style.SUCCESS('Barcode app removal completed'))