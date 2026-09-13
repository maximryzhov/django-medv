import json

from django.conf import settings
from django.views.generic.edit import FormView

from medv_api import MedvClient, MedvClientError

from .forms import MethodCallForm


class MedvTestView(FormView):
    template_name = "django_medv/medv_test.html"
    form_class = MethodCallForm
    available_methods = ("auth.check",)

    def dispatch(self, request, *args, **kwargs):
        self.medv_client = MedvClient(settings.MEDV_CERT, settings.MEDV_KEY)
        self.health_checks = self._run_health_checks()
        self.request_error = None
        return super().dispatch(request, *args, **kwargs)

    def _run_health_checks(self):
        checks = []

        try:
            self.medv_client.validate_credentials()
        except Exception as error:
            checks.append(
                {
                    "name": "Сертификат и ключ",
                    "ok": False,
                    "message": str(error),
                }
            )
        else:
            checks.append(
                {
                    "name": "Сертификат и ключ",
                    "ok": True,
                    "message": "Сертификат и ключ валидны",
                }
            )

        try:
            self.medv_client.ping_base_url()
        except MedvClientError as error:
            checks.append(
                {
                    "name": "Соединение с Medv",
                    "ok": False,
                    "message": str(error),
                }
            )
        else:
            checks.append(
                {
                    "name": "Соединение с Medv",
                    "ok": True,
                    "message": "Сервер доступен",
                }
            )

        return checks

    def get_initial(self):
        initial = super().get_initial()
        initial["method_name"] = self.request.GET.get(
            "method", self.available_methods[0]
        )
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["available_methods"] = self.available_methods
        context["health_checks"] = self.health_checks
        context["request_error"] = self.request_error
        context["BASE_URL"] = MedvClient.BASE_URL
        
        response = kwargs.get("medv_response")
        if response is not None:
            context.update(self._format_response(response))
        else:
            context["has_response"] = False

        return context

    @staticmethod
    def _format_response(response):
        body = response.text
        headers = getattr(response, "headers", {}) or {}
        content_type = headers.get("content-type", "")
        content_type = content_type.split(";", 1)[0].strip().lower()

        if content_type in {"text/html", "application/xhtml+xml"}:
            kind = "html"
            formatted_body = body
        elif content_type == "application/json" or content_type.endswith("+json"):
            kind = "json"
            try:
                formatted_body = json.dumps(
                    json.loads(body), indent=2, ensure_ascii=False
                )
            except (TypeError, ValueError):
                kind = "text"
                formatted_body = body
        else:
            kind = "text"
            formatted_body = body
            if not content_type:
                try:
                    formatted_body = json.dumps(
                        json.loads(body), indent=2, ensure_ascii=False
                    )
                    kind = "json"
                except (TypeError, ValueError):
                    pass

        status_code = response.status_code
        return {
            "has_response": True,
            "response_status_code": status_code,
            "response_content_type": content_type or "не указан",
            "response_kind": kind,
            "response_body": formatted_body,
            "response_error": status_code >= 400,
        }

    def form_valid(self, form):
        try:
            response = self.medv_client.call_method(
                form.cleaned_data["method_name"],
                form.cleaned_data["method_body"],
            )
        except MedvClientError as error:
            self.request_error = str(error)
            form.add_error(None, str(error))
            return self.form_invalid(form)

        return self.render_to_response(
            self.get_context_data(form=form, medv_response=response)
        )
