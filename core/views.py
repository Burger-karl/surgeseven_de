from django.shortcuts import render
import logging

logger = logging.getLogger(__name__)

# Create your views here.

def handler400(request, exception):
    logger.error(f'Bad Request: {exception}')
    return render(request, 'errors/400.html', status=400)

def handler403(request, exception):
    logger.error(f'Permission Denied: {exception}')
    return render(request, 'errors/403.html', status=403)

def handler404(request, exception):
    logger.error(f'Page Not Found: {request.path}')
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    logger.critical('Server Error (500)')
    return render(request, 'errors/500.html', status=500)