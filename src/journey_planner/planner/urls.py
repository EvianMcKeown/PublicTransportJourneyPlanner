from django.urls import path
from . import views
from django.views.generic import RedirectView

urlpatterns = [
    path("plan/", views.plan_view, name="plan"),
    path(
        "", RedirectView.as_view(url="plan/", permanent=True)
    ),  # Redirect root URL to plan view
]
