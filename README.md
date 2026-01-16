# 3D Printer Job Queue

A web application for managing 3D print job submissions with user authentication and admin approval workflows.

## Architecture

| Component | Stack | Purpose |
|-----------|-------|---------|
| **fly-app** | FastAPI + PostgreSQL | REST API, OAuth, job queue management |
| **web-app** | React + Vite + TypeScript | User & admin interface |

### Storage & Auth
- **File Storage**: Tigris (S3-compatible, Fly.io native)
- **Authentication**: OAuth (Google/GitHub)
- **Database**: PostgreSQL

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL
- Google/GitHub OAuth credentials (for production)
- Tigris storage credentials (for file uploads)

### Backend Setup

```bash
cd fly-app

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and configure
cp .env.example .env
# Edit .env with your credentials

# Create database
createdb printqueue  # Or use your preferred method

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd web-app

# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at http://localhost:5173

## API Endpoints

### Authentication (`/auth`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/auth/google` | Start Google OAuth |
| GET | `/auth/google/callback` | Google callback |
| GET | `/auth/github` | Start GitHub OAuth |
| GET | `/auth/github/callback` | GitHub callback |
| GET | `/auth/me` | Get current user |
| POST | `/auth/logout` | Logout |

### Jobs (`/jobs`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/jobs` | Create job & get upload URL |
| GET | `/jobs` | List my jobs |
| GET | `/jobs/{id}` | Get job detail |
| GET | `/jobs/{id}/download` | Get download URL |

### Admin (`/admin`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/jobs` | List pending jobs |
| GET | `/admin/jobs/all` | List all jobs |
| POST | `/admin/jobs/{id}/approve` | Approve job |
| POST | `/admin/jobs/{id}/reject` | Reject job |
| POST | `/admin/jobs/{id}/queue` | Queue job for printing |

## Environment Variables

### Backend (fly-app/.env)

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/printqueue

# JWT Secret
SECRET_KEY=your-secret-key-here

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# GitHub OAuth
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Tigris Storage
TIGRIS_ACCESS_KEY_ID=your-tigris-access-key
TIGRIS_SECRET_ACCESS_KEY=your-tigris-secret-key
TIGRIS_ENDPOINT_URL=https://fly.storage.tigris.dev
TIGRIS_BUCKET_NAME=print-jobs

# URLs
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000
```

## Database Models

### User
- `id`, `email`, `name`, `avatar_url`
- `oauth_provider`, `oauth_id`
- `is_admin`, `created_at`

### Job
- `id`, `user_id`, `filename`, `tigris_key`, `file_size_bytes`
- `status`: submitted | approved | rejected | queued | printing | done | failed
- `status_message`
- `submitted_at`, `approved_at`, `completed_at`
- `approved_by_id`

## File Upload Flow

1. Client calls `POST /jobs` with filename and file size
2. Server creates job record, returns pre-signed upload URL
3. Client uploads file directly to Tigris using pre-signed URL
4. Job status is "submitted", awaiting admin review

## Deployment (Fly.io)

### Backend
```bash
cd fly-app
fly launch
fly postgres create
fly secrets set SECRET_KEY=... GOOGLE_CLIENT_ID=... # etc
fly deploy
```

### Storage
```bash
fly storage create
# Configure TIGRIS_* environment variables with credentials
```

## Making a User Admin

Connect to your database and run:
```sql
UPDATE users SET is_admin = true WHERE email = 'admin@example.com';
```
