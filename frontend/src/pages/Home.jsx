// src/pages/Home.jsx
import React, { useState, useEffect } from "react";
import "./Home.css";

const API_URL = "http://localhost:8080";

export default function Home({ user }) {
  const [recommendedTasks, setRecommendedTasks] = useState([]);
  const [trendingEvents, setTrendingEvents] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [communities, setCommunities] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentSlide, setCurrentSlide] = useState(0);

  useEffect(() => {
    fetchHomeData();
  }, []);

  const fetchHomeData = async () => {
    try {
      const [tasksRes, eventsRes, analyticsRes, communitiesRes] = await Promise.all([
        fetch(`${API_URL}/api/home/recommended-tasks`, { credentials: "include" }),
        fetch(`${API_URL}/api/home/trending-events`, { credentials: "include" }),
        fetch(`${API_URL}/api/home/analytics`, { credentials: "include" }),
        fetch(`${API_URL}/api/home/communities`, { credentials: "include" })
      ]);

      const [tasksData, eventsData, analyticsData, communitiesData] = await Promise.all([
        tasksRes.json(),
        eventsRes.json(),
        analyticsRes.json(),
        communitiesRes.json()
      ]);

      setRecommendedTasks(tasksData.tasks);
      setTrendingEvents(eventsData.events);
      setAnalytics(analyticsData);
      setCommunities(communitiesData);
    } catch (error) {
      console.error("Error fetching home data:", error);
    } finally {
      setLoading(false);
    }
  };

  const nextSlide = () => {
    setCurrentSlide((prev) => (prev + 1) % 5);
  };

  const prevSlide = () => {
    setCurrentSlide((prev) => (prev - 1 + 5) % 5);
  };

  if (loading) {
    return (
      <div className="home-loading">
        <div className="loading-spinner"></div>
        <p>Loading your dashboard...</p>
      </div>
    );
  }

  return (
    <div className="home-page">
      {/* Header */}
      <header className="home-header">
        <div className="header-content">
          <h1>Welcome back, {user?.full_name || "Volunteer"}!</h1>
          <p>Ready to make a difference in your community?</p>
          <div className="header-actions">
            <a href="/analytics" className="analytics-link">
              📊 View Company Analytics
            </a>
            <a href="/create-event" className="create-event-link">
              ➕ Create Event
            </a>
          </div>
        </div>
      </header>

      {/* Recommended Tasks Slider */}
      <section className="recommended-section">
        <div className="section-header">
          <h2>Recommended for You</h2>
          <div className="slider-controls">
            <button onClick={prevSlide} className="slider-btn">‹</button>
            <button onClick={nextSlide} className="slider-btn">›</button>
          </div>
        </div>
        
        <div className="slider-container">
          <div className="slider-track" style={{ transform: `translateX(-${currentSlide * 20}%)` }}>
            {Array.from({ length: 5 }, (_, i) => (
              <div key={i} className="slider-item">
                <div className="empty-state">
                  <div className="empty-icon">📋</div>
                  <h3>Task {i + 1}</h3>
                  <p>No recommended tasks yet</p>
                  <span className="coming-soon">Coming Soon</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trending Events Slider */}
      <section className="trending-section">
        <div className="section-header">
          <h2>Trending Events</h2>
          <div className="slider-controls">
            <button onClick={prevSlide} className="slider-btn">‹</button>
            <button onClick={nextSlide} className="slider-btn">›</button>
          </div>
        </div>
        
        <div className="slider-container">
          <div className="slider-track" style={{ transform: `translateX(-${currentSlide * 20}%)` }}>
            {Array.from({ length: 5 }, (_, i) => (
              <div key={i} className="slider-item">
                <div className="empty-state">
                  <div className="empty-icon">🔥</div>
                  <h3>Event {i + 1}</h3>
                  <p>No trending events yet</p>
                  <span className="coming-soon">Coming Soon</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Analytics Dashboard */}
      <section className="analytics-section">
        <h2>Your Analytics Dashboard</h2>
        
        <div className="analytics-grid">
          {/* Registered Events */}
          <div className="analytics-card">
            <h3>Registered Events</h3>
            <div className="metric">
              <div className="metric-value">{analytics?.registered_events?.total || 0}</div>
              <div className="metric-label">Total Events</div>
            </div>
            <div className="metric-row">
              <div className="metric">
                <div className="metric-value">{analytics?.registered_events?.this_month || 0}</div>
                <div className="metric-label">This Month</div>
              </div>
              <div className="metric">
                <div className="metric-value">{analytics?.registered_events?.last_month || 0}</div>
                <div className="metric-label">Last Month</div>
              </div>
            </div>
            <div className="empty-message">No event data available yet</div>
          </div>

          {/* Top Skills */}
          <div className="analytics-card">
            <h3>Top Skills</h3>
            <div className="skills-list">
              {analytics?.top_skills?.length > 0 ? (
                analytics.top_skills.map((skill, index) => (
                  <div key={index} className="skill-item">
                    <span className="skill-rank">#{index + 1}</span>
                    <span className="skill-name">{skill}</span>
                  </div>
                ))
              ) : (
                <div className="empty-message">No skills detected yet</div>
              )}
            </div>
          </div>

          {/* Top Interests */}
          <div className="analytics-card">
            <h3>Top Interests</h3>
            <div className="interests-list">
              {analytics?.top_interests?.length > 0 ? (
                analytics.top_interests.map((interest, index) => (
                  <div key={index} className="interest-item">
                    <span className="interest-rank">#{index + 1}</span>
                    <span className="interest-name">{interest}</span>
                  </div>
                ))
              ) : (
                <div className="empty-message">No interests detected yet</div>
              )}
            </div>
          </div>

          {/* Progress Goal */}
          <div className="analytics-card">
            <h3>Monthly Goal Progress</h3>
            <div className="progress-container">
              <div className="progress-circle">
                <div className="progress-text">
                  {analytics?.progress?.percentage || 0}%
                </div>
              </div>
              <div className="progress-details">
                <div className="progress-current">{analytics?.progress?.current || 0}</div>
                <div className="progress-goal">of {analytics?.progress?.goal || 0} events</div>
              </div>
            </div>
            <div className="empty-message">{analytics?.progress?.message}</div>
          </div>
        </div>
      </section>

      {/* Communities & Leaderboard */}
      <section className="communities-section">
        <h2>Communities & Competition</h2>
        
        <div className="communities-grid">
          {/* Registered Communities */}
          <div className="communities-card">
            <h3>Your Communities</h3>
            <div className="communities-list">
              {communities?.user_communities?.length > 0 ? (
                communities.user_communities.map((community, index) => (
                  <div key={index} className="community-item">
                    <div className="community-name">{community.name}</div>
                    <div className="community-rank">Rank #{community.rank}</div>
                  </div>
                ))
              ) : (
                <div className="empty-message">No communities joined yet</div>
              )}
            </div>
          </div>

          {/* Leaderboard */}
          <div className="leaderboard-card">
            <h3>Community Leaderboard</h3>
            <div className="leaderboard-list">
              {communities?.leaderboard?.length > 0 ? (
                communities.leaderboard.map((community, index) => (
                  <div key={index} className="leaderboard-item">
                    <div className="leaderboard-rank">#{index + 1}</div>
                    <div className="leaderboard-name">{community.name}</div>
                    <div className="leaderboard-score">{community.score} pts</div>
                  </div>
                ))
              ) : (
                <div className="empty-message">No leaderboard data available</div>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}