import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app.services.seat_hold import release_expired_holds
from app.services.waitlist import expire_waitlist_offers

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def run_cleanup_jobs():
    """
    Job that runs periodically to release expired holds and expire waitlist offers.
    """
    db = SessionLocal()
    try:
        # 1. Release expired seat holds
        release_expired_holds(db)
        
        # 2. Expire waitlist offers and cycle them
        expire_waitlist_offers(db)
    except Exception as e:
        logger.error(f"Error running scheduler cleanup jobs: {e}")
    finally:
        db.close()

def start_scheduler():
    if not scheduler.running:
        # Run every 10 seconds for real-time responsiveness in tests/demo
        scheduler.add_job(run_cleanup_jobs, "interval", seconds=10, id="cleanup_job")
        scheduler.start()
        logger.info("⏰ APScheduler started successfully.")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("⏰ APScheduler shutdown successfully.")
