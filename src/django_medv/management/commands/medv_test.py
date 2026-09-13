from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from medv_api import MedvClient

class Command(BaseCommand):
    help = "Проверка medv-api"

    def handle(self, *args, **options):
        client = MedvClient(settings.MEDV_CERT, settings.MEDV_KEY)
        resp = client.call_method("auth.check")
        print (resp.text)