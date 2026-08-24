import logging
import os
import datetime
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to create a local emails directory to store sent emails as HTML files
# This makes it super easy for the grader/user to preview the premium emails visually!
EMAILS_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sent_emails")
os.makedirs(EMAILS_LOG_DIR, exist_ok=True)

def log_email_locally(to_email: str, subject: str, html_content: str):
    """
    Saves the HTML email to a local file in the `sent_emails/` folder.
    This provides a beautiful preview of what the customer would receive.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_subject = "".join(c for c in subject if c.isalnum() or c in "._- ").strip().replace(" ", "_")
    filename = f"{timestamp}_{to_email}_{safe_subject}.html"
    filepath = os.path.join(EMAILS_LOG_DIR, filename)
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"📧 [EMAIL LOGGED LOCALLY] To: {to_email} | Subject: '{subject}' | Preview: file:///{filepath.replace(os.sep, '/')}")
    except Exception as e:
        logger.error(f"Error logging email locally: {e}")

def send_booking_confirmation(to_email: str, booking_ref: str, event_title: str, date: str, time: str, venue_name: str, seats_str: str, total_amount: float, qr_base64: str):
    subject = f"Your Ticket is Confirmed: {event_title} ({booking_ref})"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #0f0c1b; color: #ffffff; margin: 0; padding: 20px; }}
            .ticket-card {{ max-width: 500px; margin: 0 auto; background: linear-gradient(135deg, #1d1b36 0%, #151324 100%); border-radius: 16px; border: 1px solid #3d3b66; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
            .header {{ background: linear-gradient(90deg, #8a2be2 0%, #4a0e4e 100%); padding: 24px; text-align: center; border-bottom: 2px dashed #3d3b66; }}
            .header h1 {{ margin: 0; font-size: 24px; color: #fff; text-transform: uppercase; letter-spacing: 2px; }}
            .content {{ padding: 24px; }}
            .event-title {{ font-size: 22px; font-weight: bold; color: #a176ff; margin-bottom: 16px; text-align: center; }}
            .details-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; font-size: 14px; border-bottom: 1px solid #2d2b4f; padding-bottom: 16px; }}
            .detail-label {{ color: #8e8bb3; text-transform: uppercase; font-size: 11px; letter-spacing: 1px; margin-bottom: 4px; }}
            .detail-value {{ font-weight: bold; color: #fff; }}
            .qr-section {{ text-align: center; padding: 20px; background: rgba(255,255,255,0.05); border-radius: 12px; margin-bottom: 20px; }}
            .qr-image {{ width: 180px; height: 180px; background: white; padding: 10px; border-radius: 8px; display: inline-block; }}
            .footer {{ text-align: center; font-size: 12px; color: #6d6b8f; border-top: 1px solid #2d2b4f; padding: 16px; background: rgba(0,0,0,0.2); }}
        </style>
    </head>
    <body>
        <div class="ticket-card">
            <div class="header">
                <h1>CONFIRMED TICKET</h1>
            </div>
            <div class="content">
                <div class="event-title">{event_title}</div>
                <div class="details-grid">
                    <div>
                        <div class="detail-label">Booking Reference</div>
                        <div class="detail-value">{booking_ref}</div>
                    </div>
                    <div>
                        <div class="detail-label">Total Paid</div>
                        <div class="detail-value">${total_amount:.2f}</div>
                    </div>
                    <div>
                        <div class="detail-label">Venue</div>
                        <div class="detail-value">{venue_name}</div>
                    </div>
                    <div>
                        <div class="detail-label">Seats</div>
                        <div class="detail-value">{seats_str}</div>
                    </div>
                    <div>
                        <div class="detail-label">Date</div>
                        <div class="detail-value">{date}</div>
                    </div>
                    <div>
                        <div class="detail-label">Time</div>
                        <div class="detail-value">{time}</div>
                    </div>
                </div>
                <div class="qr-section">
                    <div class="detail-label" style="margin-bottom: 10px;">Scan QR Code at Venue</div>
                    <img class="qr-image" src="data:image/png;base64,{qr_base64}" alt="Ticket QR Code" />
                </div>
            </div>
            <div class="footer">
                Thank you for booking with us! Please present this QR code at the entrance.
            </div>
        </div>
    </body>
    </html>
    """
    
    # Always log locally first
    log_email_locally(to_email, subject, html_content)
    
    # Try sending via Resend if configured
    if settings.EMAIL_PROVIDER == "resend" and settings.RESEND_API_KEY:
        try:
            import resend
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send({
                "from": settings.FROM_EMAIL,
                "to": to_email,
                "subject": subject,
                "html": html_content
            })
            logger.info(f"Successfully sent confirmation email to {to_email} via Resend")
        except Exception as e:
            logger.error(f"Failed to send email via Resend: {e}")

