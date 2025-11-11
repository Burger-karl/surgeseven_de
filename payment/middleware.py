import logging
from django.http import HttpResponse

logger = logging.getLogger(__name__)

class PaystackIPWhitelistMiddleware:
    """
    Middleware to whitelist Paystack IP addresses for webhooks
    """
    PAYSTACK_IPS = {
        '52.31.139.75',
        '52.49.173.169', 
        '52.214.14.220'
    }
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        if request.path == '/paystack/webhook/':
            client_ip = self.get_client_ip(request)
            if client_ip not in self.PAYSTACK_IPS:
                logger.warning(f"Blocked webhook request from non-Paystack IP: {client_ip}")
                return HttpResponse(status=403)
                
        return self.get_response(request)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip