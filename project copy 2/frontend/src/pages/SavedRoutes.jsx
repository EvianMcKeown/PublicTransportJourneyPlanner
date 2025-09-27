import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

export default function SavedRoutes() {
    const [routes, setRoutes] = useState([]);
    const [map, setMap] = useState(null);
    const [directionsService, setDirectionsService] = useState(null);
    const [directionsRenderer, setDirectionsRenderer] = useState(null);

    // Fetch saved routes from Django backend
    const fetchRoutes = () => {
        const token = localStorage.getItem("access"); // fixed key
        if (!token) {
            alert("You must be logged in to see saved routes.");
            return;
        }

        fetch("http://127.0.0.1:8000/api/routes/", {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then(res => res.json())
            .then(data => {
                setRoutes(data || []);
            })
            .catch(err => console.error("Error fetching saved routes:", err));
    };

    useEffect(() => {
        fetchRoutes();
    }, []);

    // Initialize Google Map
    useEffect(() => {
        if (!(window.google && window.google.maps)) {
            console.error("Google Maps JS API not loaded.");
            return;
        }

        const center = { lat: -33.9249, lng: 18.4241 };
        const newMap = new window.google.maps.Map(document.getElementById("map"), {
            zoom: 13,
            center,
        });

        setMap(newMap);
        setDirectionsService(new window.google.maps.DirectionsService());
        setDirectionsRenderer(new window.google.maps.DirectionsRenderer({ map: newMap }));
    }, []);

    const showRoute = (start, end) => {
        if (!directionsService || !directionsRenderer) return;

        const request = {
            origin: start,
            destination: end,
            travelMode: window.google.maps.TravelMode.TRANSIT,
        };

        directionsService.route(request, (result, status) => {
            if (status === "OK") {
                directionsRenderer.setDirections(result);
            } else {
                alert("Directions request failed: " + status);
            }
        });
    };

    const deleteRoute = async (id) => {
        if (!window.confirm("Are you sure you want to delete this route?")) {
            return; // user canceled
        }

        const token = localStorage.getItem("access"); // fixed key
        if (!token) {
            alert("You must be logged in to delete routes.");
            return;
        }

        try {
            const response = await fetch(`http://127.0.0.1:8000/api/routes/${id}/`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${token}` },
            });

            if (response.status === 204) {
                alert("Route deleted successfully!");
                // Refresh list
                fetchRoutes();
            } else {
                const data = await response.json();
                alert(data.error || "Error deleting route");
            }
        } catch (error) {
            console.error("Error deleting route:", error);
            alert("Error deleting route.");
        }
    };

    return (
        <div className="flex flex-col min-h-screen w-screen bg-[#d3d3d3]">
            {/* Header */}
            <header className="w-full bg-[#001f4d] text-white flex items-center justify-center py-3">
                <img src="/logo.png" alt="PathPilot Logo" className="h-[60px]" />
                <span className="text-xl font-bold ml-2">YOUR JOURNEY, OUR GUIDE</span>
            </header>

            {/* Back Button */}
            <div className="p-4">
                <Link to="/home">
                    <button className="bg-[#001f4d] text-white px-4 py-2 rounded hover:bg-[#003366]">
                        ← Back to Home
                    </button>
                </Link>
            </div>

            {/* Routes & Map */}
            <div className="flex-1 flex flex-col lg:flex-row p-4 gap-4">
                {/* Sidebar */}
                <div className="lg:w-1/3 bg-white p-4 rounded shadow overflow-auto text-black">
                    <h2 className="text-2xl font-bold mb-4">Saved Routes</h2>

                    {routes.length === 0 ? (
                        <p>No saved routes yet.</p>
                    ) : (
                        routes.map((route, index) => (
                            <div key={route.id} className="mb-4 border-b pb-2">
                                <button
                                    className="route-button bg-[#001f4d] text-white px-3 py-1 rounded w-full text-left mb-2 hover:bg-[#003366]"
                                    onClick={() =>
                                        showRoute(route.start_location, route.end_location)
                                    }
                                >
                                    Route {index + 1}: {route.start_location} → {route.end_location}
                                </button>
                                <p>Saved on: {new Date(route.created_at).toLocaleString()}</p>
                                <button
                                    className="mt-2 bg-red-600 text-white px-3 py-1 rounded hover:bg-red-800"
                                    onClick={() => deleteRoute(route.id)}
                                >
                                    Delete
                                </button>
                            </div>
                        ))
                    )}
                </div>

                {/* Map */}
                <div className="lg:w-2/3 h-96 lg:h-auto rounded shadow" id="map"></div>
            </div>

            {/* Footer */}
            <footer className="w-full bg-black text-white text-center py-3 mt-auto">
                <p>&copy; 2025 PathPilot</p>
                <p>Email: PathPilot@gmail.com</p>
                <p>Contact No: +27747618921</p>
            </footer>
        </div>
    );
}
