from django.shortcuts import render

from django.http import JsonResponse, HttpResponse
#from .state import PlanState
#from .service import plan_journey

# This gets executed when the URL fits the URL pattern:
# journey_planner.urls ——> planner.urls ——> path('plan/') ——> views.plan_view


def plan_view(request):
    return render(request, '1.html')