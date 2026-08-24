import datetime
from sqlalchemy.orm import Session
from app.models.models import User, Venue, SeatLayout, Event, Show, ShowSeat
from app.auth.utils import hash_password

def seed_data(db: Session):
    """
    Seeds the database with sample data if it is empty.
    Creates default Admin, Organiser, and Customer accounts,
    two venues with seat layouts, multiple events, and scheduled shows.
    """
    # 1. Check if database has users. If not, seed.
    if db.query(User).first() is not None:
        return  # Database is already populated
        
    print("[SEED] Database is empty. Seeding sample demo data...")

    # Create default accounts
    admin = User(
        email="admin@ticketflow.com",
        password_hash=hash_password("admin123"),
        full_name="Alex Administrator",
        role="admin"
    )
    organiser = User(
        email="organiser@ticketflow.com",
        password_hash=hash_password("organiser123"),
        full_name="Olivia Organiser",
        role="organiser"
    )
    customer = User(
        email="customer@ticketflow.com",
        password_hash=hash_password("customer123"),
        full_name="Charlie Customer",
        role="customer"
    )
    
    db.add_all([admin, organiser, customer])
    db.commit()
    db.refresh(organiser)
    
    # 2. Create Venues and Seat Layouts
    # Venue 1: Grand IMAX Cinema (40 seats)
    venue1 = Venue(name="Grand IMAX Cinema", address="101 Cinema Boulevard, Downtown")
    db.add(venue1)
    db.commit()
    db.refresh(venue1)
    
    seats1 = []
    for r_idx in range(5):
        row_label = chr(65 + r_idx)  # A, B, C, D, E
        category = "Premium" if r_idx < 2 else "Standard"
        for col in range(1, 9):
            seats1.append(SeatLayout(
                venue_id=venue1.id,
                row_label=row_label,
                col_number=col,
                category=category
            ))
    db.bulk_save_objects(seats1)
    db.commit()
    
    # Venue 2: Royal Symphony Hall (60 seats)
    venue2 = Venue(name="Royal Symphony Hall", address="20 Broadway Avenue, Theater District")
    db.add(venue2)
    db.commit()
    db.refresh(venue2)
    
    seats2 = []
    for r_idx in range(6):
        row_label = chr(65 + r_idx)  # A-F
        category = "Premium" if r_idx < 2 else "Standard"
        for col in range(1, 11):
            seats2.append(SeatLayout(
                venue_id=venue2.id,
                row_label=row_label,
                col_number=col,
                category=category
            ))
    db.bulk_save_objects(seats2)
    db.commit()

    # Venue 3: Cineplex Multiplex (48 seats)
    venue3 = Venue(name="Cineplex Multiplex Hall 5", address="500 Westside Mall, Level 2")
    db.add(venue3)
    db.commit()
    db.refresh(venue3)

    seats3 = []
    for r_idx in range(6):
        row_label = chr(65 + r_idx)  # A-F
        category = "Premium" if r_idx < 2 else "Standard"
        for col in range(1, 9):
            seats3.append(SeatLayout(
                venue_id=venue3.id,
                row_label=row_label,
                col_number=col,
                category=category
            ))
    db.bulk_save_objects(seats3)
    db.commit()

    # 3. Create Events
    event1 = Event(
        title="Inception (10th Anniversary Re-Release)",
        type="movie",
        description="A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O., but his tragic past may doom the project and his team.",
        poster_url="/frontend/images/inception.png",
        organiser_id=organiser.id
    )
    event2 = Event(
        title="Coldplay: Music of the Spheres World Tour",
        type="concert",
        description="Experience the spectacular live concert of Coldplay featuring lasers, fireworks, giant interactive LED wristbands, and the biggest light show ever assembled on a stadium stage.",
        poster_url="/frontend/images/coldplay.png",
        organiser_id=organiser.id
    )
    event3 = Event(
        title="Dune: Part Two — IMAX Premiere",
        type="movie",
        description="Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family. Facing a choice between the love of his life and the fate of the universe, he must prevent a terrible future only he can foresee.",
        poster_url="/frontend/images/dune.png",
        organiser_id=organiser.id
    )
    event4 = Event(
        title="Taylor Swift: The Eras Tour — Live Concert Film",
        type="concert",
        description="Relive the magic of Taylor Swift's record-breaking Eras Tour concert film, now in theaters. A breathtaking three-hour journey through her entire musical catalog, featuring dazzling costumes, stunning visuals, and unforgettable performances.",
        poster_url="/frontend/images/taylor_swift.png",
        organiser_id=organiser.id
    )
    event5 = Event(
        title="Oppenheimer — Director's Cut Screening",
        type="movie",
        description="The story of J. Robert Oppenheimer's role in the development of the atomic bomb during World War II. Christopher Nolan's stunning IMAX epic explores the triumph and tragedy of the father of the atomic bomb.",
        poster_url="/frontend/images/oppenheimer.png",
        organiser_id=organiser.id
    )
    event6 = Event(
        title="AR Rahman: Jai Ho Live Concert",
        type="concert",
        description="Grammy and Oscar-winning composer AR Rahman performs live in an electrifying fusion of Bollywood, Western classical, and electronic music — an evening that transcends genres and unites generations in pure musical bliss.",
        poster_url=None,
        organiser_id=organiser.id
    )
    event7 = Event(
        title="The Dark Knight — IMAX 4K Restoration",
        type="movie",
        description="Batman, Commissioner Gordon and District Attorney Harvey Dent mount an effort to dismantle organized crime. Their plan is disrupted by the Joker, a criminal mastermind who seeks to create anarchy in Gotham. The definitive superhero epic, now in stunning 4K IMAX.",
        poster_url=None,
        organiser_id=organiser.id
    )

    db.add_all([event1, event2, event3, event4, event5, event6, event7])
    db.commit()
    db.refresh(event1)
    db.refresh(event2)
    db.refresh(event3)
    db.refresh(event4)
    db.refresh(event5)
    db.refresh(event6)
    db.refresh(event7)

    # 4. Schedule Shows
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    day2 = today + datetime.timedelta(days=2)
    day3 = today + datetime.timedelta(days=3)
    day4 = today + datetime.timedelta(days=4)
    day5 = today + datetime.timedelta(days=5)
    
    shows = [
        Show(event_id=event1.id, venue_id=venue1.id, date=today.strftime("%Y-%m-%d"),     time="18:30", pricing={"Premium": 20.0, "Standard": 12.0}),
        Show(event_id=event2.id, venue_id=venue2.id, date=tomorrow.strftime("%Y-%m-%d"),  time="20:00", pricing={"Premium": 150.0, "Standard": 80.0}),
        Show(event_id=event3.id, venue_id=venue1.id, date=day2.strftime("%Y-%m-%d"),      time="17:00", pricing={"Premium": 25.0, "Standard": 15.0}),
        Show(event_id=event4.id, venue_id=venue2.id, date=day2.strftime("%Y-%m-%d"),      time="19:30", pricing={"Premium": 120.0, "Standard": 70.0}),
        Show(event_id=event5.id, venue_id=venue3.id, date=day3.strftime("%Y-%m-%d"),      time="20:30", pricing={"Premium": 22.0, "Standard": 14.0}),
        Show(event_id=event6.id, venue_id=venue2.id, date=day4.strftime("%Y-%m-%d"),      time="19:00", pricing={"Premium": 200.0, "Standard": 100.0}),
        Show(event_id=event7.id, venue_id=venue1.id, date=day5.strftime("%Y-%m-%d"),      time="21:00", pricing={"Premium": 18.0, "Standard": 10.0}),
        # Additional showtimes
        Show(event_id=event1.id, venue_id=venue3.id, date=tomorrow.strftime("%Y-%m-%d"),  time="14:00", pricing={"Premium": 20.0, "Standard": 12.0}),
        Show(event_id=event3.id, venue_id=venue3.id, date=day3.strftime("%Y-%m-%d"),      time="15:30", pricing={"Premium": 25.0, "Standard": 15.0}),
    ]
    
    db.add_all(shows)
    db.commit()
    for s in shows:
        db.refresh(s)

    # 5. Populate Show Seats
    layout_seats1 = db.query(SeatLayout).filter(SeatLayout.venue_id == venue1.id).all()
    layout_seats2 = db.query(SeatLayout).filter(SeatLayout.venue_id == venue2.id).all()
    layout_seats3 = db.query(SeatLayout).filter(SeatLayout.venue_id == venue3.id).all()

    venue_layout_map = {venue1.id: layout_seats1, venue2.id: layout_seats2, venue3.id: layout_seats3}

    all_show_seats = []
    for show in shows:
        layout = venue_layout_map[show.venue_id]
        for lay in layout:
            all_show_seats.append(ShowSeat(show_id=show.id, seat_layout_id=lay.id, status="available", version=1))

    db.bulk_save_objects(all_show_seats)
    db.commit()
    
    print("[SEED] Database successfully seeded with 7 events, 9 shows, 3 venues, and demo accounts!")
