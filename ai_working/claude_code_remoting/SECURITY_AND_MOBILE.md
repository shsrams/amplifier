# Security & Mobile Strategy

## Security Architecture

### Progressive Security Model

```
Level 0: Local Only (MVP)
├── No authentication required
├── Bind to localhost only
└── Trust local user completely

Level 1: LAN Access
├── Simple token authentication
├── IP whitelist
└── Basic rate limiting

Level 2: Internet Access
├── OAuth2/JWT authentication
├── HTTPS mandatory
├── Session management
└── Audit logging

Level 3: Multi-User
├── User roles and permissions
├── Resource isolation
├── Quota management
└── Compliance features
```

## Security Implementation

### Phase 1: Local Security (MVP)

```python
# Localhost only binding
app = FastAPI()

if __name__ == "__main__":
    # Only accessible from local machine
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

**Security Measures**:
- Bind to localhost only
- No external network access
- File system access limited to user permissions
- Process runs as current user

### Phase 2: LAN Security

```python
# Simple token authentication
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

# Environment variable for token
AUTH_TOKEN = os.getenv("CLAUDE_WEB_TOKEN", secrets.token_urlsafe(32))

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

@app.post("/api/chat", dependencies=[Depends(verify_token)])
async def chat(request: Request):
    # Protected endpoint
    pass
```

**Security Measures**:
- Shared secret token
- IP address whitelist
- Rate limiting (10 req/min)
- Failed attempt logging

### Phase 3: Internet Security

```python
# OAuth2 with JWT
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import JWTStrategy

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.JWT_SECRET,
        lifetime_seconds=3600,
        token_audience="claude-code:auth",
    )

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=BearerTransport(tokenUrl="auth/login"),
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

# Protected routes
current_active_user = fastapi_users.current_user(active=True)

@app.post("/api/chat")
async def chat(
    request: Request,
    user: User = Depends(current_active_user)
):
    # User-specific session
    session_id = f"{user.id}:{request.session_id}"
    # ... rest of implementation
```

**Security Measures**:
- Industry standard OAuth2/JWT
- HTTPS only (Let's Encrypt)
- CORS configuration
- Rate limiting per user
- Session timeout
- Audit logging
- OWASP Top 10 compliance

### Phase 4: Multi-User Security

```python
# Role-based access control
class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"

class ToolPermission(BaseModel):
    read: bool = True
    write: bool = False
    bash: bool = False
    web_search: bool = True

ROLE_PERMISSIONS = {
    UserRole.ADMIN: ToolPermission(read=True, write=True, bash=True, web_search=True),
    UserRole.USER: ToolPermission(read=True, write=True, bash=False, web_search=True),
    UserRole.VIEWER: ToolPermission(read=True, write=False, bash=False, web_search=False),
}

async def check_tool_permission(
    tool_name: str,
    user: User = Depends(current_active_user)
):
    permissions = ROLE_PERMISSIONS[user.role]
    if not getattr(permissions, tool_name.lower(), False):
        raise HTTPException(
            status_code=403,
            detail=f"User lacks permission for tool: {tool_name}"
        )
```

## Remote Access Options

### Option 1: Cloudflare Tunnel (Recommended)

```bash
# Install Cloudflare Tunnel
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared

# Create tunnel
./cloudflared tunnel create claude-code

# Configure tunnel
cat > config.yml <<EOF
tunnel: claude-code
credentials-file: /home/user/.cloudflared/claude-code.json

ingress:
  - hostname: claude.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
EOF

# Run tunnel
./cloudflared tunnel run claude-code
```

**Advantages**:
- Zero port forwarding
- Automatic HTTPS
- DDoS protection
- No static IP needed

### Option 2: Tailscale VPN

```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Start Tailscale
sudo tailscale up

