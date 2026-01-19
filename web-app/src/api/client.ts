const API_BASE = import.meta.env.PROD ? '' : '/api';

export interface User {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
  is_admin: boolean;
  created_at: string;
}

export type JobStatus = 'submitted' | 'approved' | 'rejected' | 'queued' | 'printing' | 'done' | 'failed';

export interface Job {
  id: string;
  user_id: string;
  filename: string;
  tigris_key: string;
  file_size_bytes: number;
  status: JobStatus;
  status_message: string | null;
  submitted_at: string;
  approved_at: string | null;
  completed_at: string | null;
  approved_by_id: string | null;
}

export interface JobWithUser extends Job {
  user: User;
}

export interface UploadUrlResponse {
  job_id: string;
  upload_url: string;
  tigris_key: string;
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}

export const api = {
  auth: {
    getMe: () => fetchApi<User>('/auth/me'),
    logout: () => fetchApi<{ message: string }>('/auth/logout', { method: 'POST' }),
    getGoogleLoginUrl: () => `${API_BASE}/auth/google`,
    getGithubLoginUrl: () => `${API_BASE}/auth/github`,
  },

  jobs: {
    create: (filename: string, file_size_bytes: number) =>
      fetchApi<UploadUrlResponse>('/jobs', {
        method: 'POST',
        body: JSON.stringify({ filename, file_size_bytes }),
      }),

    list: () => fetchApi<Job[]>('/jobs'),

    get: (id: string) => fetchApi<Job>(`/jobs/${id}`),

    getDownloadUrl: (id: string) =>
      fetchApi<{ download_url: string }>(`/jobs/${id}/download`),

    uploadFile: async (uploadUrl: string, file: File) => {
      const response = await fetch(uploadUrl, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': 'application/octet-stream',
        },
      });
      if (!response.ok) {
        throw new Error('Failed to upload file');
      }
    },
  },

  admin: {
    listPendingJobs: () => fetchApi<JobWithUser[]>('/admin/jobs'),

    listAllJobs: () => fetchApi<JobWithUser[]>('/admin/jobs/all'),

    approveJob: (id: string, message?: string) =>
      fetchApi<JobWithUser>(`/admin/jobs/${id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ message }),
      }),

    rejectJob: (id: string, message?: string) =>
      fetchApi<JobWithUser>(`/admin/jobs/${id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ message }),
      }),

    queueJob: (id: string) =>
      fetchApi<JobWithUser>(`/admin/jobs/${id}/queue`, {
        method: 'POST',
      }),
  },
};
