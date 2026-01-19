import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { api, Job } from '../api/client';
import JobUpload from '../components/JobUpload';
import JobList from '../components/JobList';
import './Dashboard.css';

export default function Dashboard() {
  const { user, loading: authLoading, logout } = useAuth();
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/');
    }
  }, [user, authLoading, navigate]);

  const fetchJobs = async () => {
    try {
      const data = await api.jobs.list();
      setJobs(data);
    } catch (err) {
      console.error('Failed to fetch jobs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchJobs();
    }
  }, [user]);

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  if (authLoading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="dashboard">
      <nav className="navbar">
        <div className="container">
          <Link to="/dashboard" className="navbar-brand">3D Print Queue</Link>
          <div className="navbar-nav">
            {user.is_admin && (
              <Link to="/admin" className="navbar-link">Admin</Link>
            )}
            <div className="user-info">
              {user.avatar_url && (
                <img src={user.avatar_url} alt="" className="user-avatar" />
              )}
              <span className="user-name">{user.name || user.email}</span>
            </div>
            <button className="btn btn-secondary" onClick={handleLogout}>
              Logout
            </button>
          </div>
        </div>
      </nav>

      <main className="main-content">
        <div className="container">
          <header className="page-header">
            <h1 className="page-title">My Print Jobs</h1>
            <p className="page-description">Upload .3mf files to submit them for printing</p>
          </header>

          <JobUpload onUploadComplete={fetchJobs} />
          <JobList jobs={jobs} loading={loading} />
        </div>
      </main>
    </div>
  );
}