# Access via Tailscale IP
# https://100.x.x.x:8000
```

**Advantages**:
- End-to-end encryption
- No public exposure
- Easy team access
- MagicDNS

### Option 3: Self-Hosted with Caddy

```caddyfile
claude.yourdomain.com {
    reverse_proxy localhost:8000 {
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
    }
    
    # Automatic HTTPS
    tls {
        dns cloudflare {env.CF_API_TOKEN}
    }
    
    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
    }
}
```

## Mobile-First Design

### Progressive Web App Configuration

```json
// manifest.json
{
  "name": "Claude Code Remote",
  "short_name": "Claude",
  "description": "AI coding assistant in your pocket",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#000000",
  "background_color": "#ffffff",
  "orientation": "portrait",
  "icons": [
    {
      "src": "/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ],
  "categories": ["productivity", "developer"],
  "screenshots": [
    {
      "src": "/screenshot1.png",
      "sizes": "1080x1920",
      "type": "image/png"
    }
  ]
}
```

### Service Worker for Offline

```javascript
// sw.js
const CACHE_NAME = 'claude-code-v1';
const urlsToCache = [
  '/',
  '/static/styles.css',
  '/static/app.js',
  '/static/icon-192.png'
];

// Install event - cache resources
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return response
        if (response) {
          return response;
        }
        
        // Clone the request
        const fetchRequest = event.request.clone();
        
        return fetch(fetchRequest).then(response => {
          // Check if valid response
          if (!response || response.status !== 200) {
            return response;
          }
          
          // Clone the response
          const responseToCache = response.clone();
          
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseToCache);
          });
          
          return response;
        });
      })
  );
});

// Push notifications
self.addEventListener('push', event => {
  const options = {
    body: event.data.text(),
    icon: '/icon-192.png',
    badge: '/badge.png',
    vibrate: [200, 100, 200],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'view',
        title: 'View',
        icon: '/images/checkmark.png'
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/images/xmark.png'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification('Claude Code', options)
  );
});
```

### Mobile UI Optimizations

```css
/* Mobile-first responsive design */

/* Touch-friendly tap targets */
button, a, input, textarea {
    min-height: 44px;
    min-width: 44px;
}

/* Prevent zoom on input focus (iOS) */
input, textarea, select {
    font-size: 16px;
}

/* Safe area insets for notched devices */
.app-container {
    padding: env(safe-area-inset-top) 
             env(safe-area-inset-right) 
             env(safe-area-inset-bottom) 
             env(safe-area-inset-left);
}

/* Smooth scrolling with momentum */
.message-container {
    -webkit-overflow-scrolling: touch;
    overscroll-behavior-y: contain;
}

/* Prevent text selection on UI elements */
.ui-element {
    -webkit-user-select: none;
    user-select: none;
    -webkit-touch-callout: none;
}

/* Landscape optimization */
@media (orientation: landscape) and (max-height: 500px) {
    header {
        position: absolute;
        transform: translateY(-100%);
    }
    
    .chat-input {
        padding: 0.5rem;
    }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
    :root {
        --bg-color: #1a1a1a;
        --text-color: #e0e0e0;
        --accent-color: #4a9eff;
    }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}
```

### Mobile-Specific Features

```javascript
// Detect mobile and adjust UI
class MobileOptimizations {
    constructor() {
        this.isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        this.isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
        this.initMobileFeatures();
    }
    
    initMobileFeatures() {
        if (this.isMobile) {
            this.enableTouchGestures();
            this.setupVirtualKeyboard();
            this.handleOrientationChange();
            this.enableHapticFeedback();
        }
    }
    
