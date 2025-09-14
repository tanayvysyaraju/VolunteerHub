// src/pages/CompanyAnalytics.jsx
import React, { useState, useEffect } from "react";
import "./CompanyAnalytics.css";

const API_URL = "http://localhost:8080";

export default function CompanyAnalytics({ user }) {
  const [overview, setOverview] = useState(null);
  const [engagement, setEngagement] = useState(null);
  const [impact, setImpact] = useState(null);
  const [progress, setProgress] = useState(null);
  const [leaderboard, setLeaderboard] = useState(null);
  const [trends, setTrends] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    fetchCompanyData();
  }, []);

  const fetchCompanyData = async () => {
    try {
      const [overviewRes, engagementRes, impactRes, progressRes, leaderboardRes, trendsRes] = await Promise.all([
        fetch(`${API_URL}/api/company/overview`, { credentials: "include" }),
        fetch(`${API_URL}/api/company/engagement`, { credentials: "include" }),
        fetch(`${API_URL}/api/company/impact`, { credentials: "include" }),
        fetch(`${API_URL}/api/company/progress`, { credentials: "include" }),
        fetch(`${API_URL}/api/company/leaderboard`, { credentials: "include" }),
        fetch(`${API_URL}/api/company/trends`, { credentials: "include" })
      ]);

      const [overviewData, engagementData, impactData, progressData, leaderboardData, trendsData] = await Promise.all([
        overviewRes.json(),
        engagementRes.json(),
        impactRes.json(),
        progressRes.json(),
        leaderboardRes.json(),
        trendsRes.json()
      ]);

      setOverview(overviewData);
      setEngagement(engagementData);
      setImpact(impactData);
      setProgress(progressData);
      setLeaderboard(leaderboardData);
      setTrends(trendsData);
    } catch (error) {
      console.error("Error fetching company data:", error);
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "engagement", label: "Engagement", icon: "👥" },
    { id: "impact", label: "Impact", icon: "🌍" },
    { id: "progress", label: "Progress", icon: "📈" },
    { id: "leaderboard", label: "Leaderboard", icon: "🏆" },
    { id: "trends", label: "Trends", icon: "📉" }
  ];

  if (loading) {
    return (
      <div className="analytics-loading">
        <div className="loading-spinner"></div>
        <p>Loading company analytics...</p>
      </div>
    );
  }

  return (
    <div className="company-analytics">
      {/* Header */}
      <header className="analytics-header">
        <div className="header-content">
          <h1>Company Analytics Dashboard</h1>
          <p>Comprehensive insights into volunteer engagement and impact</p>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="analytics-nav">
        <div className="nav-container">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className="tab-icon">{tab.icon}</span>
              <span className="tab-label">{tab.label}</span>
            </button>
          ))}
        </div>
      </nav>

      {/* Tab Content */}
      <div className="analytics-content">
        {activeTab === "overview" && <OverviewTab data={overview} />}
        {activeTab === "engagement" && <EngagementTab data={engagement} />}
        {activeTab === "impact" && <ImpactTab data={impact} />}
        {activeTab === "progress" && <ProgressTab data={progress} />}
        {activeTab === "leaderboard" && <LeaderboardTab data={leaderboard} />}
        {activeTab === "trends" && <TrendsTab data={trends} />}
      </div>
    </div>
  );
}

