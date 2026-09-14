import json
from contextlib import nullcontext
from urllib.error import URLError
from unittest import TestCase
from unittest.mock import ANY, patch
from uuid import UUID

from . import MedvClient, MedvClientConnectionError, MedvResponse


class FakeHTTPResponse:
    headers = {"content-type": "application/json"}

    def __init__(self, status_code=200, body=b'{}'):
        self.status_code = status_code
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def getcode(self):
        return self.status_code

    def read(self):
        return self.body


class MedvClientTests(TestCase):
    def test_call_method_sends_json_rpc_request(self):
        client = MedvClient("cert", "key")
        ssl_context = object()

        with (
            patch.object(
                client,
                "_authenticated_context",
                return_value=nullcontext(ssl_context),
            ),
            patch(
                "medv_api.client.urlopen",
                return_value=FakeHTTPResponse(body=b'{"result": true}'),
            ) as urlopen,
        ):
            response = client.call_method("patients.list", {"page": 1})

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, client.BASE_URL)
        self.assertEqual(
            json.loads(request.data),
            {
                "jsonrpc": "2.0",
                "id": ANY,
                "method": "patients.list",
                "params": {"page": 1},
            },
        )
        self.assertIs(urlopen.call_args.kwargs["context"], ssl_context)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, '{"result": true}')

    def test_call_method_uses_uuid_as_request_id(self):
        client = MedvClient("cert", "key")
        request_id = UUID("12345678-1234-5678-1234-567812345678")

        with (
            patch("medv_api.client.uuid4", return_value=request_id),
            patch.object(
                client,
                "_authenticated_context",
                return_value=nullcontext(object()),
            ),
            patch(
                "medv_api.client.urlopen",
                return_value=FakeHTTPResponse(
                    body=json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": str(request_id),
                            "result": {"authenticated": True},
                        }
                    ).encode(),
                ),
            ) as urlopen,
        ):
            response = client.call_method("auth.check")

        payload = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(payload["id"], str(request_id))
        self.assertEqual(response.request_id, str(request_id))
        self.assertTrue(response.is_jsonrpc_response)
        self.assertEqual(response.id, str(request_id))
        self.assertEqual(response.result, {"authenticated": True})

    def test_json_rpc_error_is_extracted(self):
        request_id = "12345678-1234-5678-1234-567812345678"
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32600,
                    "message": "Invalid Request",
                    "data": {"field": "method"},
                },
            }
        ).encode()

        response = MedvResponse(FakeHTTPResponse(body=body), request_id)

        self.assertTrue(response.is_jsonrpc_response)
        self.assertEqual(response.error_code, -32600)
        self.assertEqual(response.error_message, "Invalid Request")
        self.assertEqual(response.error_data, {"field": "method"})

    def test_json_rpc_response_with_different_id_is_rejected(self):
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": "other-id",
                "result": True,
            }
        ).encode()

        response = MedvResponse(FakeHTTPResponse(body=body), "request-id")

        self.assertFalse(response.is_jsonrpc_response)
        self.assertIsNone(response.result)

    def test_call_method_without_body_omits_params(self):
        client = MedvClient("cert", "key")

        with (
            patch.object(
                client,
                "_authenticated_context",
                return_value=nullcontext(object()),
            ),
            patch("medv_api.client.urlopen", return_value=FakeHTTPResponse()) as urlopen,
        ):
            client.call_method("auth.check")

        request = urlopen.call_args.args[0]
        self.assertEqual(
            json.loads(request.data),
            {"jsonrpc": "2.0", "id": ANY, "method": "auth.check"},
        )

    def test_call_method_wraps_transport_error(self):
        client = MedvClient("cert", "key")

        with (
            patch.object(
                client,
                "_authenticated_context",
                return_value=nullcontext(object()),
            ),
            patch("medv_api.client.urlopen", side_effect=URLError("network error")),
            self.assertRaisesRegex(
                MedvClientConnectionError,
                "Нет соединения с сервером",
            ),
        ):
            client.call_method("auth.check")
