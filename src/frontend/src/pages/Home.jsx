import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { jwtDecode } from "jwt-decode";

export default function Home() {
    const [isSuperUser, setIsSuperUser] = useState(false);
    const [lastStart, setLastStart] = useState(null);
    const [lastEnd, setLastEnd] = useState(null);
    const [toastMessage, setToastMessage] = useState(null);
    const [routeInfo, setRouteInfo] = useState(null);
    const [ptJourney, setPtJourney] = useState(null);
    const [planning, setPlanning] = useState(false);
    const navigate = useNavigate();

    // Defaults for PT day/time (Mon=0..Sun=6) and "HH:MM"
    const now = new Date();
    const [ptDay, setPtDay] = useState((now.getDay() + 6) % 7);
    const [ptTime, setPtTime] = useState(`${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`);

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
            const API_BASE = import.meta.env.DEV ? "http://127.0.0.1:8000" : "";
            const resp = await fetch(`${API_BASE}/api/plan/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    source_id: sourceId,
                    target_id: targetId,
                    day: ptDay,
                    time: ptTime, // "HH:MM"
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

    const handleLogout = () => {
        localStorage.removeItem("access");
        navigate("/");
    };

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
                body: JSON.stringify({ start_location: start, end_location: end }),
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

    const calculateAndDisplayRoute = () => {
        const startPlace = autocompleteStart?.getPlace();
        const endPlace = autocompleteEnd?.getPlace();

        if (!startPlace?.geometry || !endPlace?.geometry) {
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
            const map = new window.google.maps.Map(document.getElementById("map"), {
                zoom: 12,
                center,
                mapTypeControl: false,
                streetViewControl: false,
                fullscreenControl: true,
            });

            directionsService = new window.google.maps.DirectionsService();
            directionsRenderer = new window.google.maps.DirectionsRenderer({ map });

            initAutocomplete();
        };

        if (window.google?.maps) {
            initMap();
        } else {
            console.error("Google Maps failed to load. Check your API key and index.html setup.");
        }
    }, []);

    return (
        <div className="flex flex-col h-screen w-screen overflow-hidden bg-gradient-to-br from-slate-900 via-slate-950 to-black">
            {/* Header (glass) */}
            <header className="w-full text-white flex items-center justify-between py-3 px-6 gap-4 bg-white/10 backdrop-blur-md border-b border-white/10 shadow-lg">
                <div className="flex items-center gap-2">
                    <img src="/logo.png" alt="PathPilot Logo" className="h-[48px] w-[48px] rounded-lg ring-1 ring-white/20" />
                    <span className="text-xl font-semibold tracking-wide">YOUR JOURNEY, OUR GUIDE</span>
                </div>

                <nav className="flex gap-2 items-center">
                    <Link to="/savedroutes" className="px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 border border-white/10">
                        Saved Routes
                    </Link>
                    <Link to="/faq" className="px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 border border-white/10">
                        FAQ
                    </Link>
                    <Link to="/settings" className="px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 border border-white/10">
                        User Settings
                    </Link>
                    {isSuperUser && (
                        <a
                            href="http://127.0.0.1:8000/admin/"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 border border-white/10"
                        >
                            Admin Panel
                        </a>
                    )}
                    <button
                        onClick={handleLogout}
                        className="px-3 py-1 rounded-lg bg-rose-500/80 hover:bg-rose-500 text-white"
                    >
                        Logout
                    </button>
                </nav>
            </header>

            {/* Sidebar + Map */}
            <div className="flex w-full gap-6 p-4 flex-1 overflow-hidden">
                {/* Sidebar (glass, scrolls independently) */}
                <aside className="w-64 text-slate-100 p-4 rounded-2xl flex flex-col gap-4 h-full overflow-y-auto bg-white/10 backdrop-blur-lg border border-white/10 shadow-xl">
                    {/* Search */}
                    <form
                        className="flex flex-col gap-2 mb-2"
                        onSubmit={(e) => {
                            e.preventDefault();
                            calculateAndDisplayRoute();
                        }}
                    >
                        <input
                            id="start"
                            type="text"
                            placeholder="Start"
                            className="bg-white/10 text-white placeholder-white/60 border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                        />
                        <input
                            id="end"
                            type="text"
                            placeholder="Destination"
                            className="bg-white/10 text-white placeholder-white/60 border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                        />

                        {/* Day of week + time (defaults to now) */}
                        <div className="flex gap-2">
                            <select
                                aria-label="Day of week"
                                className="flex-1 bg-white/10 text-white border border-white/10 rounded-lg px-2 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                                value={ptDay}
                                onChange={(e) => setPtDay(parseInt(e.target.value))}
                                title="Select day of week for public transport plan"
                            >
                                <option value={0}>Mon</option>
                                <option value={1}>Tue</option>
                                <option value={2}>Wed</option>
                                <option value={3}>Thu</option>
                                <option value={4}>Fri</option>
                                <option value={5}>Sat</option>
                                <option value={6}>Sun</option>
                            </select>
                            <input
                                aria-label="Time"
                                type="time"
                                className="flex-1 bg-white/10 text-white border border-white/10 rounded-lg px-2 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                                value={ptTime}
                                onChange={(e) => setPtTime(e.target.value)}
                                title="Select time for public transport plan"
                            />
                        </div>

                        <button
                            id="searchBtn"
                            type="submit"
                            className="mt-1 bg-indigo-500 hover:bg-indigo-600 text-white px-3 py-2 rounded-lg shadow"
                        >
                            Find Routes
                        </button>
                    </form>

                    {/* Preferences */}
                    <h2 className="text-lg font-semibold">Preferences</h2>
                    <form className="flex flex-col gap-2">
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input type="checkbox" name="minWalking" className="accent-indigo-500" />
                            Minimise walking
                        </label>
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input type="checkbox" name="minStops" className="accent-indigo-500" />
                            Minimise stops
                        </label>
                    </form>

                    <button
                        type="button"
                        className="bg-emerald-500 hover:bg-emerald-600 text-white px-3 py-2 rounded-lg shadow"
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
                        <div className="mt-4 p-4 rounded-xl bg-white/10 backdrop-blur-md border border-white/10 text-center shadow">
                            <h3 className="font-semibold">{lastStart}</h3>
                            <div className="flex flex-col items-center relative my-4">
                                <div className="w-px h-16 bg-white/40"></div>
                                <div className="absolute animate-car">🚗</div>
                            </div>
                            <h3 className="font-semibold">{lastEnd}</h3>

                            {routeInfo && (
                                <div className="mt-4 text-sm text-white/80">
                                    <p>Distance: {routeInfo.distance}</p>
                                    <p>Duration: {routeInfo.duration}</p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Public Transport Itinerary */}
                    <div className="mt-4 p-4 rounded-xl bg-white/10 backdrop-blur-md border border-white/10 shadow">
                        <h2 className="text-lg font-semibold mb-2">Public Transport</h2>
                        {!ptJourney && <p className="text-sm text-white/70">Search to see an itinerary.</p>}
                        {ptJourney && (
                            <div className="space-y-2">
                                <p className="text-sm">
                                    Earliest arrival: <span className="font-semibold">{minsToStr(ptJourney.earliest_arrival)}</span>
                                </p>
                                <ol className="list-decimal list-inside space-y-2 text-sm">
                                    {ptJourney.path_objs.map((step, idx) => {
                                        const atStr = minsToStr(step.arrival_time);
                                        if (step.mode === "start") {
                                            return (
                                                <li key={idx}>
                                                    Start at {step.stop?.name || step.stop_id} at {atStr}
                                                </li>
                                            );
                                        }
                                        if (step.mode === "transfer") {
                                            return (
                                                <li key={idx}>
                                                    Walk from {step.from_stop?.name || step.from_stop_id} to{" "}
                                                    {step.stop?.name || step.stop_id} ({step.transfer_time} min). Arrive {atStr}.
                                                </li>
                                            );
                                        }
                                        if (step.mode === "trip") {
                                            return (
                                                <li key={idx}>
                                                    Board {step.route?.id || step.route_id}
                                                    {step.trip?.id ? ` (${step.trip.id})` : ""} at{" "}
                                                    {step.board_stop?.name || step.board_stop_id}. Disembark at{" "}
                                                    {step.disembark_stop?.name || step.disembark_stop_id}. Arrive {atStr}.
                                                </li>
                                            );
                                        }
                                        return (
                                            <li key={idx}>
                                                [{step.mode}] arrive {atStr} at {step.stop?.name || step.stop_id}
                                            </li>
                                        );
                                    })}
                                </ol>
                            </div>
                        )}
                        <button
                            type="button"
                            className="mt-3 bg-indigo-500 hover:bg-indigo-600 text-white py-2 px-3 rounded-lg shadow"
                            onClick={planPublicTransport}
                            disabled={planning}
                        >
                            {planning ? "Planning..." : "Replan PT"}
                        </button>
                    </div>
                </aside>

                {/* Map + Ads column (flexible map height) */}
                <div className="flex-1 flex flex-col min-h-0">
                    {/* Map fills remaining space above ads; meets ads grid with standard margin */}
                    <div className="flex-1 min-h-0">
                        <div
                            id="map"
                            className="w-full h-full rounded-2xl bg-white/5 ring-1 ring-white/10 shadow-2xl"
                            aria-label="Map"
                        />
                    </div>

                    {/* Advertisement grid with usual margin from the map */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4">
                        <img src="/ad1.png" alt="Advertisement 1" className="h-60 w-full object-cover rounded-2xl shadow-lg ring-1 ring-white/10 bg-white/5" />
                        <img src="/ad2.png" alt="Advertisement 2" className="h-60 w-full object-cover rounded-2xl shadow-lg ring-1 ring-white/10 bg-white/5" />
                        <img src="/ad3.png" alt="Advertisement 3" className="h-60 w-full object-cover rounded-2xl shadow-lg ring-1 ring-white/10 bg-white/5" />
                    </div>
                </div>
            </div>

            {/* Footer (glass) */}
            <footer className="w-full text-white text-center py-3 mt-0 bg-white/10 backdrop-blur-md border-t border-white/10">
                <p>&copy; 2025 PathPilot</p>
                <p>Email: PathPilot@gmail.com</p>
                <p>Contact No: +27747618921</p>
            </footer>

            {/* Toast */}
            {toastMessage && (
                <div
                    className={`fixed bottom-4 right-4 px-4 py-2 rounded-lg shadow-xl text-white ${toastMessage.error ? "bg-rose-600/90" : "bg-emerald-600/90"}`}
                >
                    {toastMessage.text}
                </div>
            )}
        </div>
    );
}