// Overview Tab Component
function OverviewTab({ data }) {
  return (
    <div className="tab-content">
      <div className="metrics-grid">
        <div className="metric-card primary">
          <div className="metric-icon">👥</div>
          <div className="metric-content">
            <div className="metric-value">{data?.total_employees || 0}</div>
            <div className="metric-label">Total Employees</div>
          </div>
        </div>
        
        <div className="metric-card success">
          <div className="metric-icon">🎯</div>
          <div className="metric-content">
            <div className="metric-value">{data?.active_volunteers || 0}</div>
            <div className="metric-label">Active Volunteers</div>
          </div>
        </div>
        
        <div className="metric-card info">
          <div className="metric-icon">📊</div>
          <div className="metric-content">
            <div className="metric-value">{data?.participation_rate || 0}%</div>
            <div className="metric-label">Participation Rate</div>
          </div>
        </div>
        
        <div className="metric-card warning">
          <div className="metric-icon">⏰</div>
          <div className="metric-content">
            <div className="metric-value">{data?.total_hours_volunteered || 0}</div>
            <div className="metric-label">Hours Volunteered</div>
          </div>
        </div>
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <h3>Monthly Trends</h3>
          <div className="trend-chart">
            <div className="trend-item">
              <span>Current Month</span>
              <span className="trend-value">{data?.monthly_trends?.current_month || 0}</span>
            </div>
            <div className="trend-item">
              <span>Previous Month</span>
              <span className="trend-value">{data?.monthly_trends?.previous_month || 0}</span>
            </div>
            <div className="trend-item">
              <span>Growth</span>
              <span className={`trend-value ${(data?.monthly_trends?.growth_percentage || 0) >= 0 ? 'positive' : 'negative'}`}>
                {data?.monthly_trends?.growth_percentage || 0}%
              </span>
            </div>
          </div>
        </div>

        <div className="chart-card">
          <h3>Top Departments</h3>
          <div className="empty-state">
            <div className="empty-icon">🏢</div>
            <p>No department data available yet</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// Engagement Tab Component
function EngagementTab({ data }) {
  return (
    <div className="tab-content">
      <div className="engagement-grid">
        <div className="engagement-card">
          <h3>Participation Breakdown</h3>
          <div className="participation-chart">
            <div className="participation-item">
              <div className="participation-bar">
                <div className="bar-fill" style={{ width: `${data?.participation_breakdown?.highly_engaged || 0}%` }}></div>
              </div>
              <span>Highly Engaged: {data?.participation_breakdown?.highly_engaged || 0}%</span>
            </div>
            <div className="participation-item">
              <div className="participation-bar">
                <div className="bar-fill" style={{ width: `${data?.participation_breakdown?.moderately_engaged || 0}%` }}></div>
              </div>
              <span>Moderately Engaged: {data?.participation_breakdown?.moderately_engaged || 0}%</span>
            </div>
            <div className="participation-item">
              <div className="participation-bar">
                <div className="bar-fill" style={{ width: `${data?.participation_breakdown?.low_engagement || 0}%` }}></div>
              </div>
              <span>Low Engagement: {data?.participation_breakdown?.low_engagement || 0}%</span>
            </div>
            <div className="participation-item">
              <div className="participation-bar">
                <div className="bar-fill" style={{ width: `${data?.participation_breakdown?.not_participated || 0}%` }}></div>
              </div>
              <span>Not Participated: {data?.participation_breakdown?.not_participated || 0}%</span>
            </div>
          </div>
        </div>

        <div className="engagement-card">
          <h3>Skill Development</h3>
          <div className="skill-metrics">
            <div className="skill-metric">
              <div className="skill-value">{data?.skill_development?.new_skills_learned || 0}</div>
              <div className="skill-label">New Skills Learned</div>
            </div>
            <div className="skill-metric">
              <div className="skill-value">{data?.skill_development?.learning_hours || 0}</div>
              <div className="skill-label">Learning Hours</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Impact Tab Component
function ImpactTab({ data }) {
  return (
    <div className="tab-content">
      <div className="impact-grid">
        <div className="impact-card">
          <h3>Community Impact</h3>
          <div className="impact-metrics">
            <div className="impact-metric">
              <div className="impact-value">{data?.community_impact?.communities_served || 0}</div>
              <div className="impact-label">Communities Served</div>
            </div>
            <div className="impact-metric">
              <div className="impact-value">{data?.community_impact?.people_helped || 0}</div>
              <div className="impact-label">People Helped</div>
            </div>
            <div className="impact-metric">
              <div className="impact-value">{data?.community_impact?.projects_completed || 0}</div>
              <div className="impact-label">Projects Completed</div>
            </div>
          </div>
        </div>

        <div className="impact-card">
          <h3>Cause Areas</h3>
          <div className="cause-areas">
            {Object.entries(data?.cause_areas || {}).map(([cause, value]) => (
              <div key={cause} className="cause-item">
                <span className="cause-name">{cause.replace('_', ' ').toUpperCase()}</span>
                <div className="cause-bar">
                  <div className="cause-fill" style={{ width: `${value}%` }}></div>
                </div>
                <span className="cause-value">{value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Progress Tab Component
function ProgressTab({ data }) {
  return (
    <div className="tab-content">
      <div className="progress-grid">
        <div className="progress-card">
          <h3>Annual Goals</h3>
          <div className="goal-progress">
            <div className="goal-header">
              <span>Volunteer Events Target</span>
              <span>{data?.annual_goals?.current_events || 0} / {data?.annual_goals?.events_target || 100}</span>
            </div>
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${data?.annual_goals?.percentage_complete || 0}%` }}
              ></div>
            </div>
            <div className="goal-footer">
              <span>{data?.annual_goals?.percentage_complete || 0}% Complete</span>
              <span>{data?.annual_goals?.days_remaining || 365} days remaining</span>
            </div>
          </div>
        </div>

        <div className="progress-card">
          <h3>Milestones</h3>
          <div className="milestones">
            {Object.entries(data?.milestones || {}).map(([milestone, info]) => (
              <div key={milestone} className={`milestone-item ${info.achieved ? 'achieved' : 'pending'}`}>
                <div className="milestone-icon">
                  {info.achieved ? '✅' : '⏳'}
                </div>
                <div className="milestone-content">
                  <div className="milestone-name">{milestone.replace('_', ' ').toUpperCase()}</div>
                  {info.achieved && <div className="milestone-date">{info.date}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Leaderboard Tab Component
function LeaderboardTab({ data }) {
  return (
    <div className="tab-content">
      <div className="leaderboard-grid">
        <div className="leaderboard-card">
          <h3>Top Volunteers</h3>
          {data?.top_volunteers?.length ? (
            <div className="leaderboard-list">
              {data.top_volunteers.map((v, i) => (
                <div key={i} className="leaderboard-item">
                  <div className="leaderboard-rank">#{i + 1}</div>
                  <div className="leaderboard-name">{v.name}</div>
                  <div className="leaderboard-score">{v.score} hrs</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">🏆</div>
              <p>No volunteer data available yet</p>
            </div>
          )}
        </div>

        <div className="leaderboard-card">
          <h3>Department Rankings</h3>
          {data?.department_rankings?.length ? (
            <div className="leaderboard-list">
              {data.department_rankings.map((d, i) => (
                <div key={i} className="leaderboard-item">
                  <div className="leaderboard-rank">#{i + 1}</div>
                  <div className="leaderboard-name">{d.name}</div>
                  <div className="leaderboard-score">{d.score}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">🏢</div>
              <p>No department data available yet</p>
            </div>
          )}
        </div>

        <div className="leaderboard-card">
          <h3>ERG Rankings</h3>
          {data?.erg_rankings?.length ? (
            <div className="leaderboard-list">
              {data.erg_rankings.map((e, i) => (
                <div key={i} className="leaderboard-item">
                  <div className="leaderboard-rank">#{i + 1}</div>
                  <div className="leaderboard-name">{e.name}</div>
                  <div className="leaderboard-score">{e.score}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">👥</div>
              <p>No ERG data available yet</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Trends Tab Component
function TrendsTab({ data }) {
  return (
    <div className="tab-content">
      <div className="trends-grid">
        <div className="trends-card">
          <h3>Participation Trends</h3>
          <div className="trends-chart">
            <div className="trend-metric">
              <span>Daily Average</span>
              <span className="trend-value">{data?.participation_trends?.daily_average || 0}</span>
            </div>
          </div>
        </div>

        <div className="trends-card">
          <h3>Predictive Insights</h3>
          <div className="insights">
            <div className="insight-item">
              <span>Projected Hours</span>
              <span>{data?.predictive_insights?.projected_hours || 0}</span>
            </div>
            <div className="insight-item">
              <span>Engagement Forecast</span>
              <span className="forecast">{data?.predictive_insights?.engagement_forecast || 'stable'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
