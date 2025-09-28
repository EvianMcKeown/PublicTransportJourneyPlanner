import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function FAQ() {
    const navigate = useNavigate();

    // FAQ questions and answers
    const faqs = [
        {
            question: "How do I plan a journey?",
            answer:
                "Enter your starting point and destination in the search fields. Select your route preferences (Optional). The planner will generate the best routes for you.",
        },
        {
            question: "Can I see save routes so that i can view them again?",
            answer: "Yes, after searcging for a route click the Save Current Route button on the left of your screen. That specifc route will the be saved and you can access it via the saved routes page which you can access from the button on your header",
        },

        {
            question: "Can I use the planner on my phone?",
            answer: "Yes, the website is fully mobile-friendly.",
        },
    ];

    const [visibleIndex, setVisibleIndex] = useState(null);

    const toggleFAQ = (index) => {
        setVisibleIndex(visibleIndex === index ? null : index);
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
                <h1 className="text-3xl sm:text-4xl font-bold mb-6 text-[#001f4d]">Help and FAQs</h1>

                <button
                    onClick={() => navigate("/home")}
                    className="mb-6 bg-[#001f4d] text-white py-2 px-4 rounded hover:bg-[#003366]"
                >
                    ← Back to Home
                </button>

                {/* Video Section */}
                <section className="mb-8 w-full max-w-3xl">
                    <h2 className="text-2xl font-semibold mb-4 text-[#001f4d]">Watch the help video below</h2>
                    <div className="aspect-w-16 aspect-h-9">
                        <iframe
                            src="/vid.mp4" type="video/mp4"
                            title="Journey plan walkthrough"
                            className="w-full h-[315px] sm:h-[500px]"
                            allowFullScreen
                        ></iframe>
                    </div>
                </section>

                {/* FAQ Section */}
                <section className="w-full max-w-3xl">
                    <h2 className="text-2xl font-semibold mb-4 text-[#001f4d]">Frequently Asked Questions</h2>
                    {faqs.map((faq, index) => (
                        <div key={index} className="mb-4 border-b border-gray-300 pb-2">
                            <button
                                className="w-full text-left text-lg font-medium text-white hover:text-[#003366]"
                                onClick={() => toggleFAQ(index)}
                            >
                                {faq.question}
                            </button>
                            {visibleIndex === index && (
                                <p className="mt-2 text-black text-base">{faq.answer}</p>
                            )}
                        </div>
                    ))}
                </section>
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
