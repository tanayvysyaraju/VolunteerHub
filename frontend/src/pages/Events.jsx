// src/pages/Events.jsx
import React from "react";
const API_URL = "http://localhost:8080";

export default function Events({ user }) {
  const logout = async () => {
    await fetch(`${API_URL}/auth/logout`, { method: "POST", credentials: "include" });
    window.location.href = "/login";
  };
  return (
    <div style={{ padding: 24 }}>
      <h2>Events</h2>
      <p>Welcome {user?.full_name || user?.email}</p>
      <button onClick={logout}>Logout</button>
    </div>
  );
}