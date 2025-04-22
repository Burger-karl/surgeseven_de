# from django.apps import AppConfig


# class NotificationsConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'notifications'


from django.apps import AppConfig

class NotificationsConfig(AppConfig):
    name = 'notifications'

    def ready(self):
        import notifications.signals  

