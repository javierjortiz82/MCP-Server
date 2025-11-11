# 🧪 QA Testing Checklist - Lab01-MCP v1.0.0

**Date**: October 17, 2025  
**Version**: 1.0.0  
**Status**: Ready for Production Testing

---

## 📋 Pre-Testing Setup

### Environment Configuration
- [ ] Copy `.env.example` to `.env` (do not commit `.env`)
- [ ] Update `GOOGLE_API_KEY` with valid API key
- [ ] Update `DATABASE_URL` with test database connection
- [ ] Verify `BOOKING_MIN_ADVANCE_MINUTES=5` (for testing)
- [ ] Verify `GOOGLE_CALENDAR_TIMEZONE=America/Costa_Rica`
- [ ] Confirm `BOOKING_CHOICE_CONFIDENCE_THRESHOLD=0.75`
- [ ] Confirm `BOOKING_CONFIRMATION_THRESHOLD=0.75`

### Database Setup
- [ ] PostgreSQL running on correct host/port
- [ ] Test database created and accessible
- [ ] Schema initialized with migrations
- [ ] Sample data loaded (if applicable)

### Dependencies
- [ ] All Python dependencies installed (`pip install -r requirements.txt`)
- [ ] Google Calendar credentials available (service account JSON)
- [ ] All environment variables validated

---

## 🔴 CRITICAL ISSUES (2/2)

### Issue 1.1: Timezone Handling ✅
**Test**: Verify timezone-aware datetime operations
```bash
python3 -c "from datetime import datetime; from zoneinfo import ZoneInfo; from mcp_server.config.settings import settings; tz = ZoneInfo(settings.GOOGLE_CALENDAR_TIMEZONE); print(f'✅ Now: {datetime.now(tz)}')"
```
- [ ] Output shows Costa Rica timezone (-06:00)
- [ ] DST transitions handled correctly
- [ ] Datetime objects are timezone-aware

### Issue 4.1: Google Calendar ISO 8601 ✅
**Test**: Verify ISO 8601 formatting with timezone
- [ ] Calendar events created with correct ISO 8601 format
- [ ] Timezone offset included in datetime strings
- [ ] DST transitions don't affect calendar event times

---

## 🟠 HIGH PRIORITY ISSUES (5/5)

### Issue 1.3: Race Condition Prevention ✅
**Test**: Concurrent booking attempts
- [ ] Create 10 concurrent booking requests for same slot
- [ ] Verify only 1 booking succeeds
- [ ] Other 9 receive "slot already booked" error
- [ ] No duplicate bookings in database

**Test Command**: (Run in parallel in separate terminals)
```bash
# Terminal 1-10: Each runs same booking request
curl -X POST http://localhost:8000/bookings \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-10-20", "time": "14:00", "service": "consultation"}'
```

### Issue 1.2: DST Transition Edge Case ✅
**Test**: Bookings during DST transitions
- [ ] Create booking on March 10, 2025 (DST start)
- [ ] Create booking on November 2, 2025 (DST end)
- [ ] Verify times match expected offsets
- [ ] No 1-hour offset errors

### Issue 1.5: Minimum Advance Time for All Dates ✅
**Test**: Booking minimum advance enforcement
- [ ] Try to book 2 minutes from now → ❌ Rejected (min 5)
- [ ] Try to book 5 minutes from now → ✅ Accepted
- [ ] Try to book tomorrow at midnight → ✅ Accepted (>= 5 min)
- [ ] Try to book tomorrow at 00:04 → ❌ Rejected (< 5 min)

### Issue 3.1: Smart Sticky Session Routing ✅
**Test**: Intent routing with context
- [ ] Short query ("¿y ese?") after booking → Uses previous intent ✅
- [ ] Long query ("Cancelar mi cita") after booking → Classifies new intent ✅
- [ ] Complex query routed to correct agent ✅

---

## 🟡 MEDIUM PRIORITY ISSUES (8/8)

