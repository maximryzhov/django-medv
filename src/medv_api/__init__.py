from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import urllib3

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


class MedvResponse:
    def __init__(self, response: urllib3.response.HTTPResponse) -> None:
        self.status_code = response.status
        self.headers = response.headers
        self.text = response.data.decode("utf-8", errors="replace")


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

    @contextmanager
    def _authenticated_pool(self):
        with TemporaryDirectory() as temp_dir:
            cert_path = Path(temp_dir) / "certificate.pem"
            key_path = Path(temp_dir) / "private-key.pem"
            cert_path.write_text(self.cert, encoding="utf-8")
            key_path.write_text(self.key, encoding="utf-8")

            pool = urllib3.PoolManager(
                cert_file=str(cert_path),
                key_file=str(key_path),
            )
            try:
                yield pool
            finally:
                pool.clear()

    def ping_base_url(self) -> None:
        """
        Проверяет, что  сервис доступен
        даже если ответ 4xx или 5xx
        """
        pool = urllib3.PoolManager()
        try:
            pool.request("GET", self.BASE_URL, preload_content=True)
        except urllib3.exceptions.HTTPError as error:
            raise MedvClientConnectionError("Нет соединения с сервером") from error
        finally:
            pool.clear()

    def call_method(self, method_name: str, body=None) -> MedvResponse:
        payload = {
            "jsonrpc": "2.0",
            "method": method_name
        }
        if body is not None:
            payload["params"] = body

        try:
            with self._authenticated_pool() as pool:
                response = pool.request(
                    "POST",
                    self.BASE_URL,
                    json=payload,
                    preload_content=True,
                )
        except urllib3.exceptions.HTTPError as error:
            raise MedvClientConnectionError("Нет соединения с сервером") from error

        return MedvResponse(response)
