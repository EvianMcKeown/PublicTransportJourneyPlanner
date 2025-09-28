import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function UserSettings() {
    const navigate = useNavigate();
    const token = localStorage.getItem("access");

    const [user, setUser] = useState({
        username: "",
        email: "",
        first_name: "",
        last_name: "",
    });
    const [passwords, setPasswords] = useState({
        old_password: "",
        new_password: "",
    });
    const [message, setMessage] = useState("");

    // Fetch current user data
    useEffect(() => {
        if (!token) {
            navigate("/login");
            return;
        }

        fetch("http://localhost:8000/api/user/", {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then((res) => {
                if (!res.ok) throw new Error("Failed to fetch user");
                return res.json();
            })
            .then((data) => {
                setUser({
                    username: data.username || "",
                    email: data.email || "",
                    first_name: data.first_name || "",
                    last_name: data.last_name || "",
                });
            })
            .catch((err) => {
                console.error(err);
                setMessage("⚠️ Could not load user data");
            });
    }, [token, navigate]);

    const handleProfileUpdate = async (e) => {
        e.preventDefault();
        const res = await fetch("http://localhost:8000/api/user/", {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(user),
        });
        setMessage(res.ok ? "Profile updated ✅" : "Failed to update ❌");
    };

    const handlePasswordChange = async (e) => {
        e.preventDefault();
        try {
            const res = await fetch("http://localhost:8000/api/user/change_password/", {
                method: "PUT", // ✅ backend expects PUT
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify(passwords),
            });

            const data = await res.json();
            console.log("Password change response:", data);

            if (res.ok) {
                // ✅ Show success message but keep logged in
                setMessage("✅ Password changed successfully!");
                setPasswords({ old_password: "", new_password: "" }); // clear form
            } else {
                setMessage(
                    data.detail ||
                    data.error ||
                    (typeof data === "object" ? JSON.stringify(data) : "Failed to change password ❌")
                );
            }
        } catch (err) {
            console.error(err);
            setMessage("⚠️ Network error while changing password");
        }
    };

    return (
        <div className="flex flex-col min-h-screen w-screen bg-[#d3d3d3]">
            {/* Header */}
            <header className="w-full bg-[#001f4d] text-white flex items-center justify-start py-3 px-4">
                <img src="/logo.png" alt="PathPilot Logo" className="h-[60px]" />
                <span className="text-xl font-bold ml-2">YOUR JOURNEY, OUR GUIDE</span>
            </header>

            {/* Main Content */}
            <div className="flex-1 flex flex-col items-center justify-start p-6 sm:p-12">
                <h1 className="text-3xl sm:text-4xl font-bold mb-6 text-[#001f4d]">
                    User Settings
                </h1>

                <button
                    onClick={() => navigate("/home")}
                    className="mb-6 bg-[#001f4d] text-white py-2 px-4 rounded hover:bg-[#003366]"
                >
                    ← Back to Home
                </button>

                {message && (
                    <p className="mb-4 text-lg font-medium text-[#001f4d]">{message}</p>
                )}

                {/* Profile Form */}
                <form
                    onSubmit={handleProfileUpdate}
                    className="mb-10 w-full max-w-lg bg-white p-6 rounded shadow space-y-4"
                >
                    <h2 className="text-2xl font-semibold text-[#001f4d]">
                        Update Profile
                    </h2>
                    <input
                        type="text"
                        placeholder="Username"
                        value={user.username || ""}
                        onChange={(e) => setUser({ ...user, username: e.target.value })}
                        className="border p-2 w-full rounded bg-white text-black placeholder-gray-700"
                    />
                    <input
                        type="email"
                        placeholder="Email"
                        value={user.email || ""}
                        onChange={(e) => setUser({ ...user, email: e.target.value })}
                        className="border p-2 w-full rounded bg-white text-black placeholder-gray-700"
                    />
                    <input
                        type="text"
                        placeholder="First Name"
                        value={user.first_name || ""}
                        onChange={(e) => setUser({ ...user, first_name: e.target.value })}
                        className="border p-2 w-full rounded bg-white text-black placeholder-gray-700"
                    />
                    <input
                        type="text"
                        placeholder="Last Name"
                        value={user.last_name || ""}
                        onChange={(e) => setUser({ ...user, last_name: e.target.value })}
                        className="border p-2 w-full rounded bg-white text-black placeholder-gray-700"
                    />
                    <button
                        type="submit"
                        className="bg-[#001f4d] text-white px-4 py-2 rounded hover:bg-[#003366]"
                    >
                        Save Changes
                    </button>
                </form>

                {/* Password Form */}
                <form
                    onSubmit={handlePasswordChange}
                    className="w-full max-w-lg bg-white p-6 rounded shadow space-y-4"
                >
                    <h2 className="text-2xl font-semibold text-[#001f4d]">
                        Change Password
                    </h2>
                    <input
                        type="password"
                        placeholder="Old Password"
                        value={passwords.old_password}
                        onChange={(e) =>
                            setPasswords({ ...passwords, old_password: e.target.value })
                        }
                        className="border p-2 w-full rounded bg-white text-black placeholder-gray-700"
                    />
                    <input
                        type="password"
                        placeholder="New Password"
                        value={passwords.new_password}
                        onChange={(e) =>
                            setPasswords({ ...passwords, new_password: e.target.value })
                        }
                        className="border p-2 w-full rounded bg-white text-black placeholder-gray-700"
                    />
                    <button
                        type="submit"
                        className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                    >
                        Change Password
                    </button>
                </form>
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
