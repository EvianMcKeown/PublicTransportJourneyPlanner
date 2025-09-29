import { useEffect, useState, useRef } from "react";
import { Link } from "react-router-dom";

export default function SavedRoutes() {
    const [routes, setRoutes] = useState([]);
    const [mapError, setMapError] = useState(null);
    const mapRef = useRef(null);
    const directionsServiceRef = useRef(null);
    const directionsRendererRef = useRef(null);

    // Fetch saved routes
    useEffect(() => {
        const token = localStorage.getItem("access");
        if (!token) return;

        fetch("http://127.0.0.1:8000/api/routes/", {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then((res) => res.json())
            .then((data) => {
                if (Array.isArray(data)) {
                    setRoutes(data);
                } else {
                    console.warn("Unexpected routes response:", data);
                    setRoutes([]);
                }
            })
            .catch((err) => console.error("Error fetching routes:", err));
    }, []);

    // Load Google Maps
    useEffect(() => {
        if (window.google && window.google.maps) {
            initMap();
            return;
        }

        const apiKey = process.env.REACT_APP_GOOGLE_MAPS_API_KEY || "YOUR_API_KEY";
        const scriptId = "google-maps-script";

        if (document.getElementById(scriptId)) return;

        const script = document.createElement("script");
        script.id = scriptId;
        script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&v=weekly`;
        script.async = true;
        script.defer = true;
        script.onload = initMap;
        script.onerror = () => setMapError("Failed to load Google Maps.");
        document.head.appendChild(script);
    }, []);

    const initMap = () => {
        try {
            const center = { lat: -33.9249, lng: 18.4241 }; // Cape Town
            const map = new window.google.maps.Map(mapRef.current, {
                zoom: 13,
                center,
            });

            directionsServiceRef.current = new window.google.maps.DirectionsService();
            directionsRendererRef.current = new window.google.maps.DirectionsRenderer();
            directionsRendererRef.current.setMap(map);
        } catch (err) {
            console.error("Map init failed:", err);
            setMapError("Could not initialize map.");
        }
    };

    const showRoute = (route) => {
        if (
            !window.google ||
            !directionsServiceRef.current ||
            !directionsRendererRef.current
        ) {
            alert("Map is not ready yet.");
            return;
        }

        // Prefer coordinates if available, otherwise fall back to names
        const origin = route.start_lat && route.start_lon
            ? { lat: route.start_lat, lng: route.start_lon }
            : route.start_location;

        const destination = route.end_lat && route.end_lon
            ? { lat: route.end_lat, lng: route.end_lon }
            : route.end_location;

        directionsServiceRef.current.route(
            {
                origin,
                destination,
                travelMode: window.google.maps.TravelMode.TRANSIT,
            },
            (result, status) => {
                if (status === "OK") {
                    directionsRendererRef.current.setDirections(result);
                } else {
                    alert("Directions request failed: " + status);
                }
            }
        );
    };

    const deleteRoute = async (id) => {
        if (!window.confirm("Are you sure you want to delete this route?")) return;

        const token = localStorage.getItem("access");
        if (!token) return;

        try {
            const res = await fetch(`http://127.0.0.1:8000/api/routes/${id}/`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${token}` },
            });

            if (res.status === 204) {
                setRoutes((prev) => prev.filter((r) => r.id !== id));
            } else {
                const data = await res.json();
                alert(data.error || "Error deleting route");
            }
        } catch (err) {
            console.error("Error deleting route:", err);
        }
    };

    return (
        <div className="flex flex-col min-h-screen w-screen bg-[#d3d3d3]">
            {/* Header */}
            <header className="w-full bg-[#001f4d] text-white flex items-center justify-center py-3 relative z-20">
                <img src="/logo.png" alt="PathPilot Logo" className="h-[60px]" />
                <span className="text-xl font-bold ml-2">YOUR JOURNEY, OUR GUIDE</span>
            </header>

            {/* Back Button */}
            <div className="p-4 flex justify-center relative z-30">
                <Link to="/home">
                    <button className="bg-[#001f4d] text-white px-4 py-2 rounded hover:bg-[#003366]">
                        ← Back to Home
                    </button>
                </Link>
            </div>

            {/* Main layout */}
            <div className="flex-1 flex flex-col lg:flex-row p-4 gap-4">
                {/* Sidebar */}
                <div className="lg:w-1/3 bg-white p-4 rounded shadow overflow-auto text-black relative z-10">
                    <h2 className="text-2xl font-bold mb-4">Saved Routes</h2>
                    {routes.length === 0 ? (
                        <p>No saved routes yet.</p>
                    ) : (
                        routes.map((route, index) => (
                            <div key={route.id || index} className="mb-4 border-b pb-2">
                                <button
                                    className="bg-[#001f4d] text-white px-3 py-1 rounded w-full text-left mb-2 hover:bg-[#003366]"
                                    onClick={() => showRoute(route)}
                                >
                                    Route {index + 1}: {route.start_location} →{" "}
                                    {route.end_location}
                                </button>
                                {route.start_lat && route.start_lon && (
                                    <p className="text-sm text-gray-600">
                                        ({route.start_lat.toFixed(3)}, {route.start_lon.toFixed(3)}) → ({route.end_lat.toFixed(3)}, {route.end_lon.toFixed(3)})
                                    </p>
                                )}
                                <p className="text-xs text-gray-500">
                                    Saved on:{" "}
                                    {route.created_at
                                        ? new Date(route.created_at).toLocaleString()
                                        : "Unknown"}
                                </p>
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
                <div className="lg:w-2/3 h-96 lg:h-[520px] rounded shadow bg-gray-200 relative">
                    {mapError && (
                        <div className="flex items-center justify-center h-full text-red-600 font-semibold">
                            {mapError}
                        </div>
                    )}
                    <div ref={mapRef} className="w-full h-full rounded" />
                </div>
            </div>

            {/* Footer */}
            <footer className="w-full bg-black text-white text-center py-3 mt-auto relative z-20">
                <p>&copy; 2025 PathPilot</p>
                <p>Email: PathPilot@gmail.com</p>
                <p>Contact No: +27747618921</p>
            </footer>
        </div>
    );
}
