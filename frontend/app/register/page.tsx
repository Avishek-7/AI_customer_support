"use client";

import { useState } from "react";

export default function RegisterPage() {
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");

    const register = async () => {
        if (password !== confirmPassword) {
            alert("Passwords do not match");
            return;
        }

        const response = await fetch("http://localhost:8000/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password, full_name: username })
        });

        const data = await response.json();
        if (data.token) {
            localStorage.setItem("token", data.token);
            alert("Registration successful!");
            window.location.href = "/chat";
        } else if (data.detail) {
            alert(data.detail);
        }
    };

    return (
        <div className="flex items-center justify-center h-screen bg-gray-900 text-white">
            <div className="bg-gray-800 p-6 rounded-lg w-80 space-y-4">
                <h2 className="text-xl font-semibold">Register</h2>

                <input className="w-full px-2 py-2 rounded bg-gray-700 text-white"
                    placeholder="Username" value={username} onChange={e=>setUsername(e.target.value)} />

                <input className="w-full px-2 py-2 rounded bg-gray-700 text-white"
                    placeholder="Email" value={email} onChange={e=>setEmail(e.target.value)} />
                
                <input className="w-full px-2 py-2 rounded bg-gray-700 text-white"
                    type="password" placeholder="Password"
                    value={password} onChange={e=>setPassword(e.target.value)} />
                <input className="w-full px-2 py-2 rounded bg-gray-700 text-white"
                    type="password" placeholder="Confirm Password"
                    value={confirmPassword} onChange={e=>setConfirmPassword(e.target.value)} />
                
                <button onClick={register}
                    className="w-full bg-blue-600 hover:bg-blue-700 rounded py-2">
                        Register
                    </button>

            </div>
        </div>
    )

}