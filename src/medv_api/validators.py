# Содержит функции проверки ключа и сертификата на валидность

import base64
import ssl
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory


# ENUM с тремя результатами проверки: валиден, ещё не валиден, просрочен
class CertificateStatus(Enum):
    VALID = "VALID"
    NOT_YET_VALID = "NOT_YET_VALID"
    EXPIRED = "EXPIRED"


# DTO-класс - результат проверки дат
@dataclass
class CertificateDatesCheckResult:
    status: CertificateStatus
    start_date: datetime
    end_date: datetime


def _extract_pem(contents: str, label: str) -> str | None:
    """
    Вытаскиваем PEM-сертификат из .crt-файла
    """
    begin = f"-----BEGIN {label}-----"
    end = f"-----END {label}-----"
    start_index = contents.find(begin)
    if start_index == -1:
        return None

    end_index = contents.find(end, start_index)
    if end_index == -1:
        return None

    return contents[start_index : end_index + len(end)] + "\n"


def _extract_private_key(key_contents: str) -> str | None:
    for label in ("PRIVATE KEY", "RSA PRIVATE KEY", "EC PRIVATE KEY", "DSA PRIVATE KEY"):
        key = _extract_pem(key_contents, label)
        if key is not None:
            return key

    return None


@contextmanager
def _temporary_pem_files(cert_contents: str, key_contents: str | None = None):
    """
    Временно записывает содержимое cert и key в файлы в temp_dir,
    т.к. мы не храним пути к файлу
    """
    with TemporaryDirectory() as temp_dir:
        cert_path = Path(temp_dir) / "certificate.pem"
        cert = _extract_pem(cert_contents, "CERTIFICATE") or cert_contents
        cert_path.write_text(cert, encoding="utf-8")

        key_path = None
        if key_contents is not None:
            key_path = Path(temp_dir) / "private-key.pem"
            key = _extract_private_key(key_contents) or key_contents
            key_path.write_text(key, encoding="utf-8")

        yield cert_path, key_path


def check_certificate_rsa(cert_contents: str) -> bool:
    """
    Проверяем, что сертификат содержит RSA ключ
    """
    cert = _extract_pem(cert_contents, "CERTIFICATE")
    if cert is None:
        return False

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    try:
        context.load_verify_locations(cadata=cert)
    except ssl.SSLError, ValueError:
        return False

    return True


def check_key_is_valid(key_contents: str) -> bool:
    # Если ключ валидная base64 строка - он валиден
    key = _extract_private_key(key_contents)
    if key is None:
        return False
    body = "".join(key_contents.strip().splitlines()[1:-1])
    try:
        base64.b64decode(body, validate=True)
    except ValueError, TypeError:
        return False

    return bool(body)


def check_certificate_matches_key(cert_contents: str, key_contents: str) -> bool:
    """
    Проверяет, что сертификат и ключ из одной пары
    """
    try:
        with _temporary_pem_files(cert_contents, key_contents) as (
            cert_path,
            key_path,
        ):
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_cert_chain(
                certfile=str(cert_path),
                keyfile=str(key_path),
                password=lambda: "",
            )
    except ssl.SSLError:
        return False

    return True


def check_certificate_dates(cert_contents: str) -> CertificateDatesCheckResult:
    """
    Проверяет дату сертификата
    """
    with _temporary_pem_files(cert_contents) as (cert_path, _):
        cert = ssl._ssl._test_decode_cert(str(cert_path))

    start_date = datetime.fromtimestamp(
        ssl.cert_time_to_seconds(cert["notBefore"]),
        timezone.utc,
    )
    end_date = datetime.fromtimestamp(
        ssl.cert_time_to_seconds(cert["notAfter"]),
        timezone.utc,
    )
    now = datetime.now(timezone.utc)
    status = CertificateStatus.VALID

    if now < start_date:
        status = CertificateStatus.NOT_YET_VALID

    elif now > end_date:
        status = CertificateStatus.EXPIRED

    return CertificateDatesCheckResult(status, start_date, end_date)
