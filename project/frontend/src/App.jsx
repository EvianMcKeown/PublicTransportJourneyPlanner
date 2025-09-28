import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import SignUp from "./pages/SignUp";
import Home from "./pages/Home";
import FAQ from "./pages/FAQ";
import SavedRoutes from "./pages/SavedRoutes";
import UserSettings from "./pages/UserSettings";


function PrivateRoute({ children }) {
  const token = localStorage.getItem("access"); // make sure we check "access"
  return token ? children : <Navigate to="/" replace />;
}

export default function App() {
  return (
    <Router>
      <Routes>
        {/* Public pages */}
        <Route path="/" element={<Login />} />
        <Route path="/signup" element={<SignUp />} />

        {/* Protected pages */}
        <Route
          path="/home"
          element={
            <PrivateRoute>
              <Home />
            </PrivateRoute>
          }
        />
        <Route
          path="/faq"
          element={
            <PrivateRoute>
              <FAQ />
            </PrivateRoute>
          }
        />
        <Route
          path="/savedroutes"
          element={
            <PrivateRoute>
              <SavedRoutes />
            </PrivateRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <PrivateRoute>
              <UserSettings />
            </PrivateRoute>
          }
        />
      </Routes>
    </Router>
  );
}
