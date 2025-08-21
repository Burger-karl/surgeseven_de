# qr_generator/management/commands/create_initial_qr_code.py
from django.core.management.base import BaseCommand
from qr_generator.models import QRCode
from qr_generator.utils import create_qr_code_image

class Command(BaseCommand):
    help = 'Creates an initial QR code for SurgeSeven'
    
    def handle(self, *args, **options):
        # Create or get the main QR code
        qr_code, created = QRCode.objects.get_or_create(
            name='surgeseven_main',
            defaults={
                'redirect_url': 'https://surgesevenltd.com',
                'is_active': True
            }
        )
        
        # Generate the QR code image
        create_qr_code_image(qr_code)
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('Successfully created initial QR code')
            )
        else:
            self.stdout.write('QR code already exists, updated image')