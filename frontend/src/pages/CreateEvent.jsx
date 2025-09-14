// src/pages/CreateEvent.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./CreateEvent.css";

const API_URL = "http://localhost:8080";

export default function CreateEvent() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    mode: "in_person",
    location_city: "",
    location_state: "",
    rsvp_url: "",
    contact_email: ""
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value
    }));
  };

  // sessions removed

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");

      try {
        const submitData = {
          title: formData.title,
          description: formData.description,
          mode: formData.mode,
          location_city: formData.location_city,
          location_state: formData.location_state,
          rsvp_url: formData.rsvp_url,
          contact_email: formData.contact_email
        };

      const res = await fetch(`${API_URL}/api/events`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(submitData)
      });

      const data = await res.json();

      if (!res.ok) throw new Error(data.error || "Failed to create event");

        setSuccess("Event created successfully!");
        setFormData({
          title: "",
          description: "",
          mode: "in_person",
          location_city: "",
          location_state: "",
          rsvp_url: "",
          contact_email: ""
        });

        // Reroute to dashboard/home after successful creation
        navigate("/home", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="create-event">
      <div className="event-container">
        <header className="event-header">
          <h1>Create New Event</h1>
          <p>Set up a volunteer event</p>
        </header>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}

        <form onSubmit={handleSubmit} className="event-form">
          {/* Basic Information */}
          <div className="form-section">
            <h2>Basic Information</h2>

            <div className="form-group">
              <label htmlFor="title">Event Title *</label>
              <input
                type="text"
                id="title"
                name="title"
                value={formData.title}
                onChange={handleInputChange}
                required
                placeholder="Enter event title"
              />
            </div>

            <div className="form-group">
              <label htmlFor="description">Description *</label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                required
                rows="4"
                placeholder="Describe the event and its purpose"
              />
            </div>

            <div className="form-group">
              <label htmlFor="mode">Event Mode *</label>
              <select
                id="mode"
                name="mode"
                value={formData.mode}
                onChange={handleInputChange}
                required
              >
                <option value="in_person">In Person</option>
                <option value="virtual">Virtual</option>
                <option value="hybrid">Hybrid</option>
              </select>
            </div>
          </div>

          {/* Location Information */}
          <div className="form-section">
            <h2>Location Information</h2>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="location_city">City</label>
                <input
                  type="text"
                  id="location_city"
                  name="location_city"
                  value={formData.location_city}
                  onChange={handleInputChange}
                  placeholder="City"
                />
              </div>
              <div className="form-group">
                <label htmlFor="location_state">State</label>
                <input
                  type="text"
                  id="location_state"
                  name="location_state"
                  value={formData.location_state}
                  onChange={handleInputChange}
                  placeholder="State"
                />
              </div>
            </div>

            {/* removed lat/lng and remote */}
          </div>

          {/* Event Details (minimal) */}
          <div className="form-section">
            <h2>Event Details</h2>
            <div className="form-group">
              <label htmlFor="rsvp_url">RSVP URL</label>
              <input
                type="url"
                id="rsvp_url"
                name="rsvp_url"
                value={formData.rsvp_url}
                onChange={handleInputChange}
                placeholder="https://example.com/rsvp"
              />
            </div>
            <div className="form-group">
              <label htmlFor="contact_email">Contact Email</label>
              <input
                type="email"
                id="contact_email"
                name="contact_email"
                value={formData.contact_email}
                onChange={handleInputChange}
                placeholder="contact@example.com"
              />
            </div>
          </div>

          {/* Sessions removed */}

          {/* Submit */}
          <div className="form-actions">
            <button type="submit" disabled={loading} className="submit-btn">
              {loading ? "Creating Event..." : "Create Event"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}