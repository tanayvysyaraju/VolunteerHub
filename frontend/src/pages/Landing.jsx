// src/pages/Landing.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Landing.css";

export default function Landing() {
  const navigate = useNavigate();
  const [isSignUp, setIsSignUp] = useState(false);
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    fullName: "",
    organizationId: null,
    userName: "",
    company: "",
    position: "",
    dept: "",
    locationCity: "",
    locationState: "",
    tz: "UTC",
    strengths: "",
    interests: "",
    expertise: "",
    communicationStyle: ""
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const API_URL = "http://localhost:8080";

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const endpoint = isSignUp ? "/auth/signup" : "/auth/login";
      let body;
      
      if (isSignUp) {
        // Map frontend field names to backend field names
        body = {
          email: formData.email,
          password: formData.password,
          full_name: formData.fullName,
          organization_id: formData.organizationId,
          user_name: formData.userName,
          company: formData.company,
          position: formData.position,
          dept: formData.dept,
          location_city: formData.locationCity,
          location_state: formData.locationState,
          tz: formData.tz,
          strengths: formData.strengths,
          interests: formData.interests,
          expertise: formData.expertise,
          communication_style: formData.communicationStyle
        };
      } else {
        body = { email: formData.email, password: formData.password };
      }
      
      const res = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      
      const data = await res.json().catch(() => ({}));
      
      if (!res.ok) {
        const errorMessage = data.error || `${isSignUp ? 'Signup' : 'Login'} failed`;
        
        // Handle specific redirect cases
        if (errorMessage.includes("email already registered")) {
          setError("Account already exists. Please log in instead.");
          setTimeout(() => setIsSignUp(false), 2000);
        } else if (errorMessage.includes("invalid credentials")) {
          setError("Account not found. Please sign up first.");
          setTimeout(() => setIsSignUp(true), 2000);
        } else {
          setError(errorMessage);
        }
        return;
      }
      
      // Redirect to events page after successful login/signup
      navigate("/events", { replace: true });
    } catch (err) {
      setError("Network error. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="landing-page">
      {/* Navigation */}
      <nav className="navbar">
        <div className="nav-container">
          <div className="nav-logo">
            <h2>VolunteerHub</h2>
          </div>
          <div className="nav-buttons">
            <button 
              className={`nav-btn ${!isSignUp ? 'active' : ''}`}
              onClick={() => setIsSignUp(false)}
            >
              Login
            </button>
            <button 
              className={`nav-btn ${isSignUp ? 'active' : ''}`}
              onClick={() => setIsSignUp(true)}
            >
              Sign Up
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="hero-section">
        <div className="hero-content">
          <h1 className="hero-title">
            Connect. Volunteer. Impact.
          </h1>
          <p className="hero-subtitle">
            Join a community of volunteers making a difference. 
            Discover opportunities that matter to you and create lasting change.
          </p>
          
          {/* Auth Form */}
          <div className="auth-form-container">
            <form onSubmit={handleSubmit} className="auth-form">
              <h3>{isSignUp ? 'Create Account' : 'Welcome Back'}</h3>
              
              {isSignUp && (
                <>
                  <div className="form-group">
                    <input
                      type="text"
                      name="fullName"
                      placeholder="Full Name"
                      value={formData.fullName}
                      onChange={handleInputChange}
                      required
                    />
                  </div>
                  
                  <div className="form-group">
                    <input
                      type="text"
                      name="userName"
                      placeholder="Username"
                      value={formData.userName}
                      onChange={handleInputChange}
                    />
                  </div>
                  
                  <div className="form-group">
                    <input
                      type="text"
                      name="company"
                      placeholder="Company"
                      value={formData.company}
                      onChange={handleInputChange}
                    />
                  </div>
                  
                  <div className="form-group">
                    <input
                      type="text"
                      name="position"
                      placeholder="Position/Title"
                      value={formData.position}
                      onChange={handleInputChange}
                    />
                  </div>
                  
                  <div className="form-group">
                    <input
                      type="text"
                      name="dept"
                      placeholder="Department"
                      value={formData.dept}
                      onChange={handleInputChange}
                    />
                  </div>
                  
                  <div className="form-row">
                    <div className="form-group">
                      <input
                        type="text"
                        name="locationCity"
                        placeholder="City"
                        value={formData.locationCity}
                        onChange={handleInputChange}
                      />
                    </div>
                    <div className="form-group">
                      <input
                        type="text"
                        name="locationState"
                        placeholder="State"
                        value={formData.locationState}
                        onChange={handleInputChange}
                      />
                    </div>
                  </div>
                  
                  <div className="form-group">
                    <input
                      type="text"
                      name="strengths"
                      placeholder="Strengths (comma-separated)"
                      value={formData.strengths}
                      onChange={handleInputChange}
                    />
                  </div>
                  
                  <div className="form-group">
                    <input
                      type="text"
                      name="interests"
                      placeholder="Interests (comma-separated)"
                      value={formData.interests}
                      onChange={handleInputChange}
                    />
                  </div>
                  
                  <div className="form-group">
                    <input
                      type="text"
                      name="expertise"
                      placeholder="Areas of Expertise (comma-separated)"
                      value={formData.expertise}
                      onChange={handleInputChange}
                    />
                  </div>
                  
                  <div className="form-group">
                    <input
                      type="text"
                      name="communicationStyle"
                      placeholder="Communication Style"
                      value={formData.communicationStyle}
                      onChange={handleInputChange}
                    />
                  </div>
                </>
              )}
              
              <div className="form-group">
                <input
                  type="email"
                  name="email"
                  placeholder="Email Address"
                  value={formData.email}
                  onChange={handleInputChange}
                  required
                />
              </div>
              
              <div className="form-group">
                <input
                  type="password"
                  name="password"
                  placeholder="Password"
                  value={formData.password}
                  onChange={handleInputChange}
                  required
                />
              </div>
              
              {error && <div className="error-message">{error}</div>}
              
              <button 
                type="submit" 
                className="submit-btn"
                disabled={isLoading}
              >
                {isLoading ? 'Please wait...' : (isSignUp ? 'Create Account' : 'Sign In')}
              </button>
              
              <div className="form-footer">
                <p>
                  {isSignUp ? "Already have an account?" : "Don't have an account?"}
                  <button 
                    type="button"
                    className="link-btn"
                    onClick={() => {
                      setIsSignUp(!isSignUp);
                      setError("");
                      setFormData({
                        email: "",
                        password: "",
                        fullName: "",
                        organizationId: null,
                        userName: "",
                        company: "",
                        position: "",
                        dept: "",
                        locationCity: "",
                        locationState: "",
                        tz: "UTC",
                        strengths: "",
                        interests: "",
                        expertise: "",
                        communicationStyle: ""
                      });
                    }}
                  >
                    {isSignUp ? "Sign In" : "Sign Up"}
                  </button>
                </p>
              </div>
            </form>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="features-section">
        <div className="features-container">
          <h2>Why Choose VolunteerHub?</h2>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">🎯</div>
              <h3>Find Your Passion</h3>
              <p>Discover volunteer opportunities that align with your interests and skills.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🤝</div>
              <h3>Connect & Collaborate</h3>
              <p>Join a community of like-minded volunteers and make lasting connections.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">📈</div>
              <h3>Track Your Impact</h3>
              <p>Monitor your volunteer hours and see the positive change you're creating.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
