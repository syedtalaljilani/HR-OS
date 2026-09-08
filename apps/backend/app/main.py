from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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