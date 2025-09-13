# backend/file.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()  # loads backend/.env
app = FastAPI()

origin = os.getenv("CORS_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/events")
def events():
    return [
        {"id": 1, "title": "Food Bank Shift", "city": "NYC"},
        {"id": 2, "title": "STEM Mentor (Remote)", "city": None},
    ]
