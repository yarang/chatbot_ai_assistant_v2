---
globs: templates/*.html,static/**/*,api/web_router.py
description: Rules for web UI templates, static files, and web router
---

# Web UI Rules

## Web Directory Structure
You MUST follow this structure for web-related code:
```
templates/               # Jinja2 HTML templates
├── base.html           # Base template with common layout
├── login.html          # Authentication page
├── dashboard.html      # Main dashboard
├── user_dashboard.html # User-specific dashboard
├── admin_dashboard.html# Admin-only dashboard
├── personas.html       # Persona list view
├── persona_detail.html # Persona detail view
├── persona_edit.html   # Persona create/edit form
├── rag_select_room.html# RAG room selection
└── rag_management.html # RAG document management

static/                 # Static assets
├── css/               # Stylesheets
├── js/                # JavaScript files
└── images/            # Image assets

api/
└── web_router.py      # Web UI routes and handlers
```

## Template Design Rules

### Base Template (`base.html`)
- You MUST define a base template with common layout structure.
- You MUST include these blocks for child templates:
  ```jinja2
  {% block title %}{% endblock %}
  {% block extra_css %}{% endblock %}
  {% block content %}{% endblock %}
  {% block extra_js %}{% endblock %}
  ```
- You MUST include navigation menu in base template.
- You MUST include user authentication status display.
- You SHOULD include flash message display area.

### Template Inheritance
- All page templates MUST extend `base.html`:
  ```jinja2
  {% extends "base.html" %}
  ```
- You MUST override required blocks in child templates.
- You MUST NOT duplicate common layout elements in child templates.

### Jinja2 Best Practices
- You MUST use `{{ variable | escape }}` for user-generated content.
- You MUST use `{% if %}` guards for optional content.
- You SHOULD use macros for reusable template components.
- You MUST NOT embed business logic in templates.
- You SHOULD use filters for formatting (date, number, etc.).

Example:
```jinja2
{# Good: Using filters and guards #}
{% if user %}
  <p>Welcome, {{ user.name | escape }}!</p>
  <p>Joined: {{ user.created_at | datetime }}</p>
{% endif %}

{# Bad: Business logic in template #}
{% if user.role == "admin" and user.is_active and not user.is_banned %}
  {# Complex logic belongs in the view #}
{% endif %}
```

### Form Handling
- You MUST include CSRF tokens in all forms (if CSRF protection is enabled).
- You MUST use proper HTML5 input types (`email`, `url`, `number`, etc.).
- You MUST provide client-side validation with HTML5 attributes.
- You SHOULD provide clear error messages for failed validations.
- You MUST use POST method for data-modifying operations.

Example:
```html
<form method="POST" action="/api/personas">
  <input type="text" name="name" required maxlength="100">
  <textarea name="description" rows="5"></textarea>
  <button type="submit">Create Persona</button>
</form>
```

## Web Router Rules (`api/web_router.py`)

### Route Organization
- You MUST group all web UI routes in `web_router.py`.
- You MUST use `APIRouter()` with a prefix (e.g., `/` or `/app`).
- You MUST separate API endpoints from web UI routes.
- Route handlers MUST return `TemplateResponse` for HTML pages.

Example:
```python
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": current_user}
    )
```

### Template Context
- You MUST always pass `request` in template context.
- You SHOULD pass user information if authenticated.
- You MUST NOT pass sensitive data unnecessarily.
- You SHOULD use view models/DTOs for complex data.

### Authentication and Authorization
- You MUST check user authentication before rendering protected pages.
- You MUST redirect unauthenticated users to `/login`.
- You MUST verify user permissions for admin pages.
- You SHOULD use dependency injection for auth checks.

Example:
```python
from fastapi import Depends, HTTPException
from starlette.status import HTTP_303_SEE_OTHER

async def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=HTTP_303_SEE_OTHER,
            headers={"Location": "/login"}
        )
    return await get_user_by_id(user_id)

@router.get("/dashboard")
async def dashboard(
    request: Request,
    user = Depends(get_current_user)
):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user}
    )
```

### Session Management
- You MUST use secure session cookies.
- You MUST set appropriate session expiration.
- You MUST clear session on logout.
- You SHOULD use `itsdangerous` or similar for session security.

### Form Processing
- You MUST validate form data using Pydantic models.
- You MUST handle validation errors gracefully.
- You MUST provide user feedback (flash messages or error displays).
- You SHOULD use redirect-after-POST pattern to prevent duplicate submissions.

Example:
```python
from fastapi import Form
from pydantic import BaseModel, ValidationError

class PersonaForm(BaseModel):
    name: str
    description: str

@router.post("/personas")
async def create_persona(
    request: Request,
    name: str = Form(...),
    description: str = Form(...)
):
    try:
        form = PersonaForm(name=name, description=description)
        # Process form...
        return RedirectResponse("/personas", status_code=303)
    except ValidationError as e:
        return templates.TemplateResponse(
            "persona_edit.html",
            {"request": request, "errors": e.errors()}
        )
```

## Static File Management

### CSS Rules
- You MUST organize CSS by feature/page in separate files.
- You SHOULD use a CSS framework (e.g., Tailwind, Bootstrap) for consistency.
- You MUST minify CSS for production.
- You SHOULD use CSS variables for theming.

### JavaScript Rules
- You MUST write modern JavaScript (ES6+).
- You MUST use `async`/`await` for asynchronous operations.
- You SHOULD organize JS by feature in separate modules.
- You MUST minify and bundle JS for production.
- You SHOULD avoid inline JavaScript in templates.

