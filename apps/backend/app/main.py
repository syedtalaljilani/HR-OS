from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.routes import applications as applications_routes
from app.api.routes import audit as audit_routes
from app.api.routes import auth as auth_routes
from app.api.routes import candidates as candidates_routes
from app.api.routes import emails as emails_routes
from app.api.routes import jobs as jobs_routes
from app.api.routes import public as public_routes
from app.api.routes import talent_pool as talent_pool_routes
from app.api.routes import users as users_routes
from app.db.session import get_db

app = FastAPI(
    title="HR Recruitment OS API",
    description="AI-assisted HR Recruitment System",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(users_routes.router)
app.include_router(jobs_routes.router)
app.include_router(public_routes.router)
app.include_router(applications_routes.router)
app.include_router(candidates_routes.router)
app.include_router(talent_pool_routes.router)
app.include_router(emails_routes.router)
app.include_router(audit_routes.router)


@app.get("/")
async def root():
    return {
        "name": "HR Recruitment OS API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "backend",
    }

@app.get("/health/db")
async def database_health(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1"))
    
    return {
        "database": "connected",
        "result": result.scalar(),
    }