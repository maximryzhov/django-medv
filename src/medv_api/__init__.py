import json
import ssl
from contextlib import contextmanager
from http.client import HTTPException
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from .validators import (
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
    def __init__(self, response, request_id: str | None = None) -> None:
        self.status_code = response.getcode()
        self.headers = response.headers
        self.text = response.read().decode("utf-8", errors="replace")
        self.is_jsonrpc_response = False
        self.jsonrpc = None
        self.id = None
        self.result = None
        self.error_code = None
        self.error_message = None
        self.error_data = None

        if request_id is not None:
            self._parse_jsonrpc(request_id)

    def _parse_jsonrpc(self, request_id: str) -> None:
        try:
            payload = json.loads(self.text)
        except (TypeError, ValueError):
            return

        if not isinstance(payload, dict):
            return

        has_result = "result" in payload
        has_error = "error" in payload
        if (
            payload.get("jsonrpc") != "2.0"
            or payload.get("id") != request_id
            or has_result == has_error
        ):
            return

        if has_error:
            error = payload["error"]
            if not isinstance(error, dict) or "code" not in error or "message" not in error:
                return

        self.is_jsonrpc_response = True
        self.jsonrpc = payload["jsonrpc"]
        self.id = payload["id"]

        if has_result:
            self.result = payload["result"]
        else:
            self.error_code = error["code"]
            self.error_message = error["message"]
            self.error_data = error.get("data")


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
    def _authenticated_context(self):
        with TemporaryDirectory() as temp_dir:
            cert_path = Path(temp_dir) / "certificate.pem"
            key_path = Path(temp_dir) / "private-key.pem"
            cert_path.write_text(self.cert, encoding="utf-8")
            key_path.write_text(self.key, encoding="utf-8")

            context = ssl.create_default_context()
            context.load_cert_chain(
                certfile=str(cert_path),
                keyfile=str(key_path),
            )
            yield context

    def ping_base_url(self) -> None:
        """
        Проверяет, что  сервис доступен
        даже если ответ 4xx или 5xx
        """
        try:
            try:
                with urlopen(self.BASE_URL):
                    pass
            except HTTPError as response:
                response.close()
        except (URLError, HTTPException, OSError) as error:
            raise MedvClientConnectionError("Нет соединения с сервером") from error

    def call_method(self, method_name: str, body=None) -> MedvResponse:
        request_id = str(uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method_name,
        }
        if body is not None:
            payload["params"] = body

        request = Request(
            self.BASE_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with self._authenticated_context() as context:
                try:
                    with urlopen(request, context=context) as response:
                        return MedvResponse(response, request_id)
                except HTTPError as response:
                    with response:
                        return MedvResponse(response, request_id)
        except (URLError, HTTPException, OSError) as error:
            raise MedvClientConnectionError("Нет соединения с сервером") from error
