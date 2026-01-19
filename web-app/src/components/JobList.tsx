import { Job, JobStatus } from '../api/client';
import './JobList.css';

interface JobListProps {
  jobs: Job[];
  loading: boolean;
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
    submitted: 'Pending Review',
    approved: 'Approved',
    rejected: 'Rejected',
    queued: 'In Queue',
    printing: 'Printing',
    done: 'Completed',
    failed: 'Failed',
  };
  return labels[status];
}

export default function JobList({ jobs, loading }: JobListProps) {
  if (loading) {
    return (
      <div className="job-list-loading">
        <div className="spinner"></div>
        <p>Loading jobs...</p>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="job-list-empty">
        <p>No jobs yet. Upload a .3mf file to get started.</p>
      </div>
    );
  }

  return (
    <div className="job-list">
      <table className="job-table">
        <thead>
          <tr>
            <th>File</th>
            <th>Size</th>
            <th>Status</th>
            <th>Submitted</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id}>
              <td className="job-filename">{job.filename}</td>
              <td>{formatFileSize(job.file_size_bytes)}</td>
              <td>
                <span className={`badge badge-${job.status}`}>
                  {getStatusLabel(job.status)}
                </span>
              </td>
              <td>{formatDate(job.submitted_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
