from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.config import get_settings
from app.routers import auth, jobs, admin, printer
from app.schemas import HealthResponse

settings = get_settings()

app = FastAPI(
    title="3D Printer Job Queue API",
    description="API for managing 3D print job submissions and approvals",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(printer.router, prefix="/printer", tags=["printer"])


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy")