    enableTouchGestures() {
        let startX = 0;
        
        document.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
        });
        
        document.addEventListener('touchend', (e) => {
            const endX = e.changedTouches[0].clientX;
            const diffX = endX - startX;
            
            // Swipe to go back
            if (diffX > 100) {
                this.navigateBack();
            }
        });
    }
    
    setupVirtualKeyboard() {
        // Adjust viewport when keyboard appears
        if (this.isIOS) {
            const input = document.getElementById('prompt-input');
            
            input.addEventListener('focus', () => {
                document.body.style.position = 'fixed';
                document.body.style.width = '100%';
            });
            
            input.addEventListener('blur', () => {
                document.body.style.position = '';
                document.body.style.width = '';
            });
        }
    }
    
    handleOrientationChange() {
        window.addEventListener('orientationchange', () => {
            // Adjust UI for new orientation
            setTimeout(() => {
                this.adjustLayout();
            }, 100);
        });
    }
    
    enableHapticFeedback() {
        // Vibrate on button press
        document.querySelectorAll('button').forEach(button => {
            button.addEventListener('click', () => {
                if ('vibrate' in navigator) {
                    navigator.vibrate(10);
                }
            });
        });
    }
}
```

### Push Notifications

```python
# Backend push notification support
from pywebpush import webpush, WebPushException

class NotificationService:
    def __init__(self):
        self.vapid_private_key = settings.VAPID_PRIVATE_KEY
        self.vapid_public_key = settings.VAPID_PUBLIC_KEY
        self.vapid_claims = {
            "sub": "mailto:admin@claude-code.com"
        }
    
    async def send_notification(
        self,
        subscription_info: dict,
        title: str,
        body: str,
        icon: str = "/icon-192.png",
        badge: str = "/badge.png",
        url: str = "/"
    ):
        try:
            webpush(
                subscription_info=subscription_info,
                data=json.dumps({
                    "title": title,
                    "body": body,
                    "icon": icon,
                    "badge": badge,
                    "url": url
                }),
                vapid_private_key=self.vapid_private_key,
                vapid_claims=self.vapid_claims
            )
        except WebPushException as e:
            logger.error(f"Push notification failed: {e}")
    
    async def notify_task_complete(self, user_id: str, task_summary: str):
        # Get user's push subscriptions
        subscriptions = await self.get_user_subscriptions(user_id)
        
        for sub in subscriptions:
            await self.send_notification(
                subscription_info=sub,
                title="Task Complete",
                body=task_summary,
                url=f"/session/{session_id}"
            )
```

## Security Checklist

### MVP Release
- [x] Localhost only binding
- [x] No sensitive data in logs
- [x] Secure session IDs (UUID4)
- [x] SQL injection prevention (prepared statements)
- [x] XSS prevention (content escaping)

### LAN Release
- [ ] Token authentication
- [ ] HTTPS with self-signed cert
- [ ] Rate limiting
- [ ] Failed auth logging
- [ ] IP whitelist

### Internet Release
- [ ] OAuth2/JWT implementation
- [ ] HTTPS with valid certificate
- [ ] CORS properly configured
- [ ] Security headers (HSTS, CSP, etc.)
- [ ] Rate limiting per user
- [ ] Audit logging
- [ ] Input validation
- [ ] Output encoding
- [ ] Session timeout
- [ ] CSRF protection

### Production Release
- [ ] Penetration testing
- [ ] Security audit
- [ ] Compliance check (GDPR, etc.)
- [ ] Incident response plan
- [ ] Backup and recovery
- [ ] Monitoring and alerting
- [ ] DDoS protection
- [ ] WAF configuration

## Mobile Testing Checklist

### Core Functionality
- [ ] Works on iOS Safari
- [ ] Works on Chrome Android
- [ ] Touch targets 44x44px minimum
- [ ] No zoom on input focus
- [ ] Smooth scrolling
- [ ] Landscape mode functional

### PWA Features
- [ ] Installable from browser
- [ ] Offline mode shows cached content
- [ ] Push notifications work
- [ ] App icon appears correctly
- [ ] Splash screen displays
- [ ] Status bar styled correctly

### Performance
- [ ] First load < 3s on 4G
- [ ] Subsequent loads < 1s
- [ ] Smooth 60fps scrolling
- [ ] No jank during typing
- [ ] Images optimized for mobile

### Accessibility
- [ ] VoiceOver/TalkBack compatible
- [ ] Sufficient color contrast
- [ ] Text readable at default size
- [ ] Respects reduced motion
- [ ] Keyboard navigation works