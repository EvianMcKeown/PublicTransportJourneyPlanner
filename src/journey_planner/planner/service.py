from datetime import timedelta
from .models import Route, RouteSegment, RoutePreferences, UserPreferences


# File contains the algorithms - path finding (plan_journey), etc.
#
# This is an independent module that the state and views can call to perform specific tasks.
def plan_journey(start_location, end_location, start_date_time, user):
    """
    Plans a journey from start_location to end_location starting at start_date_time for the given user.

    This function will create a new Route object and return it. It fetches data, calls the algorithm, and creates model instances.
    """

    # NOTE: MAKE LOCATION OBJECT WITH LATITUDE AND LONGITUDE
    # 1. Fetch all public transport data relevant to the user's preferences. # TODO: WILL BE IMPLEMENTED LATER
    # 2. Call the pathfinding algorithm to find the best route. # TODO: WILL BE IMPLEMENTED LATER
    # 3. Create Route and RouteSegment instances based on the algorithm's output.

    # Dummy implementation for prototype
    # i) Create Route instance
    route = Route.objects.create(
        user=user,
        start_location=start_location,
        end_location=end_location,
        start_date_time=start_date_time,
    )
    # ii_ Create RoutePreferences for the Route
    route_preferences = RoutePreferences.objects.create(
        routeId=route,
        allow_trains=True,
        allow_busses=True,
        allow_taxis=True,
        max_walk_distance=5000,  # Default value, can be adjusted later
    )
    # iii) Create dummy RouteSegment instances
    RouteSegment.objects.create(
        route=route,
        segment_type="walk",
        start_location=start_location,
        end_location="Bus Stop A",
        start_time=start_date_time,
        end_time=start_date_time + timedelta(minutes=10),
    )
    RouteSegment.objects.create(
        route=route,
        segment_type="bus",
        start_location="Bus Stop A",
        end_location="Bus Stop B",
        start_time=start_date_time + timedelta(minutes=10),
        end_time=start_date_time + timedelta(minutes=30),
    )
    RouteSegment.objects.create(
        route=route,
        segment_type="walk",
        start_location="Bus Stop B",
        end_location=end_location,
        start_time=start_date_time + timedelta(minutes=30),
        end_time=start_date_time + timedelta(minutes=40),
    )

    return route
