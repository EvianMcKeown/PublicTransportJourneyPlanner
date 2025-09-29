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
        const startPlace = autocompleteStartRef.current?.getPlace();
        const endPlace = autocompleteEndRef.current?.getPlace();

        if (!startPlace?.geometry?.location || !endPlace?.geometry?.location) {
            showToast("Please select valid locations from dropdown", true);
            return;
        }

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
                showToast("Route saved successfully!");
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

            directionsServiceRef.current = new window.google.maps.DirectionsService();
            directionsRendererRef.current = new window.google.maps.DirectionsRenderer({ map });

            initAutocomplete();
        };
        if (window.google?.maps) initMap();
        else console.error("Google Maps failed to load.");
    }, []);

    return (
        <div className="flex flex-col h-screen w-screen overflow-hidden bg-gray-800">
            {/* Header */}
            <header className="w-full text-white flex items-center justify-between py-4 px-6 gap-4 bg-white/5 backdrop-blur-xl border-b border-white/10 shadow-2xl">
                <div className="flex items-center gap-3">
                    <img src="/logo.png" alt="PathPilot Logo" className="h-[48px] w-[48px] rounded-xl ring-2 ring-white/20 shadow-lg" />
                    <span className="text-xl font-bold tracking-wide bg-gradient-to-r from-white to-blue-200 bg-clip-text text-transparent">YOUR JOURNEY, OUR GUIDE</span>
                </div>
                <nav className="flex gap-3 items-center">
                    <Link to="/savedroutes" className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 backdrop-blur-md transition-all duration-300 hover:shadow-lg text-white">
                        Saved Routes
                    </Link>
                    <Link to="/faq" className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 backdrop-blur-md transition-all duration-300 hover:shadow-lg text-white">
                        FAQ
                    </Link>
                    <Link to="/settings" className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 backdrop-blur-md transition-all duration-300 hover:shadow-lg text-white">
                        User Settings
                    </Link>
                    {isSuperUser && (
                        <a href="http://127.0.0.1:8000/admin/" target="_blank" rel="noopener noreferrer"
                            className="px-4 py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-400/30 backdrop-blur-md transition-all duration-300 hover:shadow-lg text-white">
                            Admin Panel
                        </a>
                    )}
                    <button onClick={handleLogout} className="px-4 py-2 rounded-xl bg-red-500/20 hover:bg-red-500/30 border border-red-400/30 backdrop-blur-md text-white transition-all duration-300 hover:shadow-lg">
                        Logout
                    </button>
                </nav>
            </header>

            {/* Sidebar + Map */}
            <div className="flex w-full gap-6 p-6 flex-1 overflow-hidden">
                <aside className="w-72 text-slate-100 p-6 rounded-2xl flex flex-col gap-6 h-full overflow-y-auto bg-white/10 backdrop-blur-2xl border border-white/20 shadow-2xl">
                    <form className="flex flex-col gap-3 mb-4" onSubmit={(e) => { e.preventDefault(); handleFindRoutes(); }}>
                        <input id="start" type="text" placeholder="Start Location"
                            className="bg-white/10 text-white placeholder-white/70 border border-white/20 rounded-xl px-4 py-3 backdrop-blur-md focus:ring-2 focus:ring-blue-400/50 focus:border-blue-400/50 transition-all duration-300" />
                        <input id="end" type="text" placeholder="Destination"
                            className="bg-white/10 text-white placeholder-white/70 border border-white/20 rounded-xl px-4 py-3 backdrop-blur-md focus:ring-2 focus:ring-blue-400/50 focus:border-blue-400/50 transition-all duration-300" />
                        <div className="flex gap-3">
                            <select className="flex-1 bg-white/10 text-white border border-white/20 rounded-xl px-3 py-3 backdrop-blur-md focus:ring-2 focus:ring-blue-400/50"
                                value={ptDay} onChange={(e) => setPtDay(parseInt(e.target.value))}>
                                <option value={0}>Monday</option>
                                <option value={1}>Tuesday</option>
                                <option value={2}>Wednesday</option>
                                <option value={3}>Thursday</option>
                                <option value={4}>Friday</option>
                                <option value={5}>Saturday</option>
                                <option value={6}>Sunday</option>
                            </select>
                            <input type="time" className="flex-1 bg-white/10 text-white border border-white/20 rounded-xl px-3 py-3 backdrop-blur-md focus:ring-2 focus:ring-blue-400/50"
                                value={ptTime} onChange={(e) => setPtTime(e.target.value)} />
                        </div>
                        <button id="searchBtn" type="submit"
                            className="mt-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white px-4 py-3 rounded-xl shadow-lg backdrop-blur-md border border-white/20 transition-all duration-300 hover:shadow-xl disabled:opacity-50"
                            disabled={planning}>
                            {planning ? "Planning Routes..." : "Find Routes"}
                        </button>
                    </form>

                    {/* Preferences */}
                    <div className="bg-white/5 backdrop-blur-md rounded-xl p-4 border border-white/10">
                        <h2 className="text-lg font-semibold mb-3 text-blue-200">Journey Preferences</h2>
                        <form className="flex flex-col gap-3">
                            <label className="flex items-center gap-3 cursor-pointer hover:bg-white/5 rounded-lg p-2 transition-all duration-200">
                                <input type="checkbox" name="minWalking" className="accent-blue-500 w-4 h-4" />
                                <span>Minimize walking distance</span>
                            </label>
                            <label className="flex items-center gap-3 cursor-pointer hover:bg-white/5 rounded-lg p-2 transition-all duration-200">
                                <input type="checkbox" name="minStops" className="accent-blue-500 w-4 h-4" />
                                <span>Minimize number of stops</span>
                            </label>
                        </form>
                    </div>

                    <button type="button"
                        className="bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white px-4 py-3 rounded-xl shadow-lg backdrop-blur-md border border-white/20 transition-all duration-300 hover:shadow-xl"
                        onClick={() => { if (!lastStart || !lastEnd) { showToast("Please search for a route first.", true); return; } saveRoute(lastStart, lastEnd); }}>
                        Save Current Route
                    </button>

                    {/* Driving Route Summary */}
                    {lastStart && lastEnd && (
                        <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl p-5 border border-white/20 text-center shadow-xl">
                            <h3 className="font-semibold text-blue-200 mb-3">{lastStart}</h3>
                            <div className="flex flex-col items-center relative my-6">
                                <div className="w-px h-20 bg-gradient-to-b from-blue-400 to-indigo-400 opacity-60"></div>
                                <div className="absolute top-1/2 transform -translate-y-1/2 w-3 h-3 bg-blue-400 rounded-full animate-pulse"></div>
                            </div>
                            <h3 className="font-semibold text-blue-200 mb-3">{lastEnd}</h3>
                            {routeInfo && (
                                <div className="mt-4 p-3 rounded-xl bg-white/10 backdrop-blur-md border border-white/10">
                                    <div className="text-sm text-white/90 space-y-1">
                                        <p><span className="text-blue-300">Distance:</span> {routeInfo.distance}</p>
                                        <p><span className="text-blue-300">Duration:</span> {routeInfo.duration}</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* PT Itinerary */}
                    <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl p-5 border border-white/20 shadow-xl">
                        <h2 className="text-lg font-semibold mb-4 text-blue-200">Public Transport</h2>
                        {!ptJourney && (
                            <div className="text-center py-8">
                                <div className="w-16 h-16 mx-auto mb-4 bg-white/10 rounded-full flex items-center justify-center backdrop-blur-md border border-white/20">
                                    <div className="w-8 h-8 bg-blue-400/30 rounded-full"></div>
                                </div>
                                <p className="text-sm text-white/70">Search to see an itinerary</p>
                            </div>
                        )}
                        {ptJourney && (
                            <div className="space-y-4">
                                <div className="bg-gradient-to-r from-emerald-500/20 to-teal-500/20 backdrop-blur-md rounded-xl p-4 border border-emerald-400/30">
                                    <p className="text-sm font-medium text-emerald-300">
                                        <span className="inline-block w-2 h-2 bg-emerald-400 rounded-full mr-2"></span>
                                        Earliest arrival: <span className="font-semibold">{minsToStr(ptJourney.earliest_arrival)}</span>
                                    </p>
                                    {ptJourney.path_objs.length > 1 && (
                                        <p className="text-xs text-white/70 mt-2">
                                            Total journey time: {Math.floor((ptJourney.earliest_arrival - ptJourney.path_objs[0].arrival_time) / 60)}h {(ptJourney.earliest_arrival - ptJourney.path_objs[0].arrival_time) % 60}m
                                        </p>
                                    )}
                                </div>

                                <div className="space-y-3 max-h-80 overflow-y-auto">
                                    {ptJourney.path_objs.map((step, idx) => {
                                        const atStr = minsToStr(step.arrival_time);

                                        if (step.mode === "start") {
                                            return (
                                                <div key={idx} className="flex items-start gap-4 p-4 rounded-xl bg-gradient-to-r from-blue-500/20 to-indigo-500/20 backdrop-blur-md border border-blue-400/30">
                                                    <div className="w-8 h-8 bg-blue-500/30 rounded-full flex items-center justify-center backdrop-blur-md border border-blue-400/50">
                                                        <div className="w-3 h-3 bg-blue-400 rounded-full"></div>
                                                    </div>
                                                    <div className="flex-1 text-sm">
                                                        <p className="font-medium text-blue-200">Start Journey</p>
                                                        <p className="text-white/80 mt-1">
                                                            From: <span className="font-medium">{step.stop?.name || step.stop_id}</span>
                                                        </p>
                                                        <p className="text-xs text-white/60 mt-1">Departure: {atStr}</p>
                                                    </div>
                                                </div>
                                            );
                                        }

                                        if (step.mode === "transfer") {
                                            return (
                                                <div key={idx} className="flex items-start gap-4 p-4 rounded-xl bg-gradient-to-r from-amber-500/20 to-orange-500/20 backdrop-blur-md border border-amber-400/30">
                                                    <div className="w-8 h-8 bg-amber-500/30 rounded-full flex items-center justify-center backdrop-blur-md border border-amber-400/50">
                                                        <div className="w-3 h-3 bg-amber-400 rounded-full"></div>
                                                    </div>
                                                    <div className="flex-1 text-sm">
                                                        <p className="font-medium text-amber-200">Walk</p>
                                                        <p className="text-white/80 mt-1">
                                                            From: <span className="font-medium">{step.from_stop?.name || step.from_stop_id}</span>
                                                        </p>
                                                        <p className="text-white/80">
                                                            To: <span className="font-medium">{step.stop?.name || step.stop_id}</span>
                                                        </p>
                                                        <div className="flex justify-between items-center text-xs text-white/60 mt-2">
                                                            <span>Walk time: {step.transfer_time} min</span>
                                                            <span>Arrive: {atStr}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        }

                                        if (step.mode === "trip") {
                                            const routeName = step.route?.name || step.route_id;
                                            const isRail = step.route?.mode === 2;

                                            return (
                                                <div key={idx} className={`flex items-start gap-4 p-4 rounded-xl backdrop-blur-md border ${isRail
                                                    ? "bg-gradient-to-r from-green-500/20 to-emerald-500/20 border-green-400/30"
                                                    : "bg-gradient-to-r from-purple-500/20 to-violet-500/20 border-purple-400/30"
                                                    }`}>
                                                    <div className={`w-8 h-8 rounded-full flex items-center justify-center backdrop-blur-md border ${isRail
                                                        ? "bg-green-500/30 border-green-400/50"
                                                        : "bg-purple-500/30 border-purple-400/50"
                                                        }`}>
                                                        <div className={`w-3 h-3 rounded-full ${isRail ? "bg-green-400" : "bg-purple-400"
                                                            }`}></div>
                                                    </div>
                                                    <div className="flex-1 text-sm">
                                                        <p className={`font-medium ${isRail ? "text-green-200" : "text-purple-200"}`}>
                                                            {isRail ? "Train" : "Bus"}: {routeName}
                                                        </p>
                                                        <p className="text-white/80 mt-1">
                                                            Board: <span className="font-medium">{step.board_stop?.name || step.from_stop?.name}</span>
                                                        </p>
                                                        <p className="text-white/80">
                                                            Disembark: <span className="font-medium">{step.disembark_stop?.name || step.stop?.name}</span>
                                                        </p>
                                                        <div className="flex justify-between items-center text-xs text-white/60 mt-2">
                                                            <span>Stops: {step.disembark_pos - step.board_pos}</span>
                                                            <span>Arrive: {atStr}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        }

                                        return (
                                            <div key={idx} className="flex items-start gap-4 p-4 rounded-xl bg-gradient-to-r from-slate-500/20 to-gray-500/20 backdrop-blur-md border border-slate-400/30">
                                                <div className="w-8 h-8 bg-slate-500/30 rounded-full flex items-center justify-center backdrop-blur-md border border-slate-400/50">
                                                    <div className="w-3 h-3 bg-slate-400 rounded-full"></div>
                                                </div>
                                                <div className="flex-1 text-sm">
                                                    <p className="font-medium text-slate-200">{step.mode}</p>
                                                    <p className="text-white/80 mt-1">
                                                        At: <span className="font-medium">{step.stop?.name || step.stop_id}</span>
                                                    </p>
                                                    <p className="text-xs text-white/60 mt-1">Arrive: {atStr}</p>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>

                                <div className="bg-white/5 backdrop-blur-md rounded-xl p-3 border border-white/10 text-xs text-white/70">
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
                <div className="flex-1 flex flex-col min-h-0 gap-4">
                    <div className="flex-1 min-h-0">
                        <div id="map" className="w-full h-full rounded-2xl bg-white/5 ring-2 ring-white/10 shadow-2xl backdrop-blur-sm" aria-label="Map" />
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="h-32 rounded-2xl bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl border border-white/20 shadow-xl overflow-hidden">
                            <img src="/ad1.png" alt="Advertisement 1" className="w-full h-full object-cover" />
                        </div>
                        <div className="h-32 rounded-2xl bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl border border-white/20 shadow-xl overflow-hidden">
                            <img src="/ad2.png" alt="Advertisement 2" className="w-full h-full object-cover" />
                        </div>
                        <div className="h-32 rounded-2xl bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl border border-white/20 shadow-xl overflow-hidden">
                            <img src="/ad3.png" alt="Advertisement 3" className="w-full h-full object-cover" />
                        </div>
                    </div>
                </div>
            </div>

            {/* Footer */}
            <footer className="w-full text-white text-center py-4 bg-white/5 backdrop-blur-xl border-t border-white/10 shadow-2xl">
                <div className="text-sm text-white/80 space-y-1">
                    <p>&copy; 2025 PathPilot</p>
                    <p>Email: PathPilot@gmail.com</p>
                    <p>Contact No: +27747618921</p>
                </div>
            </footer>

            {/* Toasts */}
            {toastMessage && (
                <div className={`fixed bottom-6 right-6 px-6 py-4 rounded-xl shadow-2xl text-white backdrop-blur-xl border transition-all duration-300 ${toastMessage.error
                    ? "bg-red-500/20 border-red-400/30"
                    : "bg-emerald-500/20 border-emerald-400/30"
                    }`}>
                    {toastMessage.text}
                </div>
            )}
            {coordsMessage && (
                <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 px-8 py-6 rounded-2xl shadow-2xl text-white bg-blue-600/20 backdrop-blur-xl border border-blue-400/30 whitespace-pre text-sm text-center">
                    {coordsMessage}
                </div>
            )}
        </div>
    );
}