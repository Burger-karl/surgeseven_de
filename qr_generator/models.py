# qr_generator/models.py
from django.db import models
from django.core.cache import cache
import os
import uuid
from django.conf import settings
from django.urls import reverse

class QRCode(models.Model):
    name = models.CharField(max_length=255, unique=True, help_text="Unique identifier for this QR code")
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    redirect_url = models.URLField(default=settings.QR_CODE_DEFAULT_REDIRECT)
    qr_code_image = models.ImageField(upload_to='qr_codes/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = str(uuid.uuid4())[:8]  # Generate short unique slug
        
        # Delete cached QR code when saving
        cache_key = f'qrcode_{self.slug}'
        cache.delete(cache_key)
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Delete cached QR code when deleting
        cache_key = f'qrcode_{self.slug}'
        cache.delete(cache_key)
        
        # Delete the image file
        if self.qr_code_image:
            if os.path.isfile(self.qr_code_image.path):
                os.remove(self.qr_code_image.path)
        
        super().delete(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('qr_generator:redirect', kwargs={'slug': self.slug})
    
    class Meta:
        ordering = ['-created_at']