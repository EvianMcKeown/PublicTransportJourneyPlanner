import { useEffect, useState, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { jwtDecode } from "jwt-decode";

export default function Home() {
    const [isSuperUser, setIsSuperUser] = useState(false);
    const [lastStart, setLastStart] = useState(null);
    const [lastEnd, setLastEnd] = useState(null);
    const [toastMessage, setToastMessage] = useState(null);
    const [coordsMessage, setCoordsMessage] = useState(null);
    const [routeInfo, setRouteInfo] = useState(null);
    const [ptJourney, setPtJourney] = useState(null);
    const [planning, setPlanning] = useState(false);
    const navigate = useNavigate();

    const now = new Date();
    const [ptDay, setPtDay] = useState((now.getDay() + 6) % 7);
    const [ptTime, setPtTime] = useState(
        `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`
    );

    const autocompleteStartRef = useRef(null);
    const autocompleteEndRef = useRef(null);
    const directionsServiceRef = useRef(null);
    const directionsRendererRef = useRef(null);

    const minsToStr = (total) => {
        if (total == null) return "";
        const names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
        const day = Math.floor(total / 1440) % 7;
        const minsInDay = ((total % 1440) + 1440) % 1440;
        const hh = String(Math.floor(minsInDay / 60)).padStart(2, "0");
        const mm = String(minsInDay % 60).padStart(2, "0");
        return `${names[day]} ${hh}:${mm}`;
    };

    const planPublicTransport = async () => {
        // Get the place objects from autocomplete (same as in calculateAndDisplayRoute)
        const startPlace = autocompleteStartRef.current?.getPlace();
        const endPlace = autocompleteEndRef.current?.getPlace();

        if (!startPlace?.geometry?.location || !endPlace?.geometry?.location) {
            showToast("Please select valid locations from dropdown", true);
            return;
        }

        // Extract coordinates from the place objects
        const sourceLat = startPlace.geometry.location.lat();
        const sourceLon = startPlace.geometry.location.lng();
        const targetLat = endPlace.geometry.location.lat();
        const targetLon = endPlace.geometry.location.lng();

        console.log("PT Source coords:", sourceLat, sourceLon);
        console.log("PT Target coords:", targetLat, targetLon);

        setPlanning(true);
        setPtJourney(null);
        try {
            const API_BASE = import.meta.env.DEV ? "http://127.0.0.1:8000" : "";
            const resp = await fetch(`${API_BASE}/api/plan/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    source_lat: sourceLat,
                    source_lon: sourceLon,
                    target_lat: targetLat,
                    target_lon: targetLon,
                    day: ptDay,
                    time: ptTime,
                    max_rounds: 5,
                }),
            });
            const data = await resp.json();
            if (!resp.ok) {
                showToast(data.detail || data.error || `HTTP ${resp.status}`, true);
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

    const calculateAndDisplayRoute = () => {
        // Use refs instead of let variables
        const startPlace = autocompleteStartRef.current?.getPlace();
        const endPlace = autocompleteEndRef.current?.getPlace();

        if (!startPlace?.geometry || !endPlace?.geometry) {
            showToast("Please select valid locations from dropdown", true);
            return;
        }

        directionsServiceRef.current.route(
            {
                origin: { placeId: startPlace.place_id },
                destination: { placeId: endPlace.place_id },
                travelMode: window.google.maps.TravelMode.DRIVING,
            },
            (response, status) => {
                if (status === "OK") {
                    directionsRendererRef.current.setDirections(response);
                    setLastStart(startPlace.name);
                    setLastEnd(endPlace.name);

                    const leg = response.routes[0].legs[0];
                    setRouteInfo({
                        distance: leg.distance.text,
                        duration: leg.duration.text,
                    });

                    // NEW: lat/lng notification
                    const coords = [];
                    coords.push({
                        label: "Start",
                        lat: leg.start_location.lat(),
                        lng: leg.start_location.lng(),
                    });
                    (leg.via_waypoints || []).forEach((wp, idx) => {
                        coords.push({
                            label: `Stop ${idx + 1}`,
                            lat: wp.lat(),
                            lng: wp.lng(),
                        });
                    });
                    coords.push({
                        label: "End",
                        lat: leg.end_location.lat(),
                        lng: leg.end_location.lng(),
                    });

                    const msg = coords
                        .map(c => `${c.label}: (${c.lat.toFixed(5)}, ${c.lng.toFixed(5)})`)
                        .join("\n");

                    setCoordsMessage(msg);
                    setTimeout(() => setCoordsMessage(null), 5000);
                } else {
                    showToast("Directions request failed: " + status, true);
                }
            }
        );
    };

    const handleFindRoutes = async () => {
        // Call both functions and wait for the public transport one to complete
        calculateAndDisplayRoute();
        await planPublicTransport();
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

    useEffect(() => {
        const token = localStorage.getItem("access");
        if (token) {
            try {
                const decoded = jwtDecode(token);
                if (decoded.is_superuser) setIsSuperUser(true);
            } catch (err) {
                console.error("Error decoding token:", err);
            }
        }
        const initAutocomplete = () => {
            // Use refs instead of let variables
            autocompleteStartRef.current = new window.google.maps.places.Autocomplete(
                document.getElementById("start"),
                {
                    types: ["geocode"],
                    componentRestrictions: { country: ["ZA"] },
                    fields: ["place_id", "geometry", "name"],
                }
            );
            autocompleteEndRef.current = new window.google.maps.places.Autocomplete(
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

            // Use refs instead of let variables
            directionsServiceRef.current = new window.google.maps.DirectionsService();
            directionsRendererRef.current = new window.google.maps.DirectionsRenderer({ map });

            initAutocomplete();
        };
        if (window.google?.maps) initMap();
        else console.error("Google Maps failed to load.");
    }, []);

    return (
        <div className="flex flex-col h-screen w-screen overflow-hidden bg-gradient-to-br from-slate-900 via-slate-950 to-black">
            {/* Header */}
            <header className="w-full text-white flex items-center justify-between py-3 px-6 gap-4 bg-white/10 backdrop-blur-md border-b border-white/10 shadow-lg">
                <div className="flex items-center gap-2">
                    <img src="/logo.png" alt="PathPilot Logo" className="h-[48px] w-[48px] rounded-lg ring-1 ring-white/20" />
                    <span className="text-xl font-semibold tracking-wide">YOUR JOURNEY, OUR GUIDE</span>
                </div>
                <nav className="flex gap-2 items-center">
                    <Link to="/savedroutes" className="px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 border border-white/10">Saved Routes</Link>
                    <Link to="/faq" className="px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 border border-white/10">FAQ</Link>
                    <Link to="/settings" className="px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 border border-white/10">User Settings</Link>
                    {isSuperUser && (
                        <a href="http://127.0.0.1:8000/admin/" target="_blank" rel="noopener noreferrer" className="px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 border border-white/10">Admin Panel</a>
                    )}
                    <button onClick={handleLogout} className="px-3 py-1 rounded-lg bg-rose-500/80 hover:bg-rose-500 text-white">Logout</button>
                </nav>
            </header>

            {/* Sidebar + Map */}
            <div className="flex w-full gap-6 p-4 flex-1 overflow-hidden">
                <aside className="w-64 text-slate-100 p-4 rounded-2xl flex flex-col gap-4 h-full overflow-y-auto bg-white/10 backdrop-blur-lg border border-white/10 shadow-xl">
                    <form className="flex flex-col gap-2 mb-2" onSubmit={(e) => { e.preventDefault(); handleFindRoutes(); }}>
                        <input id="start" type="text" placeholder="Start" className="bg-white/10 text-white placeholder-white/60 border border-white/10 rounded-lg px-3 py-2" />
                        <input id="end" type="text" placeholder="Destination" className="bg-white/10 text-white placeholder-white/60 border border-white/10 rounded-lg px-3 py-2" />
                        <div className="flex gap-2">
                            <select className="flex-1 bg-white/10 text-white border border-white/10 rounded-lg px-2 py-2" value={ptDay} onChange={(e) => setPtDay(parseInt(e.target.value))}>
                                <option value={0}>Mon</option><option value={1}>Tue</option><option value={2}>Wed</option>
                                <option value={3}>Thu</option><option value={4}>Fri</option><option value={5}>Sat</option><option value={6}>Sun</option>
                            </select>
                            <input type="time" className="flex-1 bg-white/10 text-white border border-white/10 rounded-lg px-2 py-2" value={ptTime} onChange={(e) => setPtTime(e.target.value)} />
                        </div>
                        <button id="searchBtn" type="submit" className="mt-1 bg-indigo-500 hover:bg-indigo-600 text-white px-3 py-2 rounded-lg shadow">
                            {planning ? "Planning..." : "Find Routes"}
                        </button>
                    </form>

                    {/* Preferences */}
                    <h2 className="text-lg font-semibold">Preferences</h2>
                    <form className="flex flex-col gap-2">
                        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" name="minWalking" className="accent-indigo-500" />Minimise walking</label>
                        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" name="minStops" className="accent-indigo-500" />Minimise stops</label>
                    </form>

                    <button type="button" className="bg-emerald-500 hover:bg-emerald-600 text-white px-3 py-2 rounded-lg shadow"
                        onClick={() => { if (!lastStart || !lastEnd) { showToast("Please search first.", true); return; } saveRoute(lastStart, lastEnd); }}>
                        Save Current Route
                    </button>

                    {/* Driving Route Summary */}
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

                    {/* PT Itinerary */}
                    <div className="mt-4 p-4 rounded-xl bg-white/10 backdrop-blur-md border border-white/10 shadow">
                        <h2 className="text-lg font-semibold mb-2">Public Transport</h2>
                        {!ptJourney && <p className="text-sm text-white/70">Search to see an itinerary.</p>}
                        {ptJourney && (
                            <div className="space-y-3">
                                <div className="bg-white/10 rounded-lg p-3 border border-white/10">
                                    <p className="text-sm font-medium text-emerald-400">
                                        🎯 Earliest arrival: <span className="font-semibold">{minsToStr(ptJourney.earliest_arrival)}</span>
                                    </p>
                                    {ptJourney.path_objs.length > 1 && (
                                        <p className="text-xs text-white/70 mt-1">
                                            Total journey time: {Math.floor((ptJourney.earliest_arrival - ptJourney.path_objs[0].arrival_time) / 60)}h {(ptJourney.earliest_arrival - ptJourney.path_objs[0].arrival_time) % 60}m
                                        </p>
                                    )}
                                </div>

                                <div className="space-y-2 max-h-64 overflow-y-auto">
                                    {ptJourney.path_objs.map((step, idx) => {
                                        const atStr = minsToStr(step.arrival_time);

                                        if (step.mode === "start") {
                                            return (
                                                <div key={idx} className="flex items-start gap-3 p-2 rounded-lg bg-blue-500/20 border border-blue-500/30">
                                                    <span className="text-blue-400 text-lg">🚀</span>
                                                    <div className="flex-1 text-sm">
                                                        <p className="font-medium">Start Journey</p>
                                                        <p className="text-white/80">
                                                            From: <span className="font-medium">{step.stop?.name || step.stop_id}</span>
                                                        </p>
                                                        <p className="text-xs text-white/60">Departure: {atStr}</p>
                                                    </div>
                                                </div>
                                            );
                                        }

                                        if (step.mode === "transfer") {
                                            return (
                                                <div key={idx} className="flex items-start gap-3 p-2 rounded-lg bg-yellow-500/20 border border-yellow-500/30">
                                                    <span className="text-yellow-400 text-lg">🚶</span>
                                                    <div className="flex-1 text-sm">
                                                        <p className="font-medium">Walk</p>
                                                        <p className="text-white/80">
                                                            From: <span className="font-medium">{step.from_stop?.name || step.from_stop_id}</span>
                                                        </p>
                                                        <p className="text-white/80">
                                                            To: <span className="font-medium">{step.stop?.name || step.stop_id}</span>
                                                        </p>
                                                        <div className="flex justify-between items-center text-xs text-white/60 mt-1">
                                                            <span>Walk time: {step.transfer_time} min</span>
                                                            <span>Arrive: {atStr}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        }

                                        if (step.mode === "trip") {
                                            const routeName = step.route?.name || step.route_id;
                                            const modeIcon = step.route?.mode === 2 ? "🚂" : "🚌";
                                            const modeColor = step.route?.mode === 2 ? "green" : "purple";

                                            return (
                                                <div key={idx} className={`flex items-start gap-3 p-2 rounded-lg bg-${modeColor}-500/20 border border-${modeColor}-500/30`}>
                                                    <span className={`text-${modeColor}-400 text-lg`}>{modeIcon}</span>
                                                    <div className="flex-1 text-sm">
                                                        <p className="font-medium">
                                                            {step.route?.mode === 2 ? "Train" : "Bus"}: {routeName}
                                                        </p>
                                                        <p className="text-white/80">
                                                            Board: <span className="font-medium">{step.board_stop?.name || step.from_stop?.name}</span>
                                                        </p>
                                                        <p className="text-white/80">
                                                            Disembark: <span className="font-medium">{step.disembark_stop?.name || step.stop?.name}</span>
                                                        </p>
                                                        <div className="flex justify-between items-center text-xs text-white/60 mt-1">
                                                            <span>Stops: {step.disembark_pos - step.board_pos}</span>
                                                            <span>Arrive: {atStr}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        }

                                        // Fallback for unknown modes
                                        return (
                                            <div key={idx} className="flex items-start gap-3 p-2 rounded-lg bg-gray-500/20 border border-gray-500/30">
                                                <span className="text-gray-400 text-lg">❓</span>
                                                <div className="flex-1 text-sm">
                                                    <p className="font-medium">{step.mode}</p>
                                                    <p className="text-white/80">
                                                        At: <span className="font-medium">{step.stop?.name || step.stop_id}</span>
                                                    </p>
                                                    <p className="text-xs text-white/60">Arrive: {atStr}</p>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>

                                {/* Journey Summary */}
                                <div className="bg-white/5 rounded-lg p-2 border border-white/10 text-xs text-white/70">
                                    <div className="flex justify-between">
                                        <span>Total Steps: {ptJourney.path_objs.length}</span>
                                        <span>
                                            Transfers: {ptJourney.path_objs.filter(s => s.mode === "transfer").length}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </aside>

                {/* Map + Ads */}
                <div className="flex-1 flex flex-col min-h-0">
                    <div className="flex-1 min-h-0">
                        <div id="map" className="w-full h-full rounded-2xl bg-white/5 ring-1 ring-white/10 shadow-2xl" aria-label="Map" />
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-2">
                        <img src="/ad1.png" alt="Advertisement 1" className="h-32 w-full object-cover rounded-2xl shadow-lg ring-1 ring-white/10 bg-white/5" />
                        <img src="/ad2.png" alt="Advertisement 2" className="h-32 w-full object-cover rounded-2xl shadow-lg ring-1 ring-white/10 bg-white/5" />
                        <img src="/ad3.png" alt="Advertisement 3" className="h-32 w-full object-cover rounded-2xl shadow-lg ring-1 ring-white/10 bg-white/5" />
                    </div>
                </div>
            </div>

            {/* Footer */}
            <footer className="w-full text-white text-center py-3 mt-0 bg-white/10 backdrop-blur-md border-t border-white/10">
                <p>&copy; 2025 PathPilot</p>
                <p>Email: PathPilot@gmail.com</p>
                <p>Contact No: +27747618921</p>
            </footer>

            {/* Toasts */}
            {toastMessage && (
                <div className={`fixed bottom-4 right-4 px-4 py-2 rounded-lg shadow-xl text-white ${toastMessage.error ? "bg-rose-600/90" : "bg-emerald-600/90"}`}>
                    {toastMessage.text}
                </div>
            )}
            {coordsMessage && (
                <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 px-6 py-4 rounded-lg shadow-2xl text-white bg-indigo-600/90 whitespace-pre text-sm text-center">
                    {coordsMessage}
                </div>
            )}
        </div>
    );
}
