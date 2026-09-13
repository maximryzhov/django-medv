from django.urls import path

from .views import MedvTestView


app_name = "django_medv"

urlpatterns = [
    path("medv-test/", MedvTestView.as_view(), name="medv-test"),
]