### Issue 5.1: Configuration Validation ✅
**Test**: Invalid configuration detection
```python
# Should raise ValueError
try:
    Settings(
        DATABASE_URL="postgresql://test@localhost/db",
        GOOGLE_API_KEY="test",
        BOOKING_DEFAULT_DURATION_MINUTES=30,  # Less than interval!
        BOOKING_SLOT_INTERVAL_MINUTES=60
    )
    print("❌ Should have rejected invalid config")
except ValueError as e:
    print(f"✅ Correctly rejected: {e}")
```
- [ ] Invalid duration/interval combo rejected
- [ ] Memory priority thresholds validated
- [ ] Session lifecycle dates validated
- [ ] Errors appear at application startup

### Issue 2.1: Fuzzy Matching Thresholds ✅
**Test**: Intent classification accuracy
- [ ] "cancelar" → CANCEL (confidence > 0.75) ✅
- [ ] "reschedule" → RESCHEDULE (confidence > 0.75) ✅
- [ ] Ambiguous input → UNKNOWN (confidence < 0.75) ✅
- [ ] Accuracy improved by 6-12%

### Issue 2.2: Substring Matching False Positives ✅
**Test**: No false positive substring matches
- [ ] "bueno" → Doesn't match "no" ✅
- [ ] "numero" → Doesn't match "no" ✅
- [ ] "cancelacion" → Correctly matches "cancel" ✅
- [ ] NEGATIVE_KEYWORDS prevents false matches

### Issue 2.3: Empty Input Validation ✅
**Test**: Empty/whitespace input handling
```python
try:
    BookingInputParser.parse_booking_choice("")
    print("❌ Should have raised ValueError")
except ValueError:
    print("✅ Correctly rejected empty input")
```
- [ ] Empty string raises ValueError ✅
- [ ] Whitespace-only string raises ValueError ✅
- [ ] Error message is clear ✅

### Issue 2.4: Language Detection ✅
**Test**: Spanish/English language detection
- [ ] "quiero cancelar mi cita" → Spanish (es) ✅
- [ ] "cancel my appointment" → English (en) ✅
- [ ] "Quisiera cambiar de fecha" → Spanish (es) ✅
- [ ] Mixed language → Defaults correctly ✅

### Issue 3.2: Memory Block Validation ✅
**Test**: Memory block structure validation
- [ ] Valid block processed ✅
- [ ] Missing `block_label` → Warning logged ✅
- [ ] Missing `block_value` → Warning logged ✅
- [ ] Non-dict block → Warning logged ✅
- [ ] Agent doesn't crash on malformed block ✅

### Issue 4.2: Google Calendar Retry Logic ✅
**Test**: Transient error retry handling
- [ ] Simulate HTTP 429 (rate limit) → Retries 3 times ✅
- [ ] Simulate HTTP 500 (internal error) → Retries 3 times ✅
- [ ] Simulate HTTP 503 (unavailable) → Retries 3 times ✅
- [ ] Verify exponential backoff (1s → 2s → 4s) ✅
- [ ] Permanent errors not retried ✅

**Monitoring**: Check logs for:
```
Transient error (HTTP 429) on attempt 1/3. Retrying in 1.0s...
Transient error (HTTP 429) on attempt 2/3. Retrying in 2.0s...
```

### Issue 4.3: Attendee Email Invites ✅
**Test**: Calendar invite handling
- [ ] Create booking with customer email ✅
- [ ] Email added as attendee OR in description ✅
- [ ] Customer receives calendar notification ✅
- [ ] Graceful fallback if Domain-Wide Delegation missing ✅
- [ ] Event created successfully even if attendee fails ✅

---

## 📊 Integration Tests

### End-to-End Booking Flow
**Scenario 1: Happy Path**
```
1. User requests available slots → Displays 30-min intervals ✅
2. User selects slot (5+ min advance) → Booking created ✅
3. Appointment added to Google Calendar ✅
4. Email confirmation sent ✅
5. Booking appears in customer's calendar ✅
```
- [ ] All steps complete successfully
- [ ] No errors in logs
- [ ] Database record created
- [ ] Calendar event visible

**Scenario 2: Invalid Booking Attempt**
```
1. User tries to book in 2 minutes → ❌ Rejected ✅
2. User tries to book same slot twice → ❌ Rejected ✅
3. User tries to reschedule past booking → ✅ Accepted
4. Reschedule updates calendar ✅
```
- [ ] All validations work
- [ ] Error messages clear
- [ ] No database corruption

**Scenario 3: Multi-Language Support**
```
1. Spanish user: "Quisiera cambiar mi cita" → BookingAgent ✅
2. English user: "I want to reschedule" → BookingAgent ✅
3. Mixed: "Quiero cancel mi appointment" → Correct parsing ✅
```
- [ ] Both languages recognized
- [ ] Intent classified correctly
- [ ] Booking flows work in both languages

---

## ✅ Performance Validation

### Booking Success Metrics
- [ ] Baseline: ~95% → After Fix: ≥99%
- [ ] Monitor failure reasons (timeout, validation, etc.)
- [ ] Average booking creation time < 2 seconds

### Google Calendar API
- [ ] Baseline: 5-10% transient errors → After Fix: ≤1%
- [ ] Retry logic reduces need for manual resubmission
- [ ] No cascading failures under load

### Intent Classification
- [ ] Baseline: ~92% accuracy → After Fix: ≥98%
- [ ] Fuzzy matching reduces misclassification
- [ ] Spanish parsing accuracy improved by 5%+

### Configuration
- [ ] Startup validation prevents deployment errors
- [ ] 0% configuration-related bugs
- [ ] Clear error messages if validation fails

---

## 🔍 Security & Compliance

### Data Handling
- [ ] Timezone calculations don't expose credentials
- [ ] Configuration validation doesn't log sensitive data
- [ ] Memory blocks don't contain PII
- [ ] API keys not logged in any tests

### Session Management
- [ ] GDPR session cleanup working
- [ ] Hard delete 365 days after archiving ✅
- [ ] Soft archive 90 days inactive ✅
- [ ] Anonymous sessions deleted faster (30 days) ✅

---

## 📈 Monitoring Setup

### Metrics to Track
- [ ] Booking creation success rate (target: ≥99%)
- [ ] Google Calendar API error rate (target: ≤1%)
- [ ] Intent classification accuracy (target: ≥98%)
- [ ] Configuration validation passes (target: 100%)
- [ ] Memory block validation passes (target: 100%)

### Logs to Monitor
```
# Issue 1.1, 4.1: Timezone operations
grep "Timezone-aware\|ISO 8601" logs/*.log

# Issue 1.3: Race conditions
grep "FOR UPDATE\|transaction\|race" logs/*.log

# Issue 4.2: Retry logic
grep "Transient error\|Retrying" logs/*.log

# Issue 5.1: Configuration
grep "Configuration validation\|ValueError" logs/*.log

# Issue 3.2: Memory validation
grep "Invalid memory block\|memory block missing" logs/*.log
```

---

## 🚀 Deployment Readiness

### Pre-Deployment Checklist
- [ ] All tests pass (19/19 smoke tests)
- [ ] Configuration validated
- [ ] Timezone handling verified
- [ ] Google Calendar retry working
- [ ] Database migrations applied
- [ ] Backups created
- [ ] Rollback procedure documented

### Post-Deployment Verification (24-48 hours)
- [ ] Monitor all metrics
- [ ] Check error logs
- [ ] Verify booking success rates
- [ ] Confirm calendar integrations
- [ ] Track user feedback
- [ ] No regression issues

### Success Criteria
- [ ] 0 configuration errors
- [ ] ≥99% booking success
- [ ] ≤1% calendar API errors
- [ ] ≥98% intent accuracy
- [ ] No user-facing issues

---

## 📞 Rollback Procedure

If critical issues found:
1. [ ] Stop services
2. [ ] Checkout previous stable commit (6b6d57a)
3. [ ] Restore backup .env
4. [ ] Restart services
5. [ ] Verify functionality

---

**QA Sign-Off**: _____________________  
**Date**: _____________________  
**Notes**: ___________________________

---

*This checklist verifies all 15 bug fixes from the comprehensive analysis report.*
