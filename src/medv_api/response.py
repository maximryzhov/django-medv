import json

class MedvResponse:
    def __init__(self, response, request_id: str | None = None) -> None:
        self.status_code = response.getcode()
        self.headers = response.headers
        self.text = response.read().decode("utf-8", errors="replace")
        self.request_id = request_id
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
        except TypeError, ValueError:
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
            if (
                not isinstance(error, dict)
                or "code" not in error
                or "message" not in error
            ):
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
