"""
Simplified SQLite version for testing without Docker
"""

import asyncio
import json
import uuid
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from fastapi import Depends
from fastapi import FastAPI
from fastapi import Form
from fastapi import HTTPException
from fastapi import status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from jose import JWTError
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker
from sse_starlette import EventSourceResponse

# Import Claude bridge for real Claude integration
try:
    from .claude_bridge import claude_bridge

    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    claude_bridge = None  # type: ignore
    print("Warning: Claude Code SDK not available, using mock responses")

# SQLite database
DATABASE_URL = "sqlite:///./claude_web.db"
SECRET_KEY = "dev-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

# Database setup
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()


# Database models
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatSession(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String)
    role = Column(String)
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)


# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(title="Claude Web Interface")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


# Pydantic models
class UserCreate(BaseModel):
    username: str
    email: str | None = None
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Auth helpers
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


# Mock Claude response for when SDK is not available
async def mock_claude_response(prompt: str):
    """Mock Claude response for testing without Claude Code SDK"""
    response_parts = [
        "I'm a mock Claude response. ",
        "The actual Claude Code SDK would provide real responses here. ",
        f"You said: {prompt[:100]}... ",
        "The interface is working correctly!",
    ]

    for part in response_parts:
        await asyncio.sleep(0.1)  # Simulate streaming delay
        yield part


# Routes
@app.get("/app.js")
async def serve_app_js():
    """Serve the app.js file"""
    js_path = frontend_path / "app.js"
    if js_path.exists():
        return FileResponse(js_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found")


@app.get("/manifest.json")
async def serve_manifest():
    """Serve the manifest.json file"""
    manifest_path = frontend_path / "manifest.json"
    if manifest_path.exists():
        return FileResponse(manifest_path, media_type="application/json")
    raise HTTPException(status_code=404, detail="manifest.json not found")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main page"""
    html_path = frontend_path / "index.html"
    if html_path.exists():
        return html_path.read_text()
    return """
    <html>
        <head><title>Claude Web</title></head>
        <body>
            <h1>Claude Web Interface</h1>
            <p>Frontend files not found. Please check the installation.</p>
        </body>
    </html>
    """


@app.post("/register")
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Create new user
    user = User(username=user_data.username, hashed_password=get_password_hash(user_data.password))
    db.add(user)
    db.commit()

    # Return success (frontend will auto-login)
    return {"username": user.username, "id": user.id}


@app.post("/token", response_model=Token)
async def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Login with form data (OAuth2 compatible)"""
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token)


@app.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {"id": current_user.id, "username": current_user.username, "created_at": current_user.created_at.isoformat()}


@app.get("/conversations")
async def get_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's conversations with titles and message counts"""
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.last_active.desc())
        .all()
    )

    result = []
    for session in sessions:
        # Get message count for this conversation
        message_count = db.query(Message).filter(Message.session_id == session.id).count()

        # Get first user message for title (or use default)
        first_message = (
            db.query(Message)
            .filter(Message.session_id == session.id, Message.role == "user")
            .order_by(Message.timestamp)
            .first()
        )

        # Generate title from first message or use default
        title = "New Conversation"
        if first_message:
            content: str = str(first_message.content)  # type: ignore
            if content:
                # Take first 50 chars of first message as title
                title = content[:50]
                if len(content) > 50:
                    title += "..."

        result.append(
            {
                "id": session.id,
                "title": title,
                "message_count": message_count,
                "created_at": session.created_at.isoformat(),
                "last_active": session.last_active.isoformat(),
            }
        )

    return result


