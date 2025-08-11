# from django.contrib.auth.backends import ModelBackend
# from django.contrib.auth import get_user_model

# import logging
# logger = logging.getLogger(__name__)

# class EmailBackend(ModelBackend):
#     def authenticate(self, request, username=None, password=None, **kwargs):
#         UserModel = get_user_model()
#         try:
#             user = UserModel.objects.get(email=username)
#             logger.info(f'User found: {user}')
#         except UserModel.DoesNotExist:
#             logger.error('User does not exist')
#             return None
#         else:
#             if user.check_password(password):
#                 logger.info('Password is correct')
#                 return user
#             else:
#                 logger.error('Password is incorrect')
#         return None



from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
import logging

logger = logging.getLogger(__name__)

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email=username)
            
            # Prevent unverified users from logging in
            if not user.is_verified:
                logger.warning(f'Login attempt for unverified user: {user.email}')
                raise PermissionDenied("Account not verified. Please check your email.")
                
            logger.info(f'Authentication attempt for: {user.email}')
        except UserModel.DoesNotExist:
            logger.error(f'User does not exist: {username}')
            return None
        
        if user.check_password(password):
            logger.info(f'Successful authentication for: {user.email}')
            return user
        else:
            logger.warning(f'Invalid password for: {user.email}')
            return None