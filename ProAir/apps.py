from django.apps import AppConfig


class ProairConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ProAir'

    
    def ready(self):
        import ProAir.signals
