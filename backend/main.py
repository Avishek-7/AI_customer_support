from fastapi import FastAPI, Request, Response
from api import auth
from api import chat
from api import documents
from api import users
from api import admin
from api import vectors
from core.database import Base, engine
from fastapi.middleware.cors import CORSMiddleware
from utils.logger import init_logging, get_logger, set_request_id, clear_request_id
from utils.metrics import REQUEST_LATENCY, render_metrics
import uuid
import time

# Initialize logging
init_logging()
logger = get_logger("backend.main")

app = FastAPI(
    title="AI Customer Support Backend"
)

# CORS middleware - must be added first
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://192.168.1.50:3000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Request ID middleware for request tracing
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    set_request_id(request_id)
    start_time = time.perf_counter()
    
    logger.info(f"Request started", extra={
        "method": request.method,
        "path": request.url.path,
        "request_id": request_id
    })
    try:
        response = await call_next(request)
        duration = time.perf_counter() - start_time
        
        # Use route template pattern (e.g., /documents/{doc_id}) to avoid cardinality explosion
        route = request.scope.get("route")
        path_template = route.path if route else request.url.path
        REQUEST_LATENCY.labels(path_template, request.method, str(response.status_code)).observe(duration)
        
        logger.info(f"Request completed", extra={
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "request_id": request_id
        })
        return response
    except Exception as e:
        duration = time.perf_counter() - start_time
        
        # Use route template pattern for error metrics
        route = request.scope.get("route")
        path_template = route.path if route else request.url.path
        REQUEST_LATENCY.labels(path_template, request.method, "500").observe(duration)
        
        logger.error(f"Request failed", extra={"error": str(e), "request_id": request_id})
        raise
    finally:
        clear_request_id()

@app.get("/metrics")
async def metrics_endpoint():
    data, content_type = render_metrics()
    return Response(content=data, media_type=content_type)

# Routes
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(admin.router)
app.include_router(vectors.router)
app.include_router(users.router)

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker/Kubernetes."""
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    # Create database tables asynchronously
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created and backend server started")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Backend server shutting down")