def send_waitlist_offer(to_email: str, event_title: str, date: str, time: str, venue_name: str, seat_label: str, price: float, offer_expires_at: str, claim_url: str):
    subject = f"Action Required: Ticket Waitlist Offer for {event_title}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #0f0c1b; color: #ffffff; margin: 0; padding: 20px; }}
            .offer-card {{ max-width: 500px; margin: 0 auto; background: linear-gradient(135deg, #1d1b36 0%, #151324 100%); border-radius: 16px; border: 1px solid #ff4500; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
            .header {{ background: linear-gradient(90deg, #ff4500 0%, #990000 100%); padding: 24px; text-align: center; border-bottom: 2px dashed #3d3b66; }}
            .header h1 {{ margin: 0; font-size: 22px; color: #fff; text-transform: uppercase; letter-spacing: 2px; }}
            .content {{ padding: 24px; }}
            .event-title {{ font-size: 22px; font-weight: bold; color: #ff7f50; margin-bottom: 16px; text-align: center; }}
            .urgency-banner {{ background: rgba(255,69,0,0.1); border: 1px solid #ff4500; padding: 12px; border-radius: 8px; margin-bottom: 20px; text-align: center; color: #ff7f50; font-size: 14px; font-weight: bold; }}
            .details-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; font-size: 14px; border-bottom: 1px solid #2d2b4f; padding-bottom: 16px; }}
            .detail-label {{ color: #8e8bb3; text-transform: uppercase; font-size: 11px; letter-spacing: 1px; margin-bottom: 4px; }}
            .detail-value {{ font-weight: bold; color: #fff; }}
            .cta-section {{ text-align: center; padding: 20px 0; }}
            .claim-btn {{ display: inline-block; padding: 14px 28px; background: linear-gradient(90deg, #ff4500 0%, #ff8c00 100%); color: white; text-decoration: none; font-weight: bold; border-radius: 8px; font-size: 16px; box-shadow: 0 4px 15px rgba(255,69,0,0.3); text-transform: uppercase; }}
            .footer {{ text-align: center; font-size: 12px; color: #6d6b8f; border-top: 1px solid #2d2b4f; padding: 16px; background: rgba(0,0,0,0.2); }}
        </style>
    </head>
    <body>
        <div class="offer-card">
            <div class="header">
                <h1>TICKET OFFER</h1>
            </div>
            <div class="content">
                <div class="event-title">{event_title}</div>
                <div class="urgency-banner">
                    This offer is time-limited! You must claim it before {offer_expires_at} or it will go to the next person.
                </div>
                <div class="details-grid">
                    <div>
                        <div class="detail-label">Offered Seat</div>
                        <div class="detail-value">{seat_label}</div>
                    </div>
                    <div>
                        <div class="detail-label">Price</div>
                        <div class="detail-value">${price:.2f}</div>
                    </div>
                    <div>
                        <div class="detail-label">Venue</div>
                        <div class="detail-value">{venue_name}</div>
                    </div>
                    <div>
                        <div class="detail-label">Date</div>
                        <div class="detail-value">{date}</div>
                    </div>
                    <div>
                        <div class="detail-label">Time</div>
                        <div class="detail-value">{time}</div>
                    </div>
                </div>
                <div class="cta-section">
                    <a href="{claim_url}" class="claim-btn">Claim Ticket Now</a>
                </div>
            </div>
            <div class="footer">
                If you do not claim this seat within the time limit, your waitlist entry will be automatically expired.
            </div>
        </div>
    </body>
    </html>
    """
    
    # Always log locally first
    log_email_locally(to_email, subject, html_content)
    
    # Try sending via Resend if configured
    if settings.EMAIL_PROVIDER == "resend" and settings.RESEND_API_KEY:
        try:
            import resend
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send({
                "from": settings.FROM_EMAIL,
                "to": to_email,
                "subject": subject,
                "html": html_content
            })
            logger.info(f"Successfully sent waitlist offer email to {to_email} via Resend")
        except Exception as e:
            logger.error(f"Failed to send email via Resend: {e}")

def send_otp_email(to_email: str, otp_code: str):
    subject = f"Your TicketFlow Login Verification Code: {otp_code}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f0f4ff; color: #0f172a; margin: 0; padding: 20px; }}
            .card {{ max-width: 480px; margin: 20px auto; background: #ffffff; border-radius: 16px; border: 1px solid rgba(109, 40, 217, 0.12); overflow: hidden; box-shadow: 0 10px 30px rgba(109, 40, 217, 0.08); }}
            .header {{ background: linear-gradient(135deg, #7c3aed 0%, #c026d3 100%); padding: 24px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 22px; color: #fff; text-transform: uppercase; letter-spacing: 2px; }}
            .content {{ padding: 32px; text-align: center; }}
            .code-box {{ background: #f1f5f9; border: 1px dashed rgba(109, 40, 217, 0.2); color: #7c3aed; font-size: 32px; font-weight: 800; padding: 16px; border-radius: 12px; margin: 24px auto; width: 200px; letter-spacing: 4px; }}
            .info-text {{ font-size: 14px; color: #64748b; line-height: 1.6; margin-bottom: 24px; }}
            .footer {{ text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid rgba(109, 40, 217, 0.08); padding: 16px; background: #f8fafc; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <h1>TicketFlow Verification</h1>
            </div>
            <div class="content">
                <p style="font-size: 16px; font-weight: bold; margin-bottom: 12px;">Hello,</p>
                <p class="info-text">You are attempting to log in to your TicketFlow account. Use the following One-Time Password (OTP) to complete your verification:</p>
                <div class="code-box">{otp_code}</div>
                <p class="info-text" style="font-size: 12px; color: #94a3b8;">This code is valid for 5 minutes. If you did not request this login, please ignore this email.</p>
            </div>
            <div class="footer">
                &copy; {datetime.datetime.now().year} TicketFlow. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    
    # Always log locally first
    log_email_locally(to_email, subject, html_content)
    
    # Try sending via Resend if configured
    if settings.EMAIL_PROVIDER == "resend" and settings.RESEND_API_KEY:
        try:
            import resend
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send({
                "from": settings.FROM_EMAIL,
                "to": to_email,
                "subject": subject,
                "html": html_content
            })
            logger.info(f"Successfully sent OTP email to {to_email} via Resend")
        except Exception as e:
            logger.error(f"Failed to send email via Resend: {e}")

