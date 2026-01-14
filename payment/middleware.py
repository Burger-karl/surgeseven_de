# import logging
# from django.http import HttpResponse

# logger = logging.getLogger(__name__)

# class PaystackIPWhitelistMiddleware:
#     """
#     Middleware to whitelist Paystack IP addresses for webhooks
#     """
#     PAYSTACK_IPS = {
#         '52.31.139.75',
#         '52.49.173.169', 
#         '52.214.14.220'
#     }
    
#     def __init__(self, get_response):
#         self.get_response = get_response
        
#     def __call__(self, request):
#         if request.path == '/paystack/webhook/':
#             client_ip = self.get_client_ip(request)
#             if client_ip not in self.PAYSTACK_IPS:
#                 logger.warning(f"Blocked webhook request from non-Paystack IP: {client_ip}")
#                 return HttpResponse(status=403)
                
#         return self.get_response(request)
    
#     def get_client_ip(self, request):
#         x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
#         if x_forwarded_for:
#             ip = x_forwarded_for.split(',')[0]
#         else:
#             ip = request.META.get('REMOTE_ADDR')
#         return ip
    


import logging
from django.http import HttpResponse
from ipaddress import ip_network, ip_address
from django.conf import settings

logger = logging.getLogger(__name__)

class PaystackIPWhitelistMiddleware:
    """
    Secure middleware for Paystack IP whitelisting
    """
    # Paystack IP ranges (check current ranges from Paystack docs)
    PAYSTACK_CIDRS = [
        '52.31.0.0/16',  # Europe West 1
        '52.49.0.0/16',  # Europe West 1
        '52.214.0.0/16', # Europe West 1
        # Add more CIDRs from Paystack documentation
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.paystack_networks = [ip_network(cidr) for cidr in self.PAYSTACK_CIDRS]
        
    def __call__(self, request):
        if request.path == '/paystack/webhook/':
            client_ip = self.get_client_ip(request)
            
            if not self.is_paystack_ip(client_ip):
                logger.warning(f"Blocked webhook request from unauthorized IP: {client_ip}")
                logger.warning(f"Request headers: {dict(request.headers)}")
                return HttpResponse(status=403)
                
        return self.get_response(request)
    
    def get_client_ip(self, request):
        """Secure method to get real client IP"""
        # Get IP from REMOTE_ADDR first (most reliable)
        ip = request.META.get('REMOTE_ADDR')
        
        # If behind proxy, ensure you trust the proxy and check X-Real-IP
        # Never use X-Forwarded-For for security decisions unless you validate proxy chain
        if not ip and settings.TRUSTED_PROXY:
            ip = request.META.get('HTTP_X_REAL_IP', request.META.get('REMOTE_ADDR'))
        
        return ip
    
    def is_paystack_ip(self, ip_str):
        """Check if IP is in Paystack's range"""
        try:
            ip = ip_address(ip_str)
            for network in self.paystack_networks:
                if ip in network:
                    return True
            return False
        except ValueError:
            return False