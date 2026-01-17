from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from app.config import get_settings

settings = get_settings()

oauth = OAuth()

# Google OAuth
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# GitHub OAuth
oauth.register(
    name="github",
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret,
    authorize_url="https://github.com/login/oauth/authorize",
    access_token_url="https://github.com/login/oauth/access_token",
    client_kwargs={"scope": "user:email"},
    api_base_url="https://api.github.com/",
)
