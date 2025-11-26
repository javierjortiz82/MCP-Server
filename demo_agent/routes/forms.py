"""Contact and Booking Form Routes.

Public endpoints for contact form submissions and demo booking requests.

Author: Lab01-MCP Team
Created: 2025-11-10
Version: 1.0.0
"""

from fastapi import APIRouter, HTTPException, Request

from demo_agent.config.settings import config
from demo_agent.db.connection import get_db
from demo_agent.logger import logger
from demo_agent.models.booking import BookingRequest, BookingResponse
from demo_agent.models.contact import ContactRequest, ContactResponse
from demo_agent.services.client_ip_service import extract_client_ip

router = APIRouter(prefix="/v1", tags=["Forms"])


def get_demo_agent(request: Request) -> Any:
    """Get demo_agent instance from app state.

    Args:
        request: FastAPI request object.

    Returns:
        DemoAgent: Demo agent instance.

    Raises:
        HTTPException: If demo_agent is not initialized.
    """
    demo_agent = request.app.state.demo_agent

    if not demo_agent:
        raise HTTPException(status_code=500, detail="Service not initialized")

    return demo_agent


@router.post("/contact", response_model=ContactResponse)
async def submit_contact_request(
    contact: ContactRequest,
    request: Request,
) -> ContactResponse | JSONResponse:
    """Submit contact form with reCAPTCHA validation.

    Processes contact form submissions from the website with spam protection.
    All fields are validated and reCAPTCHA score is checked before saving.

    Request Body:
    ```json
    {
      "full_name": "John Doe",
      "email": "john@example.com",
      "phone": "+15551234567",
      "country_code": "US",
      "company": "Acme Inc",
      "message": "I want to learn more about your services",
      "contact_type": "sales",
      "recaptcha_token": "03AGdBq..."
    }
    ```

    Response (Success - 200):
    ```json
    {
      "success": true,
      "message": "Thank you! We'll contact you soon.",
      "contact_id": 42,
      "created_at": "2025-11-09T10:30:00Z"
    }
    ```

    Response (reCAPTCHA Failed - 400):
    ```json
    {
      "success": false,
      "message": "reCAPTCHA verification failed. Please try again."
    }
    ```

    Response (Rate Limit - 429):
    ```json
    {
      "success": false,
      "message": "Too many submissions. Please try again later."
    }
    ```

    Security Features:
    - reCAPTCHA v3 spam detection (score threshold: 0.5)
    - IP-based rate limiting (5 submissions per hour per IP)
    - Input sanitization and validation
    - Suspicious submission detection

    Args:
        contact: Contact form data.
        request: FastAPI request object.

    Returns:
        ContactResponse: Submission result.
    """
    try:
        demo_agent = get_demo_agent(request)
        logger.info("=== submit_contact_request START ===")

        # Extract client IP for logging and rate limiting
        remote_ip = extract_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")

        logger.info(f"Contact submission from IP: {remote_ip}")

        # Step 1: Verify reCAPTCHA token
        try:
            verification_result = await demo_agent.captcha_handler.verify_token(
                token=contact.recaptcha_token,
                remote_ip=remote_ip,
            )

            if not verification_result.get("success"):
                logger.warning(
                    f"reCAPTCHA verification failed for {contact.email}: "
                    f"{verification_result.get('error_codes')}"
                )
                return ContactResponse(
                    success=False,
                    message="reCAPTCHA verification failed. Please try again.",
                )

            # Evaluate score
            score = verification_result.get("score", 0.0)
            evaluation = demo_agent.captcha_handler.evaluate_score(score)

            logger.info(
                f"reCAPTCHA score for {contact.email}: {score:.2f} "
                f"(risk: {evaluation['risk_level']})"
            )

            # Reject if score is too low
            if score < config.FINGERPRINT_SCORE_THRESHOLD:
                logger.warning(
                    f"Contact submission blocked: low reCAPTCHA score {score:.2f}"
                )
                return ContactResponse(
                    success=False,
                    message="Your submission appears suspicious. Please try again.",
                )

        except Exception as captcha_error:
            logger.error(f"reCAPTCHA verification error: {captcha_error}")
            return ContactResponse(
                success=False,
                message="reCAPTCHA verification failed. Please try again.",
            )

        # Step 2: Check IP rate limiting (5 submissions per hour)
        db = get_db()
        rate_limit_query = """
            SELECT COUNT(*) as count
            FROM :SCHEMA_NAME.contact_requests
            WHERE ip_address = %s
              AND created_at > NOW() - INTERVAL '1 hour'
        """
        rate_limit_result = await db.execute_one(rate_limit_query, (remote_ip,))

        if rate_limit_result and rate_limit_result.get("count", 0) >= 5:
            logger.warning(f"Rate limit exceeded for IP: {remote_ip}")
            return ContactResponse(
                success=False,
                message="Too many submissions. Please try again in an hour.",
            )

        # Step 3: Insert contact request into database
        insert_query = """
            INSERT INTO :SCHEMA_NAME.contact_requests (
                full_name, email, phone, country_code, company,
                message, contact_type, ip_address, user_agent,
                recaptcha_score, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """

        result = await db.execute_one(
            insert_query,
            (
                contact.full_name,
                contact.email,
                contact.phone,
                contact.country_code,
                contact.company,
                contact.message,
                contact.contact_type,
                remote_ip,
                user_agent,
                score,
                "pending",
            ),
        )

        if not result:
            logger.error("Failed to insert contact request")
            raise HTTPException(
                status_code=500,
                detail="Failed to save contact request",
            )

        contact_id = result["id"]
        created_at = result["created_at"].isoformat()

        logger.info(
            f"Contact request saved: ID={contact_id}, "
            f"email={contact.email}, type={contact.contact_type}"
        )

        # Step 4: Send email notification to sales team (optional)
        # TODO-DEMO-001: Implement email notification to sales team
        # Description: Send email alert to sales team when contact request received
        # Priority: MEDIUM | Status: PENDING | Effort: 2-3 hours
        # Implementation: Integrate with email_service to send templated notification
        # Acceptance Criteria:
        #   - Email template created for contact notifications
        #   - Email sent to configured sales team address
        #   - Failure to send email doesn't block contact submission (logged only)
        # await email_service.send_contact_notification(contact)

        return ContactResponse(
            success=True,
            message="Thank you! We'll contact you soon.",
            contact_id=contact_id,
            created_at=created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in submit_contact_request: {e}")
        return ContactResponse(
            success=False,
            message="An error occurred. Please try again later.",
        )


@router.post("/booking", response_model=BookingResponse)
async def submit_booking_request(booking: BookingRequest, request: Request) -> BookingResponse | JSONResponse:
    """Submit demo booking request with reCAPTCHA verification.

    Public endpoint for scheduling demo bookings from website.

    Security:
    - reCAPTCHA v3 verification (threshold: 0.7)
    - IP-based rate limiting (5 bookings per hour)
    - Input validation via Pydantic

    Args:
        booking: Validated booking request data.
        request: FastAPI request object.

    Returns:
        BookingResponse: Booking submission result with booking ID.

    Raises:
        HTTPException: 429 if rate limit exceeded.
    """
    try:
        demo_agent = get_demo_agent(request)

        # Extract client IP
        remote_ip = request.client.host if request.client else "unknown"

        # Step 1: Verify reCAPTCHA token
        verification_result = await demo_agent.captcha_handler.verify_token(
            token=booking.recaptcha_token,
            remote_ip=remote_ip,
        )

        if not verification_result["success"]:
            logger.warning(
                "reCAPTCHA verification failed for booking",
                extra={
                    "ip": remote_ip,
                    "error": verification_result.get("error"),
                },
            )
            return BookingResponse(
                success=False,
                message="Security verification failed. Please try again.",
            )

        recaptcha_score = verification_result.get("score", 0.0)

        if recaptcha_score < 0.7:
            logger.warning(
                f"Low reCAPTCHA score for booking: {recaptcha_score}",
                extra={"ip": remote_ip, "email": booking.email},
            )
            return BookingResponse(
                success=False,
                message="Security check failed. Please try again.",
            )

        # Step 2: Check IP rate limiting (5 bookings per hour)
        db = get_db()
        rate_limit_query = """
            SELECT COUNT(*) as count
            FROM :SCHEMA_NAME.booking_requests
            WHERE ip_address = %s AND created_at > NOW() - INTERVAL '1 hour'
        """
        rate_limit_result = await db.execute_one(rate_limit_query, (remote_ip,))

        if rate_limit_result and rate_limit_result.get("count", 0) >= 5:
            logger.warning(f"Rate limit exceeded for IP: {remote_ip}")
            return BookingResponse(
                success=False,
                message="Too many booking requests. Please try again in an hour.",
            )

        # Step 3: Insert booking request into database
        user_agent = request.headers.get("user-agent", "unknown")

        insert_query = """
            INSERT INTO :SCHEMA_NAME.booking_requests (
                full_name, email, phone, country_code, company,
                preferred_date, preferred_time, message,
                ip_address, user_agent, recaptcha_score, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """

        booking_result = await db.execute_one(
            insert_query,
            (
                booking.full_name,
                booking.email,
                booking.phone,
                booking.country_code,
                booking.company,
                booking.preferred_date,
                booking.preferred_time,
                booking.message,
                remote_ip,
                user_agent,
                recaptcha_score,
                "pending",
            ),
        )

        if not booking_result:
            logger.error("Failed to insert booking request")
            return BookingResponse(
                success=False,
                message="Failed to create booking. Please try again.",
            )

        booking_id = booking_result["id"]
        created_at = booking_result["created_at"]

        logger.info(
            "Booking request created successfully",
            extra={
                "booking_id": booking_id,
                "email": booking.email,
                "preferred_date": str(booking.preferred_date),
                "ip": remote_ip,
                "score": recaptcha_score,
            },
        )

        return BookingResponse(
            success=True,
            message="Demo booking request submitted successfully! We'll contact you shortly.",
            booking_id=booking_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in submit_booking_request: {e}")
        return BookingResponse(
            success=False,
            message="An error occurred. Please try again later.",
        )
