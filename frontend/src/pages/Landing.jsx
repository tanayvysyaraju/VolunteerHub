// src/pages/Landing.jsx
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./Landing.css";

export default function Landing() {
  const navigate = useNavigate();
  const [isSignUp, setIsSignUp] = useState(false);
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    fullName: "",
    dept: "",
    position: "",
    erg: ""
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [wantsSlackScan, setWantsSlackScan] = useState(false);
  const [departments, setDepartments] = useState([]);

  const API_URL = "http://localhost:8080";

  useEffect(() => {
    // Fetch departments to populate the dropdown
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/departments`, {
          credentials: "include"
        });
        const data = await res.json().catch(() => ({}));
        setDepartments(Array.isArray(data.departments) ? data.departments : []);
      } catch (e) {
        setDepartments([]);
      }
    })();
  }, []);

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
        // Minimal signup payload
        body = {
          email: formData.email,
          password: formData.password,
          full_name: formData.fullName,
          dept: formData.dept,
          position: formData.position,
          erg: formData.erg
        };
        // Optionally append suggested skills from Slack import
        if (wantsSlackScan) {
          try {
            const sres = await fetch(`${API_URL}/api/skills/suggest`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              credentials: "include",
              body: JSON.stringify({ slack_source: "latest" })
            });
            const sdata = await sres.json().catch(() => ({}));
            if (Array.isArray(sdata.suggested_skills) && sdata.suggested_skills.length) {
              body.skills = sdata.suggested_skills;
            }
          } catch (_) {}
        }
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
      
      // Redirect to home page after successful login/signup
      navigate("/home", { replace: true });
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
            <div className="logo-icon">🤝</div>
            <h2>VolunteerHub</h2>
          </div>
          <div className="nav-buttons">
            <button 
              className={`nav-btn ${!isSignUp ? 'active' : ''}`}
              onClick={() => setIsSignUp(false)}
            >
              <span className="nav-icon">↪</span>
              <span>Sign In</span>
            </button>
            <button 
              className={`nav-btn ${isSignUp ? 'active' : ''}`}
              onClick={() => setIsSignUp(true)}
            >
              <span className="nav-icon">+</span>
              <span>Sign Up</span>
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="hero-section">
        <div className="hero-content">
          <div className="hero-text">
            <h1 className="hero-title">
              Connect. Volunteer. <span className="highlight">Impact.</span>
            </h1>
            <p className="hero-subtitle">
              Join a community of volunteers making a difference. 
              Discover opportunities that matter to you and create lasting change.
            </p>
            <div className="hero-stats">
              <div className="stat">
                <div className="stat-number">500+</div>
                <div className="stat-label">Active Volunteers</div>
              </div>
              <div className="stat">
                <div className="stat-number">1,200+</div>
                <div className="stat-label">Hours Contributed</div>
              </div>
              <div className="stat">
                <div className="stat-number">50+</div>
                <div className="stat-label">Communities Served</div>
              </div>
            </div>
          </div>
          
          {/* Auth Form */}
          <div className="auth-form-container">
            <div className="form-header">
              <h3>{isSignUp ? 'Create Account' : 'Welcome Back'}</h3>
              <p className="form-subtitle">
                {isSignUp ? 'Join our community today' : 'Sign in to continue your journey'}
              </p>
            </div>
            
            <form onSubmit={handleSubmit} className="auth-form">
              
              {isSignUp && (
                <>
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">Full Name</label>
                      <input
                        type="text"
                        name="fullName"
                        placeholder="Enter your full name"
                        value={formData.fullName}
                        onChange={handleInputChange}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Position</label>
                      <input
                        type="text"
                        name="position"
                        placeholder="Your job title"
                        value={formData.position}
                        onChange={handleInputChange}
                      />
                    </div>
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">Department</label>
                      <select
                        name="dept"
                        value={formData.dept}
                        onChange={handleInputChange}
                        required
                      >
                        <option value="">Select Department</option>
                        {departments.map((d) => (
                          <option key={d.id} value={d.name}>
                            {d.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">Employee Resource Group</label>
                      <select
                        name="erg"
                        value={formData.erg}
                        onChange={handleInputChange}
                      >
                        <option value="">Select ERG (Optional)</option>
                        <option value="Women in Leadership / Women@">Women in Leadership / Women@</option>
                        <option value="Black Employee Network / Black Professionals ERG">Black Employee Network / Black Professionals ERG</option>
                        <option value="Latinx / Hispanic Heritage Network">Latinx / Hispanic Heritage Network</option>
                        <option value="Asian Pacific Islander Network">Asian Pacific Islander Network</option>
                        <option value="South Asian Professionals Network">South Asian Professionals Network</option>
                        <option value="LGBTQ+ Pride Network">LGBTQ+ Pride Network</option>
                        <option value="Veterans & Military Families Network">Veterans & Military Families Network</option>
                        <option value="Disability & Neurodiversity Alliance">Disability & Neurodiversity Alliance</option>
                        <option value="Parents & Caregivers ERG">Parents & Caregivers ERG</option>
                        <option value="Young Professionals / NextGen ERG">Young Professionals / NextGen ERG</option>
                        <option value="Multifaith / Interfaith Network">Multifaith / Interfaith Network</option>
                        <option value="Mental Health & Wellness Network">Mental Health & Wellness Network</option>
                        <option value="Environmental & Sustainability Group (Green Team)">Environmental & Sustainability Group (Green Team)</option>
                        <option value="International Employees Network / Global Cultures ERG">International Employees Network / Global Cultures ERG</option>
                        <option value="Native & Indigenous Peoples Network">Native & Indigenous Peoples Network</option>
                        <option value="African Diaspora Network">African Diaspora Network</option>
                        <option value="Middle Eastern & North African (MENA) ERG">Middle Eastern & North African (MENA) ERG</option>
                        <option value="Men as Allies / Gender Equity Advocates">Men as Allies / Gender Equity Advocates</option>
                        <option value="Volunteers & Community Impact Network">Volunteers & Community Impact Network</option>
                        <option value="Multicultural / Diversity & Inclusion Council">Multicultural / Diversity & Inclusion Council</option>
                      </select>
                    </div>
                  </div>

                  <div className="form-group checkbox-group">
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={wantsSlackScan}
                        onChange={(e) => setWantsSlackScan(e.target.checked)}
                      />
                      <span className="checkbox-custom"></span>
                      <span className="checkbox-text">Analyze recent Slack chats to suggest top 3 skills</span>
                    </label>
                  </div>
                </>
              )}
              
              <div className="form-group">
                <label className="form-label">Email Address</label>
                <input
                  type="email"
                  name="email"
                  placeholder="Enter your email"
                  value={formData.email}
                  onChange={handleInputChange}
                  required
                />
              </div>
              
              <div className="form-group">
                <label className="form-label">Password</label>
                <input
                  type="password"
                  name="password"
                  placeholder="Enter your password"
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
                <span className="btn-icon">
                  {isLoading ? '⏳' : (isSignUp ? '+' : '↪')}
                </span>
                <span>{isLoading ? 'Please wait...' : (isSignUp ? 'Create Account' : 'Sign In')}</span>
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
                        dept: "",
                        position: "",
                        erg: ""
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
