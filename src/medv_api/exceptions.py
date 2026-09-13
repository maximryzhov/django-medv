class MedvClientError(Exception):
    pass


class MedvClientCertificateError(MedvClientError):
    pass


class MedvClientConnectionError(MedvClientError):
    pass
