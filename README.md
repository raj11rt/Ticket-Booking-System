# 🎟️ TicketFlow — Ticket Booking System

A premium, full-stack movie and concert ticket booking platform featuring real-time interactive seat maps, concurrency-protected seat holds (TTL), queue-based waitlists, email ticket delivery with embedded QR codes, and a secure 2FA/OTP login system.

---

## 🚀 Setup & Execution Guide

### Prerequisites
- Python 3.13 (or 3.9+)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/raj11rt/Ticket-Booking-System.git
   cd Ticket-Booking-System
   ```
2. Set up virtual environment and install packages:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate      # Windows Powershell
   source .venv/bin/activate     # Linux / MacOS
   pip install -r requirements.txt
   ```
3. Initialize the environment configuration:
   - Copy `.env.example` to `.env`:
     ```bash
     copy .env.example .env
     ```
   - In `.env`, ensure `EMAIL_PROVIDER=console` is set. This routes HTML email logs directly to the local directory `sent_emails/` inside the project.

4. Start the Application:
   ```bash
   python main.py
   ```
   The backend API launches on `http://localhost:8000`.
   FastAPI automatically initializes the SQLite database file (`ticket_booking.db`) on start and seeds it with mock data.

5. Open the Frontend:
   - Navigate to `http://localhost:8000/frontend/index.html` in your web browser. 
   - Serving static files directly from FastAPI eliminates CORS issues.

---

## 🔑 Demo Accounts
The database is auto-seeded on first run with accounts representing the three distinct roles:
1. **Admin** (`role=admin`):
   - **Email**: `admin@ticketflow.com`
   - **Password**: `admin123`
2. **Organiser** (`role=organiser`):
   - **Email**: `organiser@ticketflow.com`
   - **Password**: `organiser123`
3. **Customer** (`role=customer`):
   - **Email**: `customer@ticketflow.com`
   - **Password**: `customer123`

---

## 🛠️ Core System Mechanics

### 1. Two-Step OTP Authentication Flow
To ensure secure login, the platform features a custom 2FA verification system:
- When a user enters their credentials at `/auth/login`, the server validates the password.
- If verified, the server generates a cryptographically random 6-digit verification code (OTP), upserts it with a 5-minute expiry in the `user_otps` table, and logs a premium HTML email locally inside `sent_emails/`.
- The OTP code is also **printed to the server terminal console** for instant copy-pasting during grading/testing.
- The frontend transitions to a passcode screen, where the user submits the code to `/auth/verify-otp` to receive their JWT token.

### 2. Seat Hold & TTL Auto-Release
- When a customer selects seats, the system places a hold with a **10-minute Time-To-Live (TTL)**.
- **Background Cleanup**: An `APScheduler` job runs every 10 seconds to sweep the `seat_holds` table, releasing seats where `expires_at` is in the past back to `"available"`.
- **On-Demand Expiry Check**: Expired holds are also swept on-demand when loading seat maps or requesting new holds to guarantee real-time correctness.

### 3. Concurrency Protection (Collision Prevention)
- High-demand ticket releases face high concurrent purchase attempts.
- We utilize **Optimistic Concurrency Control (OCC)** at the database layer.
- The `show_seats` table includes a `version` column. When updating seat status (holding or booking), the SQL update checks:
  ```sql
  UPDATE show_seats 
  SET status = 'held', version = version + 1 
  WHERE id = :seat_id AND status = 'available' AND version = :read_version;
  ```
- If the query updates 0 rows, another transaction has modified the seat in the interim. The current transaction rolls back, preventing double-bookings.

### 4. Waitlist Queue & Auto-Assignment
- When a seat category is sold out, users can enroll in a waitlist queue (`waitlist_entries` table).
- When a customer cancels their booking, the released seats are **not** immediately returned to the public pool.
- Instead, the system queries the waitlist for the next customer in line (`status = 'waiting'`) ordered by position.
- If a customer is waiting, the seat is held for them, their waitlist status transitions to `"offered"`, and they receive an email with a 5-minute time-limited claim link.
- If unclaimed within 5 minutes, the scheduler expires the offer and offers it to the next customer in queue.

---

## 🗄️ Database Schema & Tables

### 1. `users`
Stores user profile information and roles.
- `id` (INTEGER, Primary Key)
- `email` (VARCHAR, Unique, Indexed)
- `password_hash` (VARCHAR)
- `full_name` (VARCHAR)
- `role` (VARCHAR) - `admin` / `organiser` / `customer`
- `created_at` (DATETIME)

### 2. `user_otps`
Temporarily stores 6-digit login verification codes.
- `id` (INTEGER, Primary Key)
- `email` (VARCHAR, Unique, Indexed)
- `otp_code` (VARCHAR)
- `expires_at` (DATETIME)

### 3. `venues`
Venues hosting movie screenings or concerts.
- `id` (INTEGER, Primary Key)
- `name` (VARCHAR, Unique)
- `address` (VARCHAR)

