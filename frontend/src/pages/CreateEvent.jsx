// src/pages/CreateEvent.jsx
import React, { useState } from "react";
import "./CreateEvent.css";

const API_URL = "http://localhost:8080";

export default function CreateEvent() {
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    mode: "in_person",
    location_city: "",
    location_state: "",
    location_lat: "",
    location_lng: "",
    is_remote: false,
    causes: "",
    skills_needed: "",
    accessibility: "",
    tags: "",
    min_duration_min: 60,
    rsvp_url: "",
    contact_email: "",
    sessions: []
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

  const addSession = () => {
    setFormData(prev => ({
      ...prev,
      sessions: [
        ...prev.sessions,
        { start_ts: "", end_ts: "", capacity: "", meet_url: "", address_line: "" }
      ]
    }));
  };

  const removeSession = (index) => {
    setFormData(prev => ({
      ...prev,
      sessions: prev.sessions.filter((_, i) => i !== index)
    }));
  };

  const updateSession = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      sessions: prev.sessions.map((s, i) => (i === index ? { ...s, [field]: value } : s))
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");

      try {
        const submitData = {
          ...formData,
          location_lat: formData.location_lat ? parseFloat(formData.location_lat) : null,
          location_lng: formData.location_lng ? parseFloat(formData.location_lng) : null,
          causes: formData.causes.split(",").map(x => x.trim()).filter(Boolean),
          skills_needed: formData.skills_needed.split(",").map(x => x.trim()).filter(Boolean),
          accessibility: formData.accessibility.split(",").map(x => x.trim()).filter(Boolean),
          tags: formData.tags.split(",").map(x => x.trim()).filter(Boolean)
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
          location_lat: "",
          location_lng: "",
          is_remote: false,
          causes: "",
          skills_needed: "",
          accessibility: "",
          tags: "",
          min_duration_min: 60,
          rsvp_url: "",
          contact_email: "",
          sessions: []
        });
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

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="location_lat">Latitude</label>
                <input
                  type="number"
                  step="any"
                  id="location_lat"
                  name="location_lat"
                  value={formData.location_lat}
                  onChange={handleInputChange}
                  placeholder="40.7128"
                />
              </div>
              <div className="form-group">
                <label htmlFor="location_lng">Longitude</label>
                <input
                  type="number"
                  step="any"
                  id="location_lng"
                  name="location_lng"
                  value={formData.location_lng}
                  onChange={handleInputChange}
                  placeholder="-74.0060"
                />
              </div>
            </div>

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  name="is_remote"
                  checked={formData.is_remote}
                  onChange={handleInputChange}
                />
                Remote-friendly event
              </label>
            </div>
          </div>

          {/* Event Details */}
          <div className="form-section">
            <h2>Event Details</h2>

            <div className="form-group">
              <label htmlFor="causes">Causes (comma-separated)</label>
              <input
                type="text"
                id="causes"
                name="causes"
                value={formData.causes}
                onChange={handleInputChange}
                placeholder="hunger, education, environment, community"
              />
            </div>

            <div className="form-group">
              <label htmlFor="skills_needed">Skills Needed (comma-separated)</label>
              <input
                type="text"
                id="skills_needed"
                name="skills_needed"
                value={formData.skills_needed}
                onChange={handleInputChange}
                placeholder="logistics, communication, teaching, technology"
              />
            </div>

            <div className="form-group">
              <label htmlFor="accessibility">Accessibility Features (comma-separated)</label>
              <input
                type="text"
                id="accessibility"
                name="accessibility"
                value={formData.accessibility}
                onChange={handleInputChange}
                placeholder="wheelchair accessible, sign language interpreter"
              />
            </div>

            <div className="form-group">
              <label htmlFor="tags">Tags (comma-separated)</label>
              <input
                type="text"
                id="tags"
                name="tags"
                value={formData.tags}
                onChange={handleInputChange}
                placeholder="weekend, family-friendly, outdoor"
              />
            </div>

            <div className="form-group">
              <label htmlFor="min_duration_min">Minimum Duration (minutes)</label>
              <input
                type="number"
                id="min_duration_min"
                name="min_duration_min"
                value={formData.min_duration_min}
                onChange={handleInputChange}
                min="15"
              />
            </div>

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

          {/* Event Sessions */}
          <div className="form-section">
            <h2>Event Sessions (Optional)</h2>
            <p>Add specific time slots for your event</p>

            {formData.sessions.map((session, index) => (
              <div key={index} className="session-card">
                <h3>Session {index + 1}</h3>
                <div className="form-row">
                  <div className="form-group">
                    <label>Start Time</label>
                    <input
                      type="datetime-local"
                      value={session.start_ts}
                      onChange={(e) => updateSession(index, "start_ts", e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label>End Time</label>
                    <input
                      type="datetime-local"
                      value={session.end_ts}
                      onChange={(e) => updateSession(index, "end_ts", e.target.value)}
                    />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Capacity</label>
                    <input
                      type="number"
                      value={session.capacity}
                      onChange={(e) => updateSession(index, "capacity", e.target.value)}
                      placeholder="Maximum participants"
                    />
                  </div>
                  <div className="form-group">
                    <label>Meeting URL (for virtual)</label>
                    <input
                      type="url"
                      value={session.meet_url}
                      onChange={(e) => updateSession(index, "meet_url", e.target.value)}
                      placeholder="https://meet.example.com/room"
                    />
                  </div>
                </div>
                <div className="form-group">
                  <label>Address</label>
                  <input
                    type="text"
                    value={session.address_line}
                    onChange={(e) => updateSession(index, "address_line", e.target.value)}
                    placeholder="123 Main St, City, State"
                  />
                </div>
                <button type="button" onClick={() => removeSession(index)} className="remove-session-btn">
                  Remove Session
                </button>
              </div>
            ))}

            <button type="button" onClick={addSession} className="add-session-btn">
              + Add Session
            </button>
          </div>

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