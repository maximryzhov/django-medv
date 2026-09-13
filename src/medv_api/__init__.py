import niquests

class MedvClient:
    BASE_URL = "https://slb.medv.ru/api/v2/"

    def __init__(self, cert: str, key: str) -> None:
        self.cert = cert
        self.key = key

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
            