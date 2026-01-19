import { useState } from 'react';
import { api, JobWithUser, JobStatus } from '../api/client';
import './AdminQueue.css';

interface AdminQueueProps {
  jobs: JobWithUser[];
  loading: boolean;
  onUpdate: () => void;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getStatusLabel(status: JobStatus): string {
  const labels: Record<JobStatus, string> = {
    submitted: 'Pending',
    approved: 'Approved',
    rejected: 'Rejected',
    queued: 'Queued',
    printing: 'Printing',
    done: 'Done',
    failed: 'Failed',
  };
  return labels[status];
}

export default function AdminQueue({ jobs, loading, onUpdate }: AdminQueueProps) {
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleApprove = async (jobId: string) => {
    setActionLoading(jobId);
    setError(null);
    try {
      await api.admin.approveJob(jobId);
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve job');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (jobId: string) => {
    const message = window.prompt('Rejection reason (optional):');
    setActionLoading(jobId);
    setError(null);
    try {
      await api.admin.rejectJob(jobId, message || undefined);
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject job');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDownload = async (jobId: string) => {
    try {
      const { download_url } = await api.jobs.getDownloadUrl(jobId);
      window.open(download_url, '_blank');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get download URL');
    }
  };

  if (loading) {
    return (
      <div className="admin-queue-loading">
        <div className="spinner"></div>
        <p>Loading jobs...</p>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="admin-queue-empty">
        <p>No pending jobs to review.</p>
      </div>
    );
  }

  return (
    <div className="admin-queue">
      {error && <div className="admin-error">{error}</div>}

      <table className="admin-table">
        <thead>
          <tr>
            <th>File</th>
            <th>User</th>
            <th>Size</th>
            <th>Status</th>
            <th>Submitted</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id}>
              <td className="job-filename">
                <button
                  className="filename-link"
                  onClick={() => handleDownload(job.id)}
                >
                  {job.filename}
                </button>
              </td>
              <td>
                <div className="user-cell">
                  {job.user.avatar_url && (
                    <img
                      src={job.user.avatar_url}
                      alt=""
                      className="user-avatar-small"
                    />
                  )}
                  <span>{job.user.name || job.user.email}</span>
                </div>
              </td>
              <td>{formatFileSize(job.file_size_bytes)}</td>
              <td>
                <span className={`badge badge-${job.status}`}>
                  {getStatusLabel(job.status)}
                </span>
              </td>
              <td>{formatDate(job.submitted_at)}</td>
              <td>
                {job.status === 'submitted' && (
                  <div className="action-buttons">
                    <button
                      className="btn btn-success btn-sm"
                      onClick={() => handleApprove(job.id)}
                      disabled={actionLoading === job.id}
                    >
                      Approve
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => handleReject(job.id)}
                      disabled={actionLoading === job.id}
                    >
                      Reject
                    </button>
                  </div>
                )}
                {job.status_message && (
                  <p className="status-message">{job.status_message}</p>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
