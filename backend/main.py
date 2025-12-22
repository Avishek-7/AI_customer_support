from fastapi import FastAPI, Request
from api import auth
from api import chat
from api import documents
from api import admin
from api import vectors
from core.database import Base, engine
from fastapi.middleware.cors import CORSMiddleware
from utils.logger import init_logging, get_logger, set_request_id, clear_request_id
import uuid

# Initialize logging
init_logging()
logger = get_logger("backend.main")

# Create database tables
Base.metadata.create_all(bind=engine)
logger.info("Database tables created")

app = FastAPI(
    title="AI Customer Support Backend"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID middleware for request tracing
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    set_request_id(request_id)
    logger.info(f"Request started", extra={
        "method": request.method,
        "path": request.url.path,
        "request_id": request_id
    })
    try:
        response = await call_next(request)
        logger.info(f"Request completed", extra={
            "status_code": response.status_code,
            "request_id": request_id
        })
        return response
    except Exception as e:
        logger.error(f"Request failed", extra={"error": str(e), "request_id": request_id})
        raise
    finally:
        clear_request_id()

# Routes
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(admin.router)
app.include_router(vectors.router)

@app.on_event("startup")
async def startup_event():
    logger.info("Backend server started")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Backend server shutting down")

