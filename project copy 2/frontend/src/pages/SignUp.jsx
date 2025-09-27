import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";

export default function SignUp() {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        name: "",
        surname: "",
        email: "",
        username: "",
        password: "",
    });

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSignUp = async (e) => {
        e.preventDefault();

        try {
            const res = await fetch("http://127.0.0.1:8000/api/signup/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(formData),
            });

            const data = await res.json();
            console.log("Signup response:", data);

            if (res.ok) {
                alert("Signup successful! Please log in.");
                navigate("/");
            } else {
                alert(data.error || "Signup failed");
            }
        } catch (error) {
            console.error("Signup error:", error);
            alert("Something went wrong. Try again.");
        }
    };

    return (
        <div className="flex flex-col min-h-screen w-screen bg-[#d3d3d3]">
            <header className="w-full bg-[#001f4d] text-white flex items-center justify-start py-3 px-4">
                <img src="/logo.png" alt="PathPilot Logo" className="h-[60px]" />
                <span className="text-xl font-bold ml-2">YOUR JOURNEY, OUR GUIDE</span>
            </header>

            <div className="flex-1 relative w-full flex justify-center items-center p-4">
                <video autoPlay muted loop playsInline aria-hidden="true" tabIndex={-1}
                    className="absolute inset-0 w-full h-full object-cover z-0 opacity-80 pointer-events-none hidden sm:block">
                    <source src="/vid.mp4" type="video/mp4" />
                </video>

                <form
                    className="relative z-[9999] pointer-events-auto flex flex-col items-center bg-white bg-opacity-90 p-6 sm:p-12 rounded-md shadow-lg w-full max-w-md sm:max-w-lg md:max-w-xl lg:max-w-2xl overflow-auto"
                    onSubmit={handleSignUp}
                >
                    <h2 className="text-[#001f4d] text-3xl sm:text-4xl font-bold mb-6">Sign Up</h2>

                    {["name", "surname", "email", "username", "password"].map((field) => (
                        <div key={field} className="w-full mb-4">
                            <label htmlFor={field} className="text-[#001f4d] mb-2 w-full text-left text-lg capitalize">
                                {field}:
                            </label>
                            <input
                                type={field === "password" ? "password" : field === "email" ? "email" : "text"}
                                id={field}
                                name={field}
                                required
                                value={formData[field]}
                                onChange={handleChange}
                                className="border border-[#001f4d] rounded p-3 w-full text-base sm:text-lg focus:outline-none focus:ring-2 focus:ring-[#001f4d] text-black"
                            />
                        </div>
                    ))}

                    <button type="submit" className="bg-[#001f4d] text-white py-3 rounded w-full hover:bg-[#003366] text-base sm:text-lg">
                        Sign Up
                    </button>

                    <p className="mt-4 text-base text-center text-black">
                        Already have an account?{" "}
                        <Link to="/" className="text-[#001f4d] underline">Log In</Link>
                    </p>
                </form>
            </div>

            <footer className="w-full bg-black text-white text-center py-3">
                <p>&copy; 2025 PathPilot</p>
                <p>Email: PathPilot@gmail.com</p>
                <p>Contact No: +27747618921</p>
            </footer>
        </div>
    );
}

