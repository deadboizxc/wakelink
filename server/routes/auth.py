"""Authentication routes for WakeLink Cloud Server.

This module provides web-based authentication endpoints for user registration,
login, and logout functionality. Uses cookie-based sessions for maintaining
user authentication state across requests.

Authentication Flow:
    1. User registers via /register (creates account + API token)
    2. User logs in via /login (validates credentials)
    3. Session cookies are set: user_id, username, api_token
    4. User accesses protected routes (dashboard, etc.)
    5. User logs out via /logout (clears all session cookies)

Security Notes:
    - Passwords are hashed before storage (see core.auth)
    - API tokens are generated on registration for programmatic access
    - Cookies should be secured with HttpOnly/Secure flags in production

Author: deadboizxc
Version: 1.0
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth import create_user, authenticate_user
from core.schemas import UserCreate, UserLogin

router = APIRouter(prefix="", tags=["authentication"])
templates = Jinja2Templates(directory="templates")


def no_cache_response(response: Response):
    """Add no-cache headers to prevent Cloudflare caching"""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


@router.get("/register", response_class=HTMLResponse)
async def web_register(request: Request, response: Response):
    """Render the user registration page.
    
    Displays the registration form for new users to create an account.
    
    Args:
        request: The FastAPI request object.
    
    Returns:
        HTMLResponse: Rendered register.html template.
    """
    no_cache_response(response)
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register", response_class=HTMLResponse)
async def web_register_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Process user registration form submission.
    
    Creates a new user account with the provided credentials. On success,
    generates an API token and redirects to dashboard with session cookies.
    
    Args:
        request: The FastAPI request object.
        username: Unique username from form input.
        password: Password from form input (will be hashed).
        db: Database session dependency.
    
    Returns:
        HTMLResponse: Registration page with error message on failure.
        RedirectResponse: Redirect to /dashboard on success with cookies set.
    
    Side Effects:
        - Creates new User record in database
        - Generates unique API token for programmatic access
        - Sets session cookies: user_id, username, api_token
    """
    # Create user data transfer object for validation
    user_data = UserCreate(username=username, password=password)
    
    # Attempt to create user - returns (user, None) on success, (None, error) on failure
    user, error = create_user(db, user_data)
    
    if error:
        # Registration failed - re-render form with error message
        # Common errors: username already taken, validation failure
        return templates.TemplateResponse("register.html", {
            "request": request, 
            "error": error
        })
    
    # Registration successful - redirect to dashboard with session cookies
    # HTTP 303 ensures POST-redirect-GET pattern to prevent form resubmission
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    
    # Set session cookies for authentication persistence
    response.set_cookie(key="user_id", value=str(user.id))  # Primary session identifier
    response.set_cookie(key="username", value=user.username)  # Display name
    response.set_cookie(key="api_token", value=user.api_token)  # For client-side API calls
    
    return response


@router.get("/login", response_class=HTMLResponse)
async def web_login(request: Request, response: Response):
    """Render the user login page.
    
    Displays the login form for existing users to authenticate.
    
    Args:
        request: The FastAPI request object.
    
    Returns:
        HTMLResponse: Rendered login.html template.
    """
    no_cache_response(response)
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login", response_class=HTMLResponse)
async def web_login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Process user login form submission.
    
    Authenticates user credentials and establishes a session on success.
    Password verification uses secure hash comparison (see core.auth).
    
    Args:
        request: The FastAPI request object.
        username: Username from form input.
        password: Password from form input (compared against hash).
        db: Database session dependency.
    
    Returns:
        HTMLResponse: Login page with error message on authentication failure.
        RedirectResponse: Redirect to /dashboard on success with cookies set.
    
    Side Effects:
        Sets session cookies on successful authentication.
    """
    # Create login data transfer object
    login_data = UserLogin(username=username, password=password)
    
    # Verify credentials - returns User on success, None on failure
    user = authenticate_user(db, login_data)
    
    if not user:
        # Authentication failed - invalid username or password
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Invalid credentials"
        })
    
    # Authentication successful - establish session via cookies
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="user_id", value=str(user.id))  # Session identifier
    response.set_cookie(key="username", value=user.username)  # Display name
    response.set_cookie(key="api_token", value=user.api_token)  # API access token
    
    return response


@router.get("/logout")
async def logout():
    """Log out the current user and clear session.
    
    Clears all authentication cookies and redirects to home page.
    This effectively ends the user's session.
    
    Returns:
        RedirectResponse: Redirect to home page (/) with cleared cookies.
    
    Side Effects:
        Deletes session cookies: user_id, username, api_token.
    """
    # Create redirect response to home page
    response = RedirectResponse(url="/")
    
    # Clear all session cookies to invalidate the session
    response.delete_cookie("user_id")  # Remove session identifier
    response.delete_cookie("username")  # Remove cached username
    response.delete_cookie("api_token")  # Remove API token
    
    return response