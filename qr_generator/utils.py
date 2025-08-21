# qr_generator/utils.py
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.cache import cache
import os
from django.conf import settings
from .models import QRCode

def generate_qr_code_image(data, format=settings.QR_CODE_IMAGE_FORMAT):
    """
    Generate a QR code image from data
    """
    # Create QR code instance
    qr = qrcode.QRCode(
        version=settings.QR_CODE_VERSION,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=settings.QR_CODE_BOX_SIZE,
        border=settings.QR_CODE_BORDER,
    )
    
    # Add data to QR code
    qr.add_data(data)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(
        fill_color=settings.QR_CODE_FILL_COLOR,
        back_color=settings.QR_CODE_BACK_COLOR
    )
    
    # Save to bytes buffer
    buffer = BytesIO()
    img.save(buffer, format=format)
    buffer.seek(0)
    
    return buffer

def create_qr_code_image(qr_code_obj):
    """
    Create a QR code image for a QRCode object
    """
    # Generate the QR code
    buffer = generate_qr_code_image(qr_code_obj.redirect_url)
    
    # Create filename
    filename = f"{qr_code_obj.slug}.{settings.QR_CODE_IMAGE_FORMAT.lower()}"
    
    # Save to the QR code object
    if qr_code_obj.qr_code_image:
        # Remove old image if exists
        if os.path.isfile(qr_code_obj.qr_code_image.path):
            os.remove(qr_code_obj.qr_code_image.path)
    
    qr_code_obj.qr_code_image.save(filename, ContentFile(buffer.getvalue()), save=True)
    
    return qr_code_obj

def get_or_create_qr_code(name, redirect_url=None):
    """
    Get or create a QR code with caching
    """
    cache_key = f'qrcode_{name}'
    
    # Try to get from cache
    qr_code_obj = cache.get(cache_key)
    
    if qr_code_obj is None:
        # Try to get from database
        try:
            qr_code_obj = QRCode.objects.get(name=name)
        except QRCode.DoesNotExist:
            # Create new QR code
            qr_code_obj = QRCode.objects.create(
                name=name,
                redirect_url=redirect_url or settings.QR_CODE_DEFAULT_REDIRECT
            )
            qr_code_obj = create_qr_code_image(qr_code_obj)
        
        # Cache for 24 hours
        cache.set(cache_key, qr_code_obj, 60 * 60 * 24)
    
    return qr_code_obj