### Asset Loading
- You MUST use `url_for('static', path='...')` for static file URLs.
- You SHOULD use CDN for third-party libraries when possible.
- You MUST implement cache busting for static assets.
- You SHOULD lazy-load images and non-critical resources.

Example:
```jinja2
<link rel="stylesheet" href="{{ url_for('static', path='css/main.css') }}">
<script src="{{ url_for('static', path='js/app.js') }}" defer></script>
```

## UI/UX Guidelines

### Responsive Design
- You MUST ensure all pages are mobile-responsive.
- You SHOULD use mobile-first design approach.
- You MUST test on multiple screen sizes.
- You SHOULD use responsive images and media queries.

### Accessibility
- You MUST use semantic HTML tags (`<nav>`, `<main>`, `<article>`).
- You MUST provide `alt` text for images.
- You MUST ensure keyboard navigation works.
- You SHOULD use ARIA labels for interactive elements.
- You MUST maintain sufficient color contrast.

### Loading States
- You MUST show loading indicators for async operations.
- You SHOULD disable form buttons during submission.
- You MUST provide feedback for successful/failed operations.

### Error Handling
- You MUST display user-friendly error messages.
- You MUST NOT expose technical error details to users.
- You SHOULD log frontend errors for debugging.
- You MUST provide recovery actions (e.g., "Try Again" button).

## Telegram Login Widget

### Integration Rules
- You MUST use the official Telegram Login Widget.
- You MUST verify the authentication hash server-side.
- You MUST NOT trust client-side authentication data.
- You MUST implement the data check algorithm per Telegram docs.

Example:
```html
<script async src="https://telegram.org/js/telegram-widget.js?22"
        data-telegram-login="YOUR_BOT_USERNAME"
        data-size="large"
        data-auth-url="/auth/telegram"
        data-request-access="write">
</script>
```

Backend verification:
```python
import hmac
import hashlib

def verify_telegram_auth(data: dict, bot_token: str) -> bool:
    """Verify Telegram authentication data."""
    check_hash = data.pop("hash", None)
    if not check_hash:
        return False

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data.items())
    )

    secret_key = hashlib.sha256(bot_token.encode()).digest()
    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    return computed_hash == check_hash
```

## Dashboard Design

### User Dashboard
- You MUST display recent conversations.
- You SHOULD show usage statistics (if available).
- You MUST provide quick access to common actions.
- You SHOULD display active persona information.

### Admin Dashboard
- You MUST restrict access to admin users only.
- You SHOULD display system-wide statistics.
- You SHOULD provide user management features.
- You MAY include system health monitoring.

### Conversation History
- You MUST display conversations in chronological order.
- You SHOULD implement pagination for long lists.
- You MUST show clear sender identification (user/AI).
- You SHOULD highlight the current active conversation.

## Real-Time Features

### Server-Sent Events (SSE)
- You MAY use SSE for streaming AI responses.
- You MUST handle connection errors gracefully.
- You MUST implement reconnection logic.
- You SHOULD show connection status to users.

### WebSocket (Optional)
- You MAY use WebSocket for real-time chat.
- You MUST implement proper connection lifecycle management.
- You MUST handle reconnection and fallback scenarios.

## Security Best Practices

### XSS Prevention
- You MUST escape all user-generated content.
- You MUST use Content Security Policy (CSP) headers.
- You MUST sanitize HTML input if rich text is allowed.

### CSRF Protection
- You SHOULD enable CSRF protection for forms.
- You MUST include CSRF tokens in all state-changing requests.

### Session Security
- You MUST use HTTPOnly cookies for sessions.
- You MUST use Secure flag in production (HTTPS).
- You MUST set SameSite attribute appropriately.
- You SHOULD implement session timeout.

### Data Privacy
- You MUST NOT log sensitive user data.
- You MUST comply with GDPR/privacy regulations.
- You SHOULD provide data export/deletion features.

## Performance Optimization

### Template Rendering
- You SHOULD cache compiled templates.
- You MUST avoid N+1 queries in template data preparation.
- You SHOULD use database pagination for large lists.

### Asset Optimization
- You MUST minify CSS and JavaScript.
- You SHOULD use image compression.
- You SHOULD implement lazy loading.
- You SHOULD use browser caching headers.

### Database Queries
- You MUST optimize queries used in view rendering.
- You SHOULD use select_related/prefetch for related data.
- You MUST implement pagination for large datasets.

## Testing Web UI

### Template Tests
- You SHOULD test template rendering with various data.
- You MUST test authenticated and unauthenticated states.
- You SHOULD test error states.

### Integration Tests
- You SHOULD test full request/response cycles.
- You MUST test form submission and validation.
- You SHOULD test authentication flows.

### Browser Tests (Optional)
- You MAY use Selenium/Playwright for E2E tests.
- You SHOULD test critical user journeys.
- You MUST test on multiple browsers if possible.

## Anti-Patterns to Avoid

### DO NOT:
- Put business logic in templates
- Use inline styles or scripts extensively
- Ignore mobile responsiveness
- Trust client-side validation alone
- Expose sensitive data in HTML/JS
- Use synchronous blocking operations in routes
- Hardcode URLs (use `url_for` instead)
- Store sensitive data in localStorage/sessionStorage
- Ignore accessibility standards
- Create god templates (split into components)

## Best Practices

### DO:
- Use template inheritance extensively
- Implement proper error boundaries
- Provide loading states and feedback
- Use semantic HTML
- Implement progressive enhancement
- Test with various user permissions
- Optimize for performance
- Follow accessibility guidelines
- Use meaningful page titles and meta tags
- Implement proper SEO if needed
- Log frontend errors server-side
- Use feature flags for experimental UI
- Document complex UI interactions
- Version your frontend assets