@app.post("/conversations")
async def create_conversation(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new conversation"""
    session = ChatSession(user_id=current_user.id)
    db.add(session)
    db.commit()
    return {"id": session.id, "created_at": session.created_at.isoformat()}


@app.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get messages for a conversation"""
    # Verify session belongs to user
    session = (
        db.query(ChatSession).filter(ChatSession.id == conversation_id, ChatSession.user_id == current_user.id).first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.query(Message).filter(Message.session_id == conversation_id).order_by(Message.timestamp).all()

    return [{"id": m.id, "role": m.role, "content": m.content, "created_at": m.timestamp.isoformat()} for m in messages]


@app.post("/chat/stream")
async def chat_stream(
    request: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Stream chat responses"""
    # Get or create conversation
    conversation_id = request.conversation_id
    if not conversation_id:
        session = ChatSession(user_id=current_user.id)
        db.add(session)
        db.commit()
        conversation_id = session.id
    else:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == conversation_id, ChatSession.user_id == current_user.id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Conversation not found")
        session.last_active = datetime.now(UTC)  # type: ignore
        db.commit()

    # Save user message
    user_message = Message(session_id=conversation_id, role="user", content=request.message)
    db.add(user_message)
    db.commit()

    # Get conversation history for context - increased to 50 messages for better context
    history = (
        db.query(Message).filter(Message.session_id == conversation_id).order_by(Message.timestamp).limit(50).all()
    )

    conversation_history = [
        {"role": m.role, "content": m.content}
        for m in history[:-1]  # Exclude the current message we just added
    ]

    async def generate():
        """Generate SSE stream"""
        # Send conversation ID first if new
        if not request.conversation_id:
            yield {"event": "message", "data": json.dumps({"id": conversation_id})}

        full_response = ""

        # Use real Claude Code SDK if available, otherwise mock
        if CLAUDE_AVAILABLE:
            try:
                async for chunk in claude_bridge.stream_response(request.message, conversation_history):  # type: ignore
                    full_response += chunk
                    yield {"event": "message", "data": json.dumps({"content": chunk})}
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                full_response = error_msg
                yield {"event": "message", "data": json.dumps({"content": error_msg})}
        else:
            # Use mock response
            async for chunk in mock_claude_response(request.message):
                full_response += chunk
                yield {"event": "message", "data": json.dumps({"content": chunk})}

        # Save assistant message
        if full_response:
            assistant_message = Message(session_id=conversation_id, role="assistant", content=full_response)
            db.add(assistant_message)
            db.commit()

        # Send completion event
        yield {"event": "done", "data": json.dumps({"conversation_id": conversation_id})}

    return EventSourceResponse(generate())


@app.post("/chat")
async def chat_non_streaming(
    request: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Non-streaming chat endpoint"""
    # Get or create conversation
    conversation_id = request.conversation_id
    if not conversation_id:
        session = ChatSession(user_id=current_user.id)
        db.add(session)
        db.commit()
        conversation_id = session.id
    else:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == conversation_id, ChatSession.user_id == current_user.id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Conversation not found")
        session.last_active = datetime.now(UTC)  # type: ignore
        db.commit()

    # Save user message
    user_message = Message(session_id=conversation_id, role="user", content=request.message)
    db.add(user_message)
    db.commit()

    # Get conversation history for context
    history = (
        db.query(Message).filter(Message.session_id == conversation_id).order_by(Message.timestamp).limit(50).all()
    )

    conversation_history = [
        {"role": m.role, "content": m.content}
        for m in history[:-1]  # Exclude the current message we just added
    ]

    # Generate response
    full_response = ""

    if CLAUDE_AVAILABLE:
        try:
            # Use non-streaming method if available
            full_response = await claude_bridge.get_response(request.message, conversation_history)  # type: ignore
        except Exception as e:
            full_response = f"Error: {str(e)}"
    else:
        # Mock response for testing
        full_response = (
            f"This is a mock response to your message: '{request.message[:100]}...'. "
            f"The real Claude Code SDK would provide actual responses here."
        )

    # Save assistant message
    if full_response:
        assistant_message = Message(session_id=conversation_id, role="assistant", content=full_response)
        db.add(assistant_message)
        db.commit()

    return {"conversation_id": conversation_id, "response": full_response}


# Keep the old endpoints for backward compatibility but they're not used by frontend
@app.get("/api/sessions")
async def get_sessions_legacy(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Legacy endpoint - use /conversations instead"""
    return await get_conversations(current_user, db)


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "sqlite",
        "claude_sdk": CLAUDE_AVAILABLE,
        "mock_mode": not CLAUDE_AVAILABLE,
    }


if __name__ == "__main__":
    import uvicorn

    # Create a default user for testing
    db = SessionLocal()
    default_user = db.query(User).filter(User.username == "test").first()
    if not default_user:
        user = User(username="test", hashed_password=get_password_hash("test123"))
        db.add(user)
        db.commit()
        print("Created default user: username='test', password='test123'")
    db.close()

    print("Starting Claude Web Interface (SQLite/Mock Mode)")
    print("Access at: http://localhost:8000")
    print("Default login: username='test', password='test123'")

    uvicorn.run(app, host="0.0.0.0", port=8000)
