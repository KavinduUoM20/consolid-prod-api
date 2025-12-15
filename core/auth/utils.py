import uuid
from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from core.auth.schemas import TokenDataSchema
from core.auth.models import User
from core.auth.config import get_auth_settings


# Password hashing context with fallback configuration
try:
    # Try to create bcrypt context with explicit configuration
    pwd_context = CryptContext(
        schemes=["bcrypt"],
        deprecated="auto",
        bcrypt__rounds=12,  # Explicit rounds for consistency
        bcrypt__ident="2b"  # Use 2b variant for better compatibility
    )
    # Test if bcrypt works by hashing a short test password
    pwd_context.hash("test")
except Exception as e:
    print(f"Bcrypt initialization failed: {e}")
    print("Falling back to simpler bcrypt configuration...")
    # Fallback to minimal bcrypt configuration
    try:
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        pwd_context.hash("test")
    except Exception as e2:
        print(f"Simple bcrypt also failed: {e2}")
        print("Falling back to PBKDF2 (less secure but works)...")
        # Ultimate fallback to PBKDF2
        pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Get auth settings
auth_settings = get_auth_settings()


class PasswordUtils:
    """Utilities for password hashing and verification."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        # Bcrypt has a 72-byte limit, truncate if necessary
        if len(password.encode('utf-8')) > 72:
            password = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        # Bcrypt has a 72-byte limit, truncate if necessary
        if len(plain_password.encode('utf-8')) > 72:
            plain_password = plain_password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def generate_password_reset_token() -> str:
        """Generate a secure token for password reset."""
        return str(uuid.uuid4())


class JWTUtils:
    """Utilities for JWT token creation and validation."""
    
    @staticmethod
    def create_access_token(user: User, expires_delta: Optional[timedelta] = None) -> tuple[str, str, int]:
        """
        Create a JWT access token for a user.
        
        Returns:
            tuple: (token, jti, expires_in_seconds)
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=auth_settings.JWT_EXPIRE_MINUTES)
        
        jti = str(uuid.uuid4())  # Unique token identifier
        
        to_encode = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "tenant_id": str(user.tenant_id),
            "tenant_slug": user.tenant.slug if user.tenant else "default",
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": jti
        }
        
        encoded_jwt = jwt.encode(to_encode, auth_settings.JWT_SECRET_KEY, algorithm=auth_settings.JWT_ALGORITHM)
        expires_in = int((expire - datetime.utcnow()).total_seconds())
        
        return encoded_jwt, jti, expires_in
    
    @staticmethod
    def verify_token(token: str) -> Optional[TokenDataSchema]:
        """
        Verify and decode a JWT token.
        
        Returns:
            TokenDataSchema if valid, None if invalid
        """
        try:
            payload = jwt.decode(token, auth_settings.JWT_SECRET_KEY, algorithms=[auth_settings.JWT_ALGORITHM])
            
            # Extract required fields
            user_id: str = payload.get("sub")
            username: str = payload.get("username")
            email: str = payload.get("email")
            role: str = payload.get("role")
            tenant_id: str = payload.get("tenant_id")
            tenant_slug: str = payload.get("tenant_slug")
            exp: int = payload.get("exp")
            iat: int = payload.get("iat")
            jti: str = payload.get("jti")
            
            if not all([user_id, username, email, role, tenant_id, tenant_slug, exp, iat, jti]):
                return None
            
            return TokenDataSchema(
                sub=user_id,
                username=username,
                email=email,
                role=role,
                tenant_id=tenant_id,
                tenant_slug=tenant_slug,
                exp=exp,
                iat=iat,
                jti=jti
            )
        except JWTError:
            return None
    
    @staticmethod
    def is_token_expired(token_data: TokenDataSchema) -> bool:
        """Check if a token is expired."""
        return datetime.utcnow().timestamp() > token_data.exp
    
    @staticmethod
    def create_refresh_token(user: User, expires_delta: Optional[timedelta] = None) -> tuple[str, str, int]:
        """
        Create a JWT refresh token for a user.
        
        Returns:
            tuple: (token, jti, expires_in_seconds)
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=7)  # Refresh tokens last longer
        
        jti = str(uuid.uuid4())
        
        to_encode = {
            "sub": str(user.id),
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": jti
        }
        
        encoded_jwt = jwt.encode(to_encode, auth_settings.JWT_SECRET_KEY, algorithm=auth_settings.JWT_ALGORITHM)
        expires_in = int((expire - datetime.utcnow()).total_seconds())
        
        return encoded_jwt, jti, expires_in


class ValidationUtils:
    """Utilities for data validation."""
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Basic email validation."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def is_valid_username(username: str) -> bool:
        """Validate username format."""
        if len(username) < 3 or len(username) > 100:
            return False
        return username.replace('_', '').replace('-', '').replace('.', '').isalnum()
    
    @staticmethod
    def is_strong_password(password: str) -> tuple[bool, list[str]]:
        """
        Check if password meets strength requirements.
        
        Returns:
            tuple: (is_valid, list_of_errors)
        """
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        # Optional: Check for special characters
        # if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        #     errors.append("Password must contain at least one special character")
        
        return len(errors) == 0, errors


class TenantUtils:
    """Utilities for tenant operations."""
    
    @staticmethod
    def generate_tenant_slug(name: str) -> str:
        """Generate a URL-friendly slug from tenant name."""
        import re
        # Convert to lowercase and replace spaces with hyphens
        slug = name.lower().replace(' ', '-')
        # Remove non-alphanumeric characters except hyphens and underscores
        slug = re.sub(r'[^a-z0-9\-_]', '', slug)
        # Remove multiple consecutive hyphens
        slug = re.sub(r'-+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        return slug or "tenant"  # Fallback if slug is empty
    
    @staticmethod
    def is_valid_tenant_slug(slug: str) -> bool:
        """Validate tenant slug format."""
        if len(slug) < 1 or len(slug) > 100:
            return False
        return slug.replace('-', '').replace('_', '').isalnum()


# Constants for token types
class TokenType:
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"
