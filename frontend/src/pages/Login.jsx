// src/pages/Login.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
const API_URL = "http://localhost:8080";

export default function Login({ onLogin }) {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async e => {
    e.preventDefault();
    setError("");
    const res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return setError(data.error || "Login failed");
    onLogin?.(data.user);
    nav("/events", { replace: true });
  };

  return (
    <form onSubmit={handleSubmit} style={{ maxWidth: 420, margin: "4rem auto" }}>
      <h2>Login</h2>
      <label>Email</label>
      <input type="email" value={email} onChange={e => setEmail(e.target.value)} required autoFocus />
      <label>Password</label>
      <input type="password" value={password} onChange={e => setPassword(e.target.value)} required />
      {error && <div style={{ color: "red", marginTop: 8 }}>{error}</div>}
      <button type="submit" style={{ marginTop: 12 }}>Login</button>
    </form>
  );
}