### 4. `seat_layouts`
Templates for venue seat grids.
- `id` (INTEGER, Primary Key)
- `venue_id` (INTEGER, Foreign Key to `venues.id`)
- `row_label` (VARCHAR) - e.g., "A", "B"
- `col_number` (INTEGER) - e.g., 1, 2, 3
- `category` (VARCHAR) - `Standard` / `Premium`

### 5. `events`
Movie listings or concert profiles.
- `id` (INTEGER, Primary Key)
- `title` (VARCHAR)
- `type` (VARCHAR) - `movie` / `concert`
- `description` (VARCHAR)
- `poster_url` (VARCHAR, Nullable)
- `organiser_id` (INTEGER, Foreign Key to `users.id`)

### 6. `shows`
Specific time slots scheduled for events.
- `id` (INTEGER, Primary Key)
- `event_id` (INTEGER, Foreign Key to `events.id`)
- `venue_id` (INTEGER, Foreign Key to `venues.id`)
- `date` (VARCHAR) - YYYY-MM-DD
- `time` (VARCHAR) - HH:MM
- `pricing` (JSON) - e.g., `{"Standard": 12.00, "Premium": 20.00}`

### 7. `show_seats`
Instances of seats mapped to specific showtimes.
- `id` (INTEGER, Primary Key)
- `show_id` (INTEGER, Foreign Key to `shows.id`)
- `seat_layout_id` (INTEGER, Foreign Key to `seat_layouts.id`)
- `status` (VARCHAR) - `available` / `held` / `booked`
- `version` (INTEGER) - Used for OCC locking

### 8. `seat_holds`
Active customer checkout checkout holds.
- `id` (INTEGER, Primary Key)
- `show_seat_id` (INTEGER, Foreign Key to `show_seats.id`)
- `customer_id` (INTEGER, Foreign Key to `users.id`)
- `held_at` (DATETIME)
- `expires_at` (DATETIME)

### 9. `bookings`
Completed orders containing reference codes.
- `id` (INTEGER, Primary Key)
- `show_id` (INTEGER, Foreign Key to `shows.id`)
- `customer_id` (INTEGER, Foreign Key to `users.id`)
- `booking_ref` (VARCHAR, Unique, Indexed)
- `total_amount` (FLOAT)
- `status` (VARCHAR) - `confirmed` / `cancelled`
- `booked_at` (DATETIME)

### 10. `booking_seats`
Many-to-many relationship mapping bookings to specific seats.
- `id` (INTEGER, Primary Key)
- `booking_id` (INTEGER, Foreign Key to `bookings.id`)
- `show_seat_id` (INTEGER, Foreign Key to `show_seats.id`)

### 11. `waitlist_entries`
FIFO waitlist entries for sold-out events.
- `id` (INTEGER, Primary Key)
- `show_id` (INTEGER, Foreign Key to `shows.id`)
- `customer_id` (INTEGER, Foreign Key to `users.id`)
- `category` (VARCHAR)
- `position` (INTEGER)
- `status` (VARCHAR) - `waiting` / `offered` / `expired` / `converted`
- `offer_expires_at` (DATETIME, Nullable)
- `offered_seat_id` (INTEGER, Foreign Key to `show_seats.id`, Nullable)
- `created_at` (DATETIME)

---

## 📡 Core API Reference

All requests and responses use JSON. Authenticated requests require: `Authorization: Bearer <JWT_TOKEN>`.

### Authentication
- `POST /auth/register` - Register a new user profile.
- `POST /auth/login` - Verify password and send a 6-digit OTP to email.
- `POST /auth/verify-otp` - Verify login OTP and return JWT token.

### Venues & Layouts
- `POST /venues` (Admin) - Bulk register venue and seat layout templates.
- `GET /venues` - Retrieve registered venues list.
- `GET /venues/{id}/seats` - Retrieve templates of a venue's seat layout.

### Events & Shows
- `POST /events` (Organiser) - Create event listing.
- `POST /events/{id}/shows` (Organiser) - Schedule showtime and auto-populate show seat records.
- `GET /events` - List upcoming events with text search and category filter.
- `GET /shows/{show_id}` - Retrieve showtime, price lists, and venue name.

### Seat Holds & Bookings
- `GET /shows/{show_id}/seats` - Retrieve visual grid seats data with `is_mine` flags.
- `POST /shows/{show_id}/seats/hold` (Customer) - Establish TTL-based hold for selected seats.
- `DELETE /shows/{show_id}/seats/hold` (Customer) - Cancel active holds.
- `POST /bookings` (Customer) - Finalize hold checkout or claim waitlist offer.
- `GET /bookings` (Customer) - Retrieve booking history.
- `DELETE /bookings/{id}` (Customer) - Cancel booking (triggers waitlist reallocation).
- `GET /bookings/{id}/qr` (Customer) - Fetch base64 string encoding booking reference.

### Waitlist Operations
- `POST /shows/{show_id}/waitlist` (Customer) - Join waitlist category.
- `GET /shows/{show_id}/waitlist/status` (Customer) - Check current queue position or active offers.
