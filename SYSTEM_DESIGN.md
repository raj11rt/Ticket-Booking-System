# Ticket Booking System - System Design

This document details the core architectural mechanisms implemented in the Ticket Booking System to handle high-demand events, concurrent transactions, seat hold timeouts, and automated waitlist management.

---

## 1. Seat Hold & TTL Mechanism

To prevent seat hoarding, the system implements a short-lived **Seat Hold** protocol with a configurable Time-To-Live (TTL) (default: 10 minutes) during checkout.

```
[Available Seat] 
      │ (Customer selects seat)
      ▼
[Seat Status: Held] ──► (Create SeatHold entry with expires_at = now() + 10 mins)
      │
      ├─► (Checkout Completed) ──────► [Seat Status: Booked]
      │
      └─► (TTL Expiry / Abandon) ───► [Seat Status: Available]
```

### Expiry Enforcements:
1. **Active Background Worker**: An `APScheduler` job runs every 10 seconds. It queries `SeatHold` records where `expires_at < CURRENT_TIMESTAMP`, reverts corresponding `ShowSeat` statuses to `"available"`, increments their `version` column, and deletes the expired holds.
2. **On-Demand Expiry Check**: Before loading the seat map (`GET /shows/{id}/seats`) or attempting to hold new seats (`POST /shows/{id}/seats/hold`), the backend executes `release_expired_holds()`. This ensures that even if the background worker hasn't run yet, users instantly get accurate availability.

---

## 2. Concurrency Protection (Seat Collision Prevention)

High-demand events lead to simultaneous select/hold attempts for the same seats. To ensure only one user succeeds, we implement **Optimistic Concurrency Control (OCC)** at the database level.

### Database Design:
The `show_seats` table includes a `version` column (integer).

### Concurrency Flow:
1. **Read phase**: The backend queries the seat status and version:
   ```sql
   SELECT id, status, version FROM show_seats WHERE id = :seat_id;
   ```
2. **Validation**: The system verifies `status == 'available'`.
3. **Write phase (Atomic Update)**: The system attempts to update the seat status conditional on the version matching the read version:
   ```sql
   UPDATE show_seats 
   SET status = 'held', version = version + 1 
   WHERE id = :seat_id AND status = 'available' AND version = :read_version;
   ```
4. **Collision Resolution**: 
   - If the update affects `1` row, the hold is successful and the transaction commits.
   - If the update affects `0` rows, another transaction modified the seat in the interim. The current transaction immediately rolls back, raising a `409 Conflict` HTTP exception.

This approach is highly performant, lock-free, prevents deadlocks, and is database-independent (works seamlessly with SQLite and PostgreSQL).

---

## 3. Waitlist Queue & Auto-Assignment Flow

When all seats in a category (e.g. *Premium*, *Standard*) for a show are sold out, customers can join a waitlist queue (`waitlist_entries` table).

```
[Booking Cancelled] 
      │
      ▼
(Query waitlist_entries for 'waiting' status, sorted by position ASC)
      │
      ├──► [No entries] ──► (Mark seat as Available)
      │
      └──► [Entry Found] ─► (Mark seat as Held for user; set 5-minute offer TTL)
                            (Send waitlist offer email with claim URL)
```

### Auto-Assignment Algorithm:
1. When a customer cancels a booking, `cancel_booking()` marks the booking as `"cancelled"`.
2. The service queries the `waitlist_entries` for the next user with status `"waiting"` for that specific show and seat category, ordered by `position` ASC.
3. If an entry is found, the released seat status remains `"held"`, a `SeatHold` record is created for the waitlisted customer, and the waitlist status changes to `"offered"` with a 5-minute expiry link.
4. An email containing a claim link is dispatched.

---

## 4. Time-Limited Offer Handling

Waitlist offers must expire to prevent deadlocks if a customer ignores their offer.

- When an offer is made, `offer_expires_at` is set to `now() + 5 minutes`.
- The `APScheduler` checks for expired offers every 10 seconds.
- If an offer expires unclaimed:
  1. The waitlist entry status is updated to `"expired"`.
  2. The `SeatHold` is deleted.
  3. `process_seat_release()` is recursively triggered to immediately offer the seat to the *next* customer in line.
- To claim the offer, the user clicks the link, holds the seat, and submits checkout. The endpoint `POST /bookings` verifies the claim is active, converts the seat to `"booked"`, and marks the waitlist entry as `"converted"`.

---

## 5. Two-Step Verification (OTP Authentication) Flow

To prevent unauthorized access to user accounts, the system implements a secure Two-Factor Authentication (2FA) login process:

```
[User Login Attempt]
         │ (Submits credentials)
         ▼
(Validate password hash) ──► [Fail] ──► (Raise 401 Unauthorized)
         │
         ├──► [Success] ──► (Generate 6-digit OTP code)
                            (Upsert code + 5-minute TTL to user_otps table)
                            (Send OTP email & log verification code)
                            (Response: otp_required = True)
                                  │
                                  ▼
                     [User enters OTP on frontend]
                                  │
                                  ▼
                     (Verify OTP matches user_otps code & is not expired)
                                  │
                                  ├──► [Fail] ──► (Raise 400 Bad Request)
                                  │
                                  └──► [Success] ──► (Delete OTP record from DB)
                                                     (Generate & return JWT token)
```
- **Cryptographic Randomness**: The OTP is a random 6-digit integer string generated via Python's standard `random` library.
- **Short-Lived Expiry (TTL)**: Active OTPs are valid for only 5 minutes.
- **Single-Use Enforcement**: Upon successful verification, the database record is deleted immediately.
- **Graceful Resend**: The frontend features a 30-second cooldown timer on the resend button to throttle repeated verification emails.

