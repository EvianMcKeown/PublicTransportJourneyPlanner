import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { jwtDecode } from "jwt-decode";

export default function Home() {
    const [isSuperUser, setIsSuperUser] = useState(false);
    const [lastStart, setLastStart] = useState(null);
    const [lastEnd, setLastEnd] = useState(null);
    const [toastMessage, setToastMessage] = useState(null);
    const [routeInfo, setRouteInfo] = useState(null); // Stores time & distance
    const [ptJourney, setPtJourney] = useState(null);
    const [planning, setPlanning] = useState(false)
    const navigate = useNavigate();

    let autocompleteStart;
    let autocompleteEnd;
    let directionsService;
    let directionsRenderer;

    // Helper: map JS day (0=Sun..6=Sat) to backend (0=Mon..6=Sun)
    const getBackendDay = () => {
        const js = new Date().getDay(); // 0..6
        return (js + 6) % 7;
    };
    // Helper: format minutes to 'Mon HH:MM'
    const minsToStr = (total) => {
        if (total == null) return "";
        const names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
        const day = Math.floor(total / 1440) % 7;
        const minsInDay = ((total % 1440) + 1440) % 1440;
        const hh = String(Math.floor(minsInDay / 60)).padStart(2, "0");
        const mm = String(minsInDay % 60).padStart(2, "0");
        return `${names[day]} ${hh}:${mm}`;
    };
    // Call Django /api/plan/ using the Start/End input values as GTFS stop IDs
    const planPublicTransport = async () => {
        const sourceId = document.getElementById("start")?.value?.trim();
        const targetId = document.getElementById("end")?.value?.trim();
        if (!sourceId || !targetId) {
            showToast("Enter valid stop IDs (e.g., GABS001, GABS006).", true);
            return;
        }
        setPlanning(true);
        setPtJourney(null);
        try {
            const now = new Date();
            const day = getBackendDay();
            const hh = String(now.getHours()).padStart(2, "0");
            const mm = String(now.getMinutes()).padStart(2, "0");
            const time = `${hh}:${mm}`;

            const API_BASE = import.meta.env.DEV ? "http://127.0.0.1:8000" : "";
            const resp = await fetch(`${API_BASE}/api/plan/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    source_id: sourceId,
                    target_id: targetId,
                    day,
                    time,
                    max_rounds: 5,
                }),
            });

            // Read text first, then try JSON if content-type is JSON
            const contentType = resp.headers.get("content-type") || "";
            const text = await resp.text();
            let data = null;
            if (contentType.includes("application/json") && text) {
                try {
                    data = JSON.parse(text);
                } catch (_) {
                    // ignore parse error; fall back to text
                }
            }

            if (!resp.ok) {
                const msg = (data && (data.detail || data.error)) || text || `HTTP ${resp.status}`;
                showToast(msg, true);
                return;
            }
            setPtJourney({
                earliest_arrival: data?.earliest_arrival,
                path_objs: data?.path_objs || [],
            });
            showToast("Public transport plan ready.");
        } catch (e) {
            console.error(e);
            showToast("Error contacting journey planner.", true);
        } finally {
            setPlanning(false);
        }
    };

    const showToast = (message, isError = false) => {
        setToastMessage({ text: message, error: isError });
        setTimeout(() => setToastMessage(null), 3000);
    };

    // Logout
    const handleLogout = () => {
        localStorage.removeItem("access");
        navigate("/");
    };

    // Save Route
    const saveRoute = async (start, end) => {
        const token = localStorage.getItem("access");
        if (!token) {
            showToast("You must be logged in to save routes.", true);
            return;
        }

        if (!start || !end) {
            showToast("No route selected to save.", true);
            return;
        }

        try {
            const response = await fetch("http://127.0.0.1:8000/api/routes/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    start_location: start,
                    end_location: end,
                }),
            });

            const data = await response.json();
            if (response.ok) {
                showToast("✅ Route saved successfully!");
            } else {
                showToast(data.error || "Error saving route", true);
            }
        } catch (error) {
            console.error(error);
            showToast("Error saving route", true);
        }
    };

    // Calculate route
    const calculateAndDisplayRoute = () => {
        const startPlace = autocompleteStart?.getPlace();
        const endPlace = autocompleteEnd?.getPlace();

        if (!startPlace || !startPlace.geometry || !endPlace || !endPlace.geometry) {
            showToast("Please select valid locations from dropdown", true);
            return;
        }

        directionsService.route(
            {
                origin: { placeId: startPlace.place_id },
                destination: { placeId: endPlace.place_id },
                travelMode: window.google.maps.TravelMode.DRIVING,
            },
            (response, status) => {
                if (status === "OK") {
                    directionsRenderer.setDirections(response);
                    setLastStart(startPlace.name);
                    setLastEnd(endPlace.name);

                    // Extract distance & duration
                    const leg = response.routes[0].legs[0];
                    setRouteInfo({
                        distance: leg.distance.text,
                        duration: leg.duration.text,
                    });
                } else {
                    showToast("Directions request failed: " + status, true);
                }
            }
        );
    };

    useEffect(() => {
        // Decode token once
        const token = localStorage.getItem("access");
        if (token) {
            try {
                const decoded = jwtDecode(token);
                if (decoded.is_superuser) {
                    setIsSuperUser(true);
                }
            } catch (err) {
                console.error("Error decoding token:", err);
            }
        }

        let map;

        const initAutocomplete = () => {
            autocompleteStart = new window.google.maps.places.Autocomplete(
                document.getElementById("start"),
                {
                    types: ["geocode"],
                    componentRestrictions: { country: ["ZA"] },
                    fields: ["place_id", "geometry", "name"],
                }
            );
            autocompleteEnd = new window.google.maps.places.Autocomplete(
                document.getElementById("end"),
                {
                    types: ["geocode"],
                    componentRestrictions: { country: ["ZA"] },
                    fields: ["place_id", "geometry", "name"],
                }
            );
        };

        const initMap = () => {
            const center = { lat: -33.9249, lng: 18.4241 };
            map = new window.google.maps.Map(document.getElementById("map"), {
                zoom: 12,
                center: center,
            });

            directionsService = new window.google.maps.DirectionsService();
            directionsRenderer = new window.google.maps.DirectionsRenderer({ map: map });

            initAutocomplete();
        };

        if (window.google && window.google.maps) {
            initMap();
        } else {
            console.error("Google Maps failed to load. Check your API key and index.html setup.");
        }
    }, []);

    return (
        <div className="flex flex-col h-screen w-screen bg-[#d3d3d3]">
            {/* Header with logo, search, and nav */}
            <header className="w-full bg-[#001f4d] text-white flex items-center justify-between py-3 px-6 gap-4">
                <div className="flex items-center gap-2">
                    <img src="/logo.png" alt="PathPilot Logo" className="h-[60px]" />
                    <span className="text-xl font-bold">YOUR JOURNEY, OUR GUIDE</span>
                </div>

                {/* Search inline */}
                <form
                    className="flex gap-2 items-center"
                    onSubmit={(e) => {
                        e.preventDefault();
                        calculateAndDisplayRoute();
                        planPublicTransport();
                    }}
                >
                    <input
                        id="start"
                        type="text"
                        placeholder="Start"
                        className="bg-white text-black placeholder-gray-500 border border-[#001f4d] rounded px-2 py-1 w-32 sm:w-40 focus:outline-none focus:ring-2 focus:ring-[#003366]"
                    />
                    <input
                        id="end"
                        type="text"
                        placeholder="Destination"
                        className="bg-white text-black placeholder-gray-500 border border-[#001f4d] rounded px-2 py-1 w-32 sm:w-40 focus:outline-none focus:ring-2 focus:ring-[#003366]"
                    />
                    <button
                        id="searchBtn"
                        type="submit"
                        className="bg-gray-800 text-white px-3 py-1 rounded hover:bg-gray-900"
                    >
                        Find Routes
                    </button>
                </form>

                {/* Nav buttons */}
                <nav className="flex gap-2 items-center">
                    <Link to="/savedroutes" className="bg-gray-800 text-white px-3 py-1 rounded hover:bg-gray-900">
                        Saved Routes
                    </Link>
                    <Link to="/faq" className="bg-gray-800 text-white px-3 py-1 rounded hover:bg-gray-900">
                        FAQ
                    </Link>
                    <Link to="/settings" className="bg-gray-800 text-white px-3 py-1 rounded hover:bg-gray-900">
                        Settings
                    </Link>
                    {isSuperUser && (
                        <a
                            href="http://127.0.0.1:8000/admin/"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="bg-gray-800 text-white px-3 py-1 rounded hover:bg-gray-900"
                        >
                            Admin Panel
                        </a>
                    )}
                    <button
                        onClick={handleLogout}
                        className="bg-gray-800 text-white px-3 py-1 rounded hover:bg-gray-900"
                    >
                        Logout
                    </button>
                </nav>
            </header>

            {/* Sidebar + Map */}
            <div className="flex flex-1 w-full gap-6 p-4">
                {/* Sidebar */}
                <aside className="w-64 bg-gray-700 text-white p-4 rounded-md flex flex-col gap-4 h-[calc(100vh-160px)] overflow-y-auto">
                    <h2 className="text-lg font-bold">Preferences</h2>
                    <form className="flex flex-col gap-2">
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input type="checkbox" name="minWalking" />
                            Minimise walking
                        </label>
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input type="checkbox" name="minStops" />
                            Minimise stops
                        </label>
                    </form>
                    <button
                        type="button"
                        className="bg-[#001f4d] py-2 rounded hover:bg-[#003366]"
                        onClick={() => {
                            if (!lastStart || !lastEnd) {
                                showToast("Please search for a route before saving.", true);
                                return;
                            }
                            saveRoute(lastStart, lastEnd);
                        }}
                    >
                        Save Current Route
                    </button>

                    {/* Route Visualisation */}
                    {lastStart && lastEnd && (
                        <div className="mt-6 p-4 bg-gray-800 rounded text-center relative overflow-hidden">
                            <h3 className="font-bold text-white">{lastStart}</h3>
                            <div className="flex flex-col items-center relative my-4">
                                <div className="w-px h-16 bg-white"></div>
                                <div className="absolute animate-car">🚗</div>
                            </div>
                            <h3 className="font-bold text-white">{lastEnd}</h3>

                            {/* Show Distance & Duration */}
                            {routeInfo && (
                                <div className="mt-4 text-sm text-gray-300">
                                    <p>Distance: {routeInfo.distance}</p>
                                    <p>Duration: {routeInfo.duration}</p>
                                </div>
                            )}
                        </div>
                    )}
                    <div className="mt-6 p-4 bg-gray-800 rounded">
                        <h2 className="text-lg font-bold mb-2">Public Transport</h2>
                        {!ptJourney && <p className="text-sm text-gray-300">Search to see an itinerary.</p>}
                        {ptJourney && (
                            <div className="space-y-2">
                                <p className="text-sm">
                                    Earliest arrival: <span className="font-semibold">{minsToStr(ptJourney.earliest_arrival)}</span>
                                </p>
                                <ol className="list-decimal list-inside space-y-2">
                                    {ptJourney.path_objs.map((step, idx) => {
                                        const atStr = minsToStr(step.arrival_time);
                                        if (step.mode === "start") {
                                            return (
                                                <li key={idx} className="text-sm">
                                                    Start at {step.stop?.name || step.stop_id} at {atStr}
                                                </li>
                                            );
                                        }
                                        if (step.mode === "transfer") {
                                            return (
                                                <li key={idx} className="text-sm">
                                                    Walk from {step.from_stop?.name || step.from_stop_id} to{" "}
                                                    {step.stop?.name || step.stop_id} ({step.transfer_time} min). Arrive {atStr}.
                                                </li>
                                            );
                                        }
                                        if (step.mode === "trip") {
                                            return (
                                                <li key={idx} className="text-sm">
                                                    Board {step.route?.id || step.route_id}
                                                    {step.trip?.id ? ` (${step.trip.id})` : ""} at{" "}
                                                    {step.board_stop?.name || step.board_stop_id}. Disembark at{" "}
                                                    {step.disembark_stop?.name || step.disembark_stop_id}. Arrive {atStr}.
                                                </li>
                                            );
                                        }
                                        return (
                                            <li key={idx} className="text-sm">
                                                [{step.mode}] arrive {atStr} at {step.stop?.name || step.stop_id}
                                            </li>
                                        );
                                    })}
                                </ol>
                            </div>
                        )}
                        <button
                            type="button"
                            className="mt-3 bg-[#001f4d] py-2 px-3 rounded hover:bg-[#003366]"
                            onClick={planPublicTransport}
                            disabled={planning}
                        >
                            {planning ? "Planning..." : "Replan PT"}
                        </button>
                    </div>
                </aside>

                {/* Map + Ads */}
                <div className="flex-1 flex flex-col">
                    <div className="flex-1 relative">
                        <div id="map" className="w-full h-full border-2 border-gray-300 rounded-md"></div>
                    </div>

                    {/* Advertisement Squares */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4">
                        <img src="/ad1.png" alt="Advertisement 1" className="h-60 w-full object-cover rounded" />
                        <img src="/ad2.png" alt="Advertisement 2" className="h-60 w-full object-cover rounded" />
                        <img src="/ad3.png" alt="Advertisement 3" className="h-60 w-full object-cover rounded" />
                    </div>
                </div>
            </div>

            {/* Footer */}
            <footer className="w-full bg-black text-white text-center py-3 mt-auto">
                <p>&copy; 2025 PathPilot</p>
                <p>Email: PathPilot@gmail.com</p>
                <p>Contact No: +27747618921</p>
            </footer>

            {/* Toast Notification */}
            {toastMessage && (
                <div
                    className={`fixed bottom-4 right-4 px-4 py-2 rounded shadow-lg text-white ${toastMessage.error ? "bg-red-500" : "bg-green-600"
                        }`}
                >
                    {toastMessage.text}
                </div>
            )}
        </div>
    );
}
