from unittest.mock import patch

from django.test import TestCase

from medv_api import MedvClientCertificateError, MedvClientConnectionError


class FakeResponse:
    def __init__(
        self,
        status_code=200,
        text="",
        content_type="text/plain",
        request_id="request-id",
    ):
        self.status_code = status_code
        self.text = text
        self.headers = {"content-type": content_type}
        self.request_id = request_id


class MedvTestViewTests(TestCase):
    url = "/"

    @patch("django_medv.views.MedvClient")
    def test_method_is_loaded_from_query_string(self, _client_class):
        response = self.client.get(f"{self.url}?method=patients.list")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["form"].initial["method_name"],
            "patients.list",
        )

    @patch("django_medv.views.MedvClient")
    def test_invalid_json_is_displayed_and_not_sent(self, client_class):
        response = self.client.post(
            self.url,
            {"method_name": "auth.check", "method_body": "not json"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Введите корректный JSON")
        client_class.return_value.call_method.assert_not_called()

    @patch("django_medv.views.MedvClient")
    def test_request_and_error_response_are_displayed(self, client_class):
        client_class.return_value.call_method.return_value = FakeResponse(
            status_code=500,
            text='{"error": "Ошибка сервиса"}',
            content_type="application/json",
        )

        response = self.client.post(
            f"{self.url}?method=patients.list",
            {"method_name": "patients.list", "method_body": '{"page": 1}'},
        )

        client_class.return_value.call_method.assert_called_once_with(
            "patients.list",
            {"page": 1},
        )
        self.assertEqual(response.wsgi_request.GET["method"], "patients.list")
        self.assertEqual(response.context["request_id"], "request-id")
        self.assertContains(response, "ID запроса: request-id")
        self.assertContains(response, "Код ответа: 500")
        self.assertContains(response, "Ошибка сервиса")
        self.assertTrue(response.context["response_error"])

    @patch("django_medv.views.MedvClient")
    def test_health_check_errors_are_displayed(self, client_class):
        client_class.return_value.validate_credentials.side_effect = (
            MedvClientCertificateError("Ключ не валиден")
        )
        client_class.return_value.ping_base_url.side_effect = (
            MedvClientConnectionError("Нет соединения с сервером")
        )

        response = self.client.get(self.url)

        self.assertContains(response, "Ключ не валиден")
        self.assertContains(response, "Нет соединения с сервером")
        self.assertContains(response, 'class="status error"', count=2)
