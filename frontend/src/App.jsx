// src/App.jsx
import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from "react-router-dom";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Events from "./pages/Events";

const API_URL = "http://localhost:8080";

function RequireAuth({ children }) {
  const [ok, setOk] = useState(null);
  useEffect(() => {
    fetch(`${API_URL}/auth/me`, { credentials: "include" }).then(r => setOk(r.ok)).catch(() => setOk(false));
  }, []);
  if (ok === null) return null;
  return ok ? children : <Navigate to="/login" replace />;
}

export default function App() {
  const [user, setUser] = useState(null);
  useEffect(() => {
    fetch(`${API_URL}/auth/me`, { credentials: "include" })
      .then(async r => (r.ok ? setUser((await r.json()).user) : null))
      .catch(() => {});
  }, []);
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login onLogin={setUser} />} />
        <Route
          path="/events"
          element={
            <RequireAuth>
              <Events user={user} />
            </RequireAuth>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}