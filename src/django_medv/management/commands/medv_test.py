from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from medv_api import MedvClient
from medv_api.utils import CertificateStatus, check_certificate_rsa, check_certificate_matches_key, check_certificate_dates, check_key_is_valid

class Command(BaseCommand):
    help = "Проверка medv-api"

    def handle(self, *args, **options):
        if not check_certificate_rsa(settings.MEDV_CERT):
            raise CommandError("Сертификат не содержит RSA ключ")
        else:
            print("Сертификат содержит RSA ключ")

        if not check_key_is_valid(settings.MEDV_KEY):
            raise CommandError("Ключ не валиден")
        else:
            print("Ключ валиден")
        
        if not check_certificate_matches_key(settings.MEDV_CERT, settings.MEDV_KEY):
            raise CommandError("Ключ и сертификат не совпадают")
        else:
            print("Сертификат и ключ совпадают")

        dates_check_result = check_certificate_dates(settings.MEDV_CERT)
        if dates_check_result.status == CertificateStatus.NOT_YET_VALID:
            raise CommandError(f"Сертификат начнёт действовать с {dates_check_result.not_valid_before}")
        elif dates_check_result.status == CertificateStatus.EXPIRED:
            raise CommandError(f"Срок действия сертификата истёк {dates_check_result.end_date}")
        else:
            print("Сертификат валиден")
        
        client = MedvClient(settings.MEDV_CERT, settings.MEDV_KEY)
        resp = client.call_method("auth.check")
        print (resp.text)