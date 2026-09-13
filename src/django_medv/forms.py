from django import forms


class MethodCallForm(forms.Form):
    method_name = forms.CharField(
        label="Имя метода",
        max_length=200,
        strip=True,
    )
    method_body = forms.JSONField(
        label="Тело метода (JSON)",
        required=False,
        error_messages={"invalid": "Введите корректный JSON."},
        widget=forms.Textarea(attrs={"rows": 12, "spellcheck": "false"}),
    )
