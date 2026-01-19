import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { api, JobWithUser } from '../api/client';
import AdminQueue from '../components/AdminQueue';
import './Admin.css';

export default function Admin() {
  const { user, loading: authLoading, logout } = useAuth();
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<JobWithUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        navigate('/');
      } else if (!user.is_admin) {
        navigate('/dashboard');
      }
    }
  }, [user, authLoading, navigate]);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const data = showAll
        ? await api.admin.listAllJobs()
        : await api.admin.listPendingJobs();
      setJobs(data);
    } catch (err) {
      console.error('Failed to fetch jobs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.is_admin) {
      fetchJobs();
    }
  }, [user, showAll]);

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  if (authLoading) {
    return (
      <div className="admin-loading">
        <div className="spinner"></div>
      </div>
    );
  }

  if (!user || !user.is_admin) {
    return null;
  }

  return (
    <div className="admin">
      <nav className="navbar">
        <div className="container">
          <Link to="/dashboard" className="navbar-brand">3D Print Queue</Link>
          <div className="navbar-nav">
            <Link to="/dashboard" className="navbar-link">My Jobs</Link>
            <Link to="/admin" className="navbar-link active">Admin</Link>
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
            <div className="page-header-row">
              <div>
                <h1 className="page-title">Admin Queue</h1>
                <p className="page-description">Review and approve print job submissions</p>
              </div>
              <div className="view-toggle">
                <button
                  className={`btn ${!showAll ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setShowAll(false)}
                >
                  Pending
                </button>
                <button
                  className={`btn ${showAll ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setShowAll(true)}
                >
                  All Jobs
                </button>
              </div>
            </div>
          </header>

          <AdminQueue jobs={jobs} loading={loading} onUpdate={fetchJobs} />
        </div>
      </main>
    </div>
  );
}
