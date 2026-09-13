# Полезные функции для  работы с API и авторизацией

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


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


def check_certificate_rsa(cert_contents: str) -> bool:
    """
    Проверяем, что сертификат содержит RSA ключ
    """
    cert = x509.load_pem_x509_certificate(cert_contents.encode())
    public_key = cert.public_key()

    return isinstance(public_key, rsa.RSAPublicKey)


def check_key_is_valid(key_contents: str) -> bool:
    # Если ключ загружается, он валиден
    try:
        key = serialization.load_pem_private_key(
            key_contents.encode("utf-8"),
            password=None,
        )
        return True

    except (ValueError, TypeError) as e:
        return False


def check_certificate_matches_key(cert_contents: str, key_contents: str) -> bool:
    """
    Проверяет, что сертификат и ключ из одной пары
    """

    cert = x509.load_pem_x509_certificate(cert_contents.encode())

    private_key = serialization.load_pem_private_key(
        key_contents.encode(), 
        password=None  # NOTE: подразумеваем, что пароля нет
    )

    return (
        cert.public_key().public_numbers() == private_key.public_key().public_numbers()
    )


def check_certificate_dates(cert_contents: str) -> CertificateDatesCheckResult:
    """
    Проверяет дату сертификата
    """
    cert = x509.load_pem_x509_certificate(cert_contents.encode())
    now = datetime.now(timezone.utc)
    status = CertificateStatus.VALID

    if now < cert.not_valid_before_utc:
        status = CertificateStatus.NOT_YET_VALID

    elif now > cert.not_valid_after_utc:
        status = CertificateStatus.EXPIRED

    return CertificateDatesCheckResult(
        status, cert.not_valid_before_utc, cert.not_valid_after_utc
    )


def check_certificate_auth(cert_contents: str):
    cert = x509.load_pem_x509_certificate(cert_contents.encode())
        
    eku = cert.extensions.get_extension_for_class(
        x509.ExtendedKeyUsage
    ).value

    return x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH in eku