# qr_generator/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse, FileResponse
from django.core.cache import cache
from .models import QRCode
from .utils import get_or_create_qr_code, create_qr_code_image, generate_qr_code_image
import os
from django.conf import settings

class QRCodeRedirectView(View):
    def get(self, request, slug):
        # Get QR code from cache or database
        cache_key = f'qrcode_{slug}'
        qr_code_obj = cache.get(cache_key)
        
        if qr_code_obj is None:
            try:
                qr_code_obj = QRCode.objects.get(slug=slug)
                # Cache for 24 hours
                cache.set(cache_key, qr_code_obj, 60 * 60 * 24)
            except QRCode.DoesNotExist:
                return render(request, 'qr_generator/404.html', status=404)
        
        # Redirect to the URL
        return redirect(qr_code_obj.redirect_url)

class QRCodeDownloadView(View):
    def get(self, request, slug):
        # Get QR code
        qr_code_obj = get_object_or_404(QRCode, slug=slug)
        
        if not qr_code_obj.qr_code_image:
            # Generate image if it doesn't exist
            qr_code_obj = create_qr_code_image(qr_code_obj)
        
        # Serve the image file for download
        response = FileResponse(qr_code_obj.qr_code_image.open(), as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="{qr_code_obj.slug}.{settings.QR_CODE_IMAGE_FORMAT.lower()}"'
        return response

class QRCodeListView(LoginRequiredMixin, ListView):
    model = QRCode
    template_name = 'qr_generator/qr_code_list.html'
    context_object_name = 'qr_codes'
    paginate_by = 20

class QRCodeCreateView(LoginRequiredMixin, CreateView):
    model = QRCode
    template_name = 'qr_generator/qr_code_form.html'
    fields = ['name', 'redirect_url', 'is_active']
    success_url = reverse_lazy('qr_generator:list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Generate QR code image after saving
        create_qr_code_image(self.object)
        return response

class QRCodeDetailView(LoginRequiredMixin, DetailView):
    model = QRCode
    template_name = 'qr_generator/qr_code_detail.html'
    context_object_name = 'qr_code'

class QRCodeUpdateView(LoginRequiredMixin, UpdateView):
    model = QRCode
    template_name = 'qr_generator/qr_code_form.html'
    fields = ['name', 'redirect_url', 'is_active']
    
    def get_success_url(self):
        return reverse_lazy('qr_generator:detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Regenerate QR code image if redirect_url changed
        if 'redirect_url' in form.changed_data:
            create_qr_code_image(self.object)
        return response

class QRCodeDeleteView(LoginRequiredMixin, DeleteView):
    model = QRCode
    template_name = 'qr_generator/qr_code_confirm_delete.html'
    success_url = reverse_lazy('qr_generator:list')

class QRCodeAPIView(View):
    def get(self, request, slug):
        # API endpoint to get QR code data
        qr_code_obj = get_object_or_404(QRCode, slug=slug)
        
        return JsonResponse({
            'name': qr_code_obj.name,
            'slug': qr_code_obj.slug,
            'redirect_url': qr_code_obj.redirect_url,
            'image_url': request.build_absolute_uri(qr_code_obj.qr_code_image.url) if qr_code_obj.qr_code_image else None,
            'created_at': qr_code_obj.created_at.isoformat(),
            'updated_at': qr_code_obj.updated_at.isoformat(),
        })