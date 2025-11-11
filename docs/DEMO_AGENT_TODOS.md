# Demo Agent - TODO Items Tracker

This document tracks pending improvements for the demo_agent service.

**Last Updated:** 2025-11-10
**Service:** demo_agent (v1.0.0)
**Status:** 2 pending items

---

## TODO Items

### TODO-DEMO-001: Implement Email Notification to Sales Team

**Location:** `demo_agent/routes/forms.py:219`

**Priority:** MEDIUM
**Status:** PENDING
**Effort:** 2-3 hours
**Category:** Feature Enhancement

**Description:**
Send email alert to sales team when a contact request is submitted through the contact form.

**Current Implementation:**
```python
# await email_service.send_contact_notification(contact)
```

The functionality is stubbed out but not implemented. Contact requests are saved to the database but no notification email is sent to the sales team.

**Implementation Requirements:**

- [ ] Create email template for contact notifications (Jinja2)
- [ ] Implement `EmailIntegrationService.send_contact_notification()` method
- [ ] Configure sales team email address in .env.example
- [ ] Ensure email failures don't block contact submission (async, logged)
- [ ] Add unit tests for email delivery
- [ ] Add integration test with mock email service

**Acceptance Criteria:**

1. When contact request is submitted, email is queued for sending
2. Email contains: contact name, email, phone, message, request type
3. Email is sent to configured sales team email address
4. If email fails to send, error is logged but contact request submission succeeds
5. Email service uses existing `email_service` for SMTP delivery
6. No new external dependencies required

**Template Example:**
```
Subject: New Contact Request - {contact_type}
From: noreply@demo-agent.local
To: sales@example.com

Name: {name}
Email: {email}
Phone: {phone}
Type: {contact_type}

Message:
{message}

---
Submitted at: {created_at}
```

**Related Services:**
- `demo_agent.services.email_integration.EmailIntegrationService`
- `demo_agent.routes.forms.submit_contact_request()`

**Notes:**
- Email service is already configured and working for OTP delivery
- Should follow same pattern as OTP email notifications
- Consider adding email rate limiting (max 5 emails/day per unique email)

---

### TODO-DEMO-002: Extract Frontend API Domain from JWT 'iss' Claim

**Location:** `demo_agent/services/clerk_service.py:101`

**Priority:** MEDIUM
**Status:** PENDING
**Effort:** 1-2 hours
**Category:** Security Hardening

**Description:**
Dynamically determine the Clerk frontend API domain from the JWT token's 'iss' (issuer) claim instead of using hardcoded configuration.

**Current Implementation:**
```python
# Current workaround: Use config.CLERK_FRONTEND_API or default domain
return config.CLERK_FRONTEND_API if hasattr(config, "CLERK_FRONTEND_API") else "clerk.accounts.dev"
```

The implementation reads from configuration, but for multi-tenant scenarios (multiple Clerk organizations), it should extract the domain from the JWT token's `iss` claim.

**Implementation Requirements:**

- [ ] Extract JWT 'iss' claim from the token
- [ ] Parse domain from issuer claim (format: `https://clerk.{domain}.clerk.accounts.dev`)
- [ ] Validate domain format is valid Clerk instance
- [ ] Implement fallback to config value if claim extraction fails
- [ ] Add unit tests with sample JWT tokens
- [ ] Document JWT claim format expectations
- [ ] Add error logging for malformed claims

**Acceptance Criteria:**

1. Extract 'iss' claim from JWT token
2. Parse domain in format: `https://clerk.{instance}.clerk.accounts.dev`
3. Return extracted domain if valid
4. Fall back to `config.CLERK_FRONTEND_API` if claim missing
5. Log warnings for malformed claims (no errors)
6. All existing tests pass
7. Code is type-hinted and documented

**Example Implementation:**
```python
async def get_frontend_api_domain(self, token: str) -> str:
    """Extract Clerk frontend API domain from JWT 'iss' claim.

    For multi-tenant support, extracts the domain from the JWT token
    instead of using hardcoded configuration.

    Args:
        token: JWT token from Clerk

    Returns:
        Frontend API domain (e.g., "clerk.odiseo.com")
    """
    try:
        # Decode token without verification (we only need 'iss' claim)
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(token, options={"verify_signature": False})

        iss = payload.get("iss")
        if not iss:
            logger.warning("JWT 'iss' claim missing, using config value")
            return self._get_default_domain()

        # Parse domain from iss claim
        # Expected format: https://clerk.{instance}.clerk.accounts.dev
        parsed_domain = self._parse_clerk_domain(iss)
        if parsed_domain:
            return parsed_domain

        logger.warning(f"Failed to parse 'iss' claim: {iss}")
        return self._get_default_domain()

    except Exception as e:
        logger.exception(f"Error extracting domain from JWT: {e}")
        return self._get_default_domain()
```

**Related Services:**
- `demo_agent.services.clerk_service.ClerkService`
- JWT token validation and verification

**Dependencies:**
- Already using `PyJWT` library
- No new dependencies required

**Notes:**
- Multi-tenant support is a future enhancement
- Current single-tenant implementation is stable
- This is a quality improvement, not a blocker
- Consider prioritizing after basic functionality is production-ready

---

## Completion Guidelines

To complete a TODO item:

1. Create a feature branch: `feat/demo-agent-{todo-id}`
2. Implement the changes with:
   - Google-style docstrings
   - Type hints
   - Unit tests (minimum 80% coverage)
   - Integration tests where applicable
3. Update this document with completion date
4. Create a pull request referencing this issue
5. Mark as COMPLETED after review and merge

---

## Statistics

| Status | Count | Effort |
|--------|-------|--------|
| PENDING | 2 | 3-5 hours |
| COMPLETED | 0 | - |
| **TOTAL** | **2** | **3-5 hours** |

---

## Related Issues

- Feature: Email notifications system
- Feature: Multi-tenant Clerk support
- Refactoring: Code quality improvements

