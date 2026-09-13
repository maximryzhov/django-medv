from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from medv_api import MedvClient, MedvClientError

class Command(BaseCommand):
    help = "Проверка medv-api"

    def handle(self, *args, **options):
        client = MedvClient(settings.MEDV_CERT, settings.MEDV_KEY)

        print("Проверка доступности сервиса")
        try:
            client.ping_base_url()
        except MedvClientError as e:
            raise CommandError(e)
        print("Сервис доступен")


        print("Проверка сертификата и ключа")
        try:
            client.validate_credentials()
        except MedvClientError as e:
            raise CommandError(e)
        print("Сертификат и ключ валидны")
    
        resp = client.call_method("auth.check")
        print (resp.text)