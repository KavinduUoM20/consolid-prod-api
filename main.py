# main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from api.router import router as api_router  # << use this, not api.v1.router
from apps.dociq.db import init_dociq_db
from apps.dociq.config import get_dociq_settings
from core.auth.db import setup_initial_data

app = FastAPI(title="Consolidator AI API", version="1.0.0")

# Get settings
settings = get_dociq_settings()

# Add trusted host middleware for security
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure this properly for production
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Custom middleware to handle HTTPS redirects and proxy headers
class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Check if we're behind a proxy and get the real protocol
        forwarded_proto = request.headers.get("x-forwarded-proto")
        forwarded_host = request.headers.get("x-forwarded-host")
        forwarded_for = request.headers.get("x-forwarded-for")
        
        # If we're behind a proxy and it's HTTP, redirect to HTTPS
        if forwarded_proto == "http" and forwarded_host:
            # Construct HTTPS URL
            https_url = f"https://{forwarded_host}{request.url.path}"
            if request.url.query:
                https_url += f"?{request.url.query}"
            return RedirectResponse(url=https_url, status_code=301)
        
        # Continue with the request
        response = await call_next(request)
        return response

# Custom middleware to add security headers
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers to prevent mixed content
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "upgrade-insecure-requests"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response

# Add HTTPS redirect middleware
app.add_middleware(HTTPSRedirectMiddleware)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await init_dociq_db()
    # Setup initial auth data (default tenant and super admin)
    try:
        result = await setup_initial_data()
        if result[0] is None:  # Auth setup failed but app should continue
            print("Auth setup skipped due to compatibility issues. App will run without initial admin user.")
    except Exception as e:
        print(f"Critical error during auth setup: {e}")
        # Don't crash the entire app for auth setup issues
        print("Application will continue without auth setup. You can create users manually via API.")

app.include_router(api_router) 