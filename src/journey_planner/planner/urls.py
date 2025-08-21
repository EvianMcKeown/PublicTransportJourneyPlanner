from django.urls import path
from . import views
from django.views.generic import RedirectView

urlpatterns = [
    path("", views.home_view, name="home"),
    path("journey/", views.journey_view, name="journey"),
    path("faq/", views.faq_view, name="faq"),
    path("login/", views.user_login_view, name="login"),
    path("signUp/", views.user_signup_view, name="signup"),
    # NOTE: MCKEVI001 Tailwind Test Site
    path("tailwind/", views.tailwind_view, name="plan"),
    # path(
    #    # Redirect root URL to plan view
    #    "",
    #    RedirectView.as_view(url="plan/", permanent=True),
    # ),
]
