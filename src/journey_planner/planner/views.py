from django.shortcuts import render

from django.http import JsonResponse, HttpResponse

# from .state import PlanState
# from .service import plan_journey

# This gets executed when the URL fits the URL pattern:
# journey_planner.urls ——> planner.urls ——> path('plan/') ——> views.plan_view


def tailwind_view(request):
    return render(request, "tailwindcss-test.html")


def home_view(request):
    return render(request, "homePage.html")


def journey_view(request):
    return render(request, "journey.html")


def faq_view(request):
    return render(request, "faq.html")


def user_login_view(request):
    return render(request, "logIn.html")


def user_signup_view(request):
    return render(request, "signUp.html")
