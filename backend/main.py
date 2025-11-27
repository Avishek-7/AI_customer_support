from fastapi import FastAPI
from api import auth
from core.database import Base, engine

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Customer Support Backend"
)

# Routes
app.include_router(auth.router)