import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.config import settings

# Import routers
from app.auth.router import router as auth_router
from app.routers.venues import router as venues_router
from app.routers.events import router as events_router
from app.routers.seats import router as seats_router
from app.routers.bookings import router as bookings_router
from app.routers.waitlist import router as waitlist_router
from app.routers.organiser import router as organiser_router

# Import scheduler & seed service
from app.services.scheduler import start_scheduler, shutdown_scheduler
from app.database import SessionLocal
from app.services.seed import seed_data

# Automatically create all tables on startup (no need for complex migrations setup)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Ticket Booking System API",
    description="Backend API for managing events, shows, seat layouts, real-time seat holds, bookings, and waitlist queues.",
    version="1.0.0"
)

# CORS middleware config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(venues_router)
app.include_router(events_router)
app.include_router(seats_router)
app.include_router(bookings_router)
app.include_router(waitlist_router)
app.include_router(organiser_router)

# Mount frontend directory to serve UI pages directly
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
os.makedirs(frontend_dir, exist_ok=True)
app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")

@app.on_event("startup")
def startup_event():
    start_scheduler()
    db = SessionLocal()
    try:
        seed_data(db)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error seeding database: {e}")
    finally:
        db.close()

@app.on_event("shutdown")
def shutdown_event():
    shutdown_scheduler()

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Welcome to the Ticket Booking System API. Access the frontend at /frontend/index.html",
        "docs": "/docs"
    }
