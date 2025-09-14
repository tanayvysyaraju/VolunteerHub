// src/pages/Home.jsx
import React, { useState, useEffect } from "react";
import "./Home.css";

const API_URL = "http://localhost:8080";

export default function Home({ user: propUser }) {
  const [user, setUser] = useState(propUser);
  const [recommendedTasks, setRecommendedTasks] = useState([]);
  const [trendingEvents, setTrendingEvents] = useState([]);
  const [registeredTasks, setRegisteredTasks] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [communities, setCommunities] = useState(null);
  const [loading, setLoading] = useState(true);
  const [recSlide, setRecSlide] = useState(0);
  const [trendSlide, setTrendSlide] = useState(0);
  const [regSlide, setRegSlide] = useState(0);
  const regCount = registeredTasks.length;

  // Debug: Log user data
  console.log("Home component - user data:", user);

  useEffect(() => {
    // If no user prop, fetch user data directly
    if (!user) {
      fetch(`${API_URL}/auth/me`, { credentials: "include" })
        .then(async r => {
          if (r.ok) {
            const data = await r.json();
            setUser(data.user);
          }
        })
        .catch(console.error);
    }
  }, [propUser]);

  useEffect(() => {
    fetchHomeData();
  }, []);

  const fetchHomeData = async () => {
    try {
      const [tasksRes, trendingRes, regRes, analyticsRes, communitiesRes] = await Promise.all([
        fetch(`${API_URL}/api/tasks/recommended?use_gemini=true`, { credentials: "include" }),
        fetch(`${API_URL}/api/home/trending-events`, { credentials: "include" }),
        fetch(`${API_URL}/api/tasks/registered`, { credentials: "include" }),
        fetch(`${API_URL}/api/home/analytics`, { credentials: "include" }),
        fetch(`${API_URL}/api/home/communities`, { credentials: "include" })
      ]);

      const [tasksData, trendingData, regData, analyticsData, communitiesData] = await Promise.all([
        tasksRes.json(),
        trendingRes.json(),
        regRes.json(),
        analyticsRes.json(),
        communitiesRes.json()
      ]);

      setRecommendedTasks(tasksData.tasks);
      setTrendingEvents(trendingData.events || []);
      setRegisteredTasks(regData.tasks || []);
      setAnalytics(analyticsData);
      setCommunities(communitiesData);
    } catch (error) {
      console.error("Error fetching home data:", error);
    } finally {
      setLoading(false);
    }
  };

  const nextRec = () => setRecSlide((p) => (p + 1) % 5);
  const prevRec = () => setRecSlide((p) => (p - 1 + 5) % 5);
  const nextTrend = () => setTrendSlide((p) => (p + 1) % 5);
  const prevTrend = () => setTrendSlide((p) => (p - 1 + 5) % 5);
  const nextReg = (len) => setRegSlide((p) => (len ? (p + 1) % len : 0));
  const prevReg = (len) => setRegSlide((p) => (len ? (p - 1 + len) % len : 0));

  if (loading) {
    return (
      <div className="home-loading">
        <div className="loading-spinner"></div>
        <p>Loading your dashboard...</p>
      </div>
    );
  }

  const handleSignOut = async () => {
    try {
      await fetch(`${API_URL}/auth/logout`, { method: 'POST', credentials: 'include' });
    } catch (_) {}
    window.location.href = '/';
  };

  return (
    <div className="home-page">
      {/* Top Navigation */}
      <div className="top-nav">
        <div className="nav-left">
          <a href="/home" className="nav-btn home-btn">
            <span className="nav-icon">⌂</span>
            <span>Home</span>
          </a>
          <button onClick={handleSignOut} className="nav-btn signout-btn">
            <span className="nav-icon">↪</span>
            <span>Sign Out</span>
          </button>
        </div>
        <div className="nav-right">
          <a href="/analytics" className="nav-btn analytics-btn">
            <span className="nav-icon">📊</span>
            <span>Analytics</span>
          </a>
          <a href="/create-event" className="nav-btn create-btn">
            <span className="nav-icon">+</span>
            <span>Create Event</span>
          </a>
        </div>
      </div>

      {/* Header */}
      <header className="home-header">
        <div className="header-content">
          <h1>Welcome back, {user?.full_name || "Loading..."}!</h1>
          <p>Ready to make a difference in your community?</p>
        </div>
      </header>

      {/* Recommended Tasks Slider */}
      <section className="recommended-section">
        <div className="section-header">
          <h2>Recommended for You</h2>
          <div className="slider-controls">
            <button onClick={prevRec} className="slider-btn">‹</button>
            <button onClick={nextRec} className="slider-btn">›</button>
          </div>
        </div>
        
        <div className="slider-container">
          <div className="slider-track" style={{ transform: `translateX(-${recSlide * 20}%)` }}>
            {Array.from({ length: 5 }, (_, i) => {
              const t = recommendedTasks[i];
              return (
                <div key={i} className="slider-item">
                  {t ? (
                    <div className="task-card">
                      <div className="task-card-header">
                        <h3 className="task-title">{t.title}</h3>
                        <span className="reg-badge">{t.registered_count ?? 0}</span>
                      </div>
                      <p className="task-desc">{t.description || ""}</p>
                      <div className="task-time">
                        {t.start_ts && <span>Start: {new Date(t.start_ts).toLocaleString()}</span>}
                        {t.end_ts && <span> · End: {new Date(t.end_ts).toLocaleString()}</span>}
                      </div>
                      <div className="task-meta">
                        {(t.skills_required || []).slice(0,3).map((s, idx) => (
                          <span key={idx} className="skill-chip">{s}</span>
                        ))}
                      </div>
                      <div className="task-actions">
                        <button
                          className="register-btn"
                          onClick={async () => {
                            try {
                              const res = await fetch(`${API_URL}/api/tasks/${t.id}/register`, { method: 'POST', credentials: 'include' });
                              const data = await res.json();
                              if (res.ok) {
                                fetchHomeData();
                              } else {
                                console.error(data);
                              }
                            } catch (e) {
                              console.error(e);
                            }
                          }}
                        >Register</button>
                      </div>
                    </div>
                  ) : (
                    <div className="empty-state">
                      <div className="empty-icon">📋</div>
                      <h3>Task {i + 1}</h3>
                      <p>No recommended tasks yet</p>
                      <span className="coming-soon">Coming Soon</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Events Slider */}
      <section className="trending-section">
        <div className="section-header">
          <h2>Trending</h2>
          <div className="slider-controls">
            <button onClick={prevTrend} className="slider-btn">‹</button>
            <button onClick={nextTrend} className="slider-btn">›</button>
          </div>
        </div>
        
        <div className="slider-container">
          <div className="slider-track" style={{ transform: `translateX(-${trendSlide * 20}%)` }}>
            {Array.from({ length: 5 }, (_, i) => {
              const e = trendingEvents[i];
              return (
                <div key={i} className="slider-item">
                  {e ? (
                    <div className="task-card">
                      <div className="task-card-header">
                        <h3 className="task-title">{e.title}</h3>
                        <span className="reg-badge">{e.total_registered_count ?? 0}</span>
                      </div>
                      <p className="task-desc">{e.description || ''}</p>
                      <div className="task-time">
                        {e.event_start_ts && <span>Start: {new Date(e.event_start_ts).toLocaleString()}</span>}
                        {e.event_end_ts && <span> · End: {new Date(e.event_end_ts).toLocaleString()}</span>}
                      </div>
                      <div className="task-meta">
                        {e.mode && <span className="priority-chip">{e.mode}</span>}
                        {(e.event_skills || []).slice(0,3).map((s, idx) => (
                          <span key={idx} className="skill-chip">{s}</span>
                        ))}
                      </div>
                      <div className="task-actions">
                        <a className="register-btn register-btn--sm" href={e.rsvp_url || '#'} target="_blank" rel="noreferrer">
                          {e.user_registered ? 'Registered' : 'Register'}
                        </a>
                      </div>
                    </div>
                  ) : (
                    <div className="empty-state">
                      <div className="empty-icon">🔥</div>
                      <h3>Event {i + 1}</h3>
                      <p>No events yet</p>
                      <span className="coming-soon">Coming Soon</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Registered Events/Tasks */}
      <section className="registered-section">
        <div className="section-header">
          <h2>Registered Events</h2>
          <div className="slider-controls">
            <button onClick={() => prevReg(registeredTasks.length)} className="slider-btn">‹</button>
            <button onClick={() => nextReg(registeredTasks.length)} className="slider-btn">›</button>
          </div>
        </div>
        <div className="panel-container">
          {registeredTasks.length === 0 ? (
            <div className="empty-message">You haven’t registered for any tasks yet.</div>
          ) : (
            <div className="slider-container">
              <div className="slider-track" style={{ width: `${regCount * 100}%`, transform: `translateX(-${regCount ? (regSlide * 100) / regCount : 0}%)` }}>
                {registeredTasks.map((t, i) => (
                  <div key={t.id} className="slider-item" style={{ width: `${regCount ? 100 / regCount : 100}%` }}>
                    <div className="task-card">
                      <div className="task-card-header">
                        <h3 className="task-title">{t.title}</h3>
                        <span className="reg-badge">{t.registered_count ?? 0}</span>
                      </div>
                      <p className="task-desc">{t.description || ''}</p>
                      <div className="task-time">
                        {t.start_ts && <span>Start: {new Date(t.start_ts).toLocaleString()}</span>}
                        {t.end_ts && <span> · End: {new Date(t.end_ts).toLocaleString()}</span>}
                      </div>
                      <div className="task-meta">
                        {(t.skills_required || []).slice(0,3).map((s, idx) => (
                          <span key={idx} className="skill-chip">{s}</span>
                        ))}
                        {t.mode && <span className="priority-chip">{t.mode}</span>}
                      </div>
                      <div className="task-actions">
                        <button
                          className="register-btn registered"
                          onClick={async () => {
                            try {
                              const res = await fetch(`${API_URL}/api/tasks/${t.id}/register`, { method: 'DELETE', credentials: 'include' });
                              await res.json();
                              // Reset slide if needed then refresh
                              setRegSlide((s) => (s >= registeredTasks.length - 1 ? 0 : s));
                              fetchHomeData();
                            } catch (e) {
                              console.error(e);
                            }
                          }}
                        >Unregister</button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
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
            {registeredTasks.length > 0 ? (
              <div className="registered-names">
                <div className="list-title">Your Registered Events</div>
                <ul>
                  {(analytics?.registered_events?.names || []).map((name, idx) => (
                    <li key={idx} className="registered-name">{name}</li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="empty-message">No event data available yet</div>
            )}
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
              <div
                className="progress-circle"
                style={{
                  background: `conic-gradient(#10b981 ${(analytics?.progress?.percentage || 0) * 3.6}deg, #e5e7eb 0deg)`
                }}
              >
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
                    <div className="community-cta">Register for 3 more events to rank up!</div>
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