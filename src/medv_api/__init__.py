import niquests

from .utils import (
    CertificateStatus,
    check_certificate_dates,
    check_certificate_matches_key,
    check_certificate_rsa,
    check_key_is_valid,
)


class MedvClientError(Exception):
    pass


class MedvClientCertificateError(MedvClientError):
    pass


class MedvClientConnectionError(MedvClientError):
    pass


class MedvClient:
    BASE_URL = "https://slb.medv.ru/api/v2/"

    def __init__(self, cert: str, key: str) -> None:
        self.cert = cert
        self.key = key

    def validate_credentials(self):
        """
        Проверяет валидность сертификата и ключа
        """
        if not check_certificate_rsa(self.cert):
            raise MedvClientCertificateError("Сертификат не содержит RSA ключ")

        if not check_key_is_valid(self.key):
            raise MedvClientCertificateError("Ключ не валиден")

        if not check_certificate_matches_key(self.cert, self.key):
            raise MedvClientCertificateError("Ключ и сертификат не совпадают")

        dates_check_result = check_certificate_dates(self.cert)
        if dates_check_result.status == CertificateStatus.NOT_YET_VALID:
            raise MedvClientCertificateError(
                f"Сертификат начнёт действовать с {dates_check_result.not_valid_before}"
            )
        elif dates_check_result.status == CertificateStatus.EXPIRED:
            raise MedvClientCertificateError(
                f"Срок действия сертификата истёк {dates_check_result.end_date}"
            )

    def ping_base_url(self) -> None:
        """
        Проверяет, что  сервис доступен
        даже если ответ 4xx или 5xx
        """
        try:
            response = niquests.get(self.BASE_URL)
        except niquests.exceptions.ConnectionError:
            raise MedvClientConnectionError("Нет соединения с сервером")

    def call_method(self, method_name: str) -> niquests.Response:
        payload = {
            "jsonrpc": "2.0",
            "method": method_name
        }

        response = niquests.post(
            self.BASE_URL,
            json=payload,
            cert=(self.cert, self.key)
        )

        return response
            