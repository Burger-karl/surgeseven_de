from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

import logging
logger = logging.getLogger(__name__)

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email=username)
            logger.info(f'User found: {user}')
        except UserModel.DoesNotExist:
            logger.error('User does not exist')
            return None
        else:
            if user.check_password(password):
                logger.info('Password is correct')
                return user
            else:
                logger.error('Password is incorrect')
        return None
