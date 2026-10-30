from django.apps import AppConfig
class AppstoreConfig(AppConfig):
    name = 'appstore'

    def ready(self):
        from . import signals
