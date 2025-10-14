# Google Calendar Integration Setup Guide

**Version:** 1.0.0
**Created:** 2025-10-13
**Author:** Lab01-MCP Team
**Status:** Production Ready (Configuration Required)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Step-by-Step Setup](#step-by-step-setup)
- [Configuration](#configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Security Best Practices](#security-best-practices)
- [API Limitations](#api-limitations)

---

## 🎯 Overview

The Lab01-MCP platform includes **complete Google Calendar integration** that automatically syncs bookings to your Google Calendar. This integration is **already implemented** in the codebase but **disabled by default** for security reasons.

### What's Included

The integration automatically handles:
- **Creating calendar events** when bookings are made
- **Updating events** when bookings are rescheduled
- **Deleting events** when bookings are cancelled
- **Sending email notifications** to attendees (customer)
- **Adding reminders** (30 minutes and 10 minutes before)
- **Checking busy times** to prevent double-booking

### Technical Implementation

**Files Involved:**
- `mcp_server/utils/google_calendar.py` - GoogleCalendarClient class (570 lines)
- `mcp_server/tools/bookings.py` - Integration with booking functions
- `mcp_server/config/settings.py` - Configuration settings

**Authentication Method:** Service Account (server-to-server, no OAuth flow needed)

---

## ✅ Prerequisites

Before starting, ensure you have:

1. **Google Account** with access to Google Cloud Console
2. **Google Calendar** that will receive bookings
3. **Admin access** to enable APIs and create service accounts
4. **Python 3.8+** with pip installed
5. **Lab01-MCP** codebase with latest changes

**Estimated Setup Time:** 15-20 minutes

---

## 🚀 Step-by-Step Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Select a project"** → **"New Project"**
3. Enter project details:
   - **Project Name:** `Lab01-MCP-Calendar`
   - **Organization:** (optional)
   - **Location:** (optional)
4. Click **"Create"**
5. Wait for project creation (30 seconds)
6. Select the newly created project

**Screenshot Reference:** Top navbar shows project name after selection

---

### Step 2: Enable Google Calendar API

1. In the Google Cloud Console, ensure your project is selected
2. Navigate to **"APIs & Services"** → **"Library"**
3. Search for **"Google Calendar API"**
4. Click on **"Google Calendar API"** result
5. Click **"Enable"** button
6. Wait for API to be enabled (10 seconds)

**Verification:** You should see "API enabled" with a green checkmark

**Alternative URL:** https://console.cloud.google.com/apis/library/calendar-json.googleapis.com

---

### Step 3: Create Service Account

A service account allows your server to access Google Calendar without requiring user login.

1. Navigate to **"APIs & Services"** → **"Credentials"**
2. Click **"Create Credentials"** → **"Service Account"**
3. Fill in service account details:
   - **Service account name:** `lab01-mcp-calendar-bot`
   - **Service account ID:** (auto-generated) `lab01-mcp-calendar-bot@...`
   - **Description:** `Service account for Lab01-MCP booking calendar integration`
4. Click **"Create and Continue"**
5. **Grant access** (Optional):
   - Role: `None` (calendar access granted via sharing, not IAM)
   - Click **"Continue"**
6. **Grant users access** (Optional):
   - Leave empty
   - Click **"Done"**

**Result:** Service account created with email like:
```
lab01-mcp-calendar-bot@lab01-mcp-calendar.iam.gserviceaccount.com
```

**Important:** Copy this email address - you'll need it in Step 5!

---

### Step 4: Generate Service Account Credentials (JSON Key)

1. In **"Credentials"** page, find your service account in the list
2. Click on the service account name
3. Go to **"Keys"** tab
4. Click **"Add Key"** → **"Create new key"**
5. Select **"JSON"** key type
6. Click **"Create"**

**Result:** A JSON file downloads automatically to your computer.

**File Name Example:** `lab01-mcp-calendar-1a2b3c4d5e6f.json`

**Security Warning:** This file grants access to your calendar. Store it securely!

---

### Step 5: Share Google Calendar with Service Account

The service account needs permission to create/edit/delete events in your calendar.

1. Open [Google Calendar](https://calendar.google.com/)
2. Locate the calendar you want to use for bookings (usually "Primary")
3. Hover over the calendar name in the left sidebar
4. Click the **three dots** (⋮) → **"Settings and sharing"**
5. Scroll to **"Share with specific people"**
6. Click **"Add people"**
7. Enter the **service account email** from Step 3:
   ```
   lab01-mcp-calendar-bot@lab01-mcp-calendar.iam.gserviceaccount.com
   ```
8. Set permissions: **"Make changes to events"**
9. Click **"Send"**

**Verification:** Service account email appears in the shared list with "Make changes to events" permission.

**Calendar ID:** If using primary calendar, the ID is usually your Gmail address. For other calendars, find the Calendar ID in Settings → "Integrate calendar" → "Calendar ID"

---

### Step 6: Install Credentials File in Lab01-MCP

1. **Create credentials directory** (if it doesn't exist):
   ```bash
   mkdir -p /home/javort/Lab01-MCP/credentials
   ```

2. **Move downloaded JSON file** to credentials directory:
   ```bash
   mv ~/Downloads/lab01-mcp-calendar-*.json /home/javort/Lab01-MCP/credentials/service-account.json
   ```

3. **Set secure permissions** (recommended):
   ```bash
   chmod 600 /home/javort/Lab01-MCP/credentials/service-account.json
   ```

**Final Path:** `/home/javort/Lab01-MCP/credentials/service-account.json`

**Security Note:** Add `credentials/` to `.gitignore` to prevent committing secrets!

---

### Step 7: Configure Environment Variables

1. **Open your `.env` file**:
   ```bash
   nano /home/javort/Lab01-MCP/.env
   ```

2. **Add/Update Google Calendar configuration**:
   ```env
   # =============================================================================
   # Google Calendar Integration
   # =============================================================================
   GOOGLE_CALENDAR_ENABLED=true
   GOOGLE_CALENDAR_CREDENTIALS_PATH=credentials/service-account.json
   GOOGLE_CALENDAR_ID=primary
   GOOGLE_CALENDAR_TIMEZONE=America/New_York
   ```

3. **Customize values**:
   - `GOOGLE_CALENDAR_ENABLED`: Set to `true` to enable integration
   - `GOOGLE_CALENDAR_CREDENTIALS_PATH`: Path to JSON key file (relative to project root)
   - `GOOGLE_CALENDAR_ID`:
     - `primary` for your main calendar
     - Or specific calendar ID (e.g., `user@example.com`)
   - `GOOGLE_CALENDAR_TIMEZONE`: Your timezone ([IANA format](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones))
     - Examples: `America/New_York`, `Europe/Madrid`, `Asia/Tokyo`

4. **Save and close** (Ctrl+X, Y, Enter)

---

### Step 8: Install Required Python Dependencies

The Google Calendar API client library should already be in `requirements.txt`, but verify:

```bash
cd /home/javort/Lab01-MCP

# Check if dependencies are installed
pip list | grep google-api-python-client
pip list | grep google-auth
```

If not installed:

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

**Expected Versions:**
- `google-api-python-client>=2.100.0`
- `google-auth>=2.23.0`
- `google-auth-httplib2>=0.1.1`

---

### Step 9: Test the Integration

Run the provided test script to verify everything works:

```bash
cd /home/javort/Lab01-MCP
python3 test_calendar_integration.py
```

**Expected Output:**
```
=============================================================================
GOOGLE CALENDAR INTEGRATION TEST
=============================================================================
Timestamp: 2025-10-13 10:30:45

Step 1/5: Loading configuration...
✅ Configuration loaded successfully
   Calendar ID: primary
   Timezone: America/New_York

Step 2/5: Initializing GoogleCalendarClient...
✅ GoogleCalendarClient initialized

Step 3/5: Creating test event...
✅ Test event created successfully
   Event ID: abc123xyz
   Calendar Link: https://calendar.google.com/event?eid=...

Step 4/5: Verifying event in calendar...
✅ Event verified in Google Calendar

Step 5/5: Cleaning up (deleting test event)...
✅ Test event deleted

=============================================================================
✅ ALL TESTS PASSED - Google Calendar integration is working!
=============================================================================

Next steps:
1. Create a test booking via your application
2. Check that the event appears in Google Calendar
3. Try rescheduling and cancelling bookings
4. Monitor logs for any errors
```

**If Tests Fail:** See [Troubleshooting](#troubleshooting) section below.

---

### Step 10: Restart Services

Restart all Lab01-MCP services to load the new configuration:

```bash
# If using systemd
sudo systemctl restart lab01-mcp-server
sudo systemctl restart lab01-mcp-agent

# Or if running manually
# Stop current processes (Ctrl+C) and restart:
cd /home/javort/Lab01-MCP/mcp_server
python3 server.py &

cd /home/javort/Lab01-MCP/agent
python3 -m gemini_agent.agent &
```

**Verification:** Check logs for successful initialization:
```bash
tail -f /home/javort/Lab01-MCP/logs/mcp_server.log | grep "GoogleCalendarClient"
# Should see: "GoogleCalendarClient initialized successfully"
```

---

## ⚙️ Configuration

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_CALENDAR_ENABLED` | Yes | `false` | Enable/disable integration |
| `GOOGLE_CALENDAR_CREDENTIALS_PATH` | Yes | `credentials/service-account.json` | Path to service account JSON |
| `GOOGLE_CALENDAR_ID` | Yes | `primary` | Calendar ID to use |
| `GOOGLE_CALENDAR_TIMEZONE` | Yes | `UTC` | Timezone for events ([IANA format](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)) |

### Common Timezone Values

| Region | Timezone |
|--------|----------|
| **US East Coast** | `America/New_York` |
| **US West Coast** | `America/Los_Angeles` |
| **US Central** | `America/Chicago` |
| **Spain** | `Europe/Madrid` |
| **UK** | `Europe/London` |
| **Japan** | `Asia/Tokyo` |
| **Australia (Sydney)** | `Australia/Sydney` |

### Using Multiple Calendars

To use a specific calendar instead of primary:

1. Get Calendar ID from Google Calendar:
   - Settings → Select calendar → "Integrate calendar" → "Calendar ID"
   - Example: `bookings@example.com` or `abc123xyz@group.calendar.google.com`

2. Update `.env`:
   ```env
   GOOGLE_CALENDAR_ID=bookings@example.com
   ```

3. Ensure service account has "Make changes to events" permission on that calendar

---

## 🧪 Testing

### Manual Test via Booking Creation

1. **Create a booking** using your application or API:
   ```bash
   curl -X POST http://localhost:8000/api/bookings \
     -H "Content-Type: application/json" \
     -d '{
       "customer_name": "Test User",
       "customer_email": "test@example.com",
       "service_type": "Consulting",
       "booking_date": "2025-10-20",
       "start_time": "14:00",
       "duration_minutes": 60
     }'
   ```

2. **Check Google Calendar**:
   - Open https://calendar.google.com/
   - Navigate to 2025-10-20 at 2:00 PM
   - You should see: "Consulting - Test User"

3. **Verify event details**:
   - Click the event
   - Check description includes service type and customer info
   - Check attendee is `test@example.com`
   - Check reminders are set (30 min, 10 min before)

4. **Test rescheduling**:
   ```bash
   curl -X PUT http://localhost:8000/api/bookings/{booking_id}/reschedule \
     -H "Content-Type: application/json" \
     -d '{
       "new_booking_date": "2025-10-21",
       "new_start_time": "15:00"
     }'
   ```
   - Event should move to new date/time in calendar

5. **Test cancellation**:
   ```bash
   curl -X DELETE http://localhost:8000/api/bookings/{booking_id}
   ```
   - Event should disappear from calendar

### Automated Test Script

The included `test_calendar_integration.py` script tests:
- ✅ Configuration loading
- ✅ Client initialization
- ✅ Event creation
- ✅ Event verification
- ✅ Event deletion

Run it anytime to verify integration health:
```bash
python3 test_calendar_integration.py
```

---

## 🔧 Troubleshooting

### Error: "Credentials file not found"

**Symptom:**
```
FileNotFoundError: credentials/service-account.json not found
```

**Solution:**
1. Verify file exists: `ls -la /home/javort/Lab01-MCP/credentials/service-account.json`
2. Check path in `.env` matches actual file location
3. Ensure path is relative to project root, not absolute

---

### Error: "Access denied" or "403 Forbidden"

**Symptom:**
```
HttpError 403: The caller does not have permission
```

**Solution:**
1. Verify calendar is shared with service account email
2. Check permission level is "Make changes to events" (not "See all event details")
3. Wait 5 minutes for permissions to propagate
4. Try again

**Verify Sharing:**
- Go to Google Calendar → Settings → Select calendar → "Share with specific people"
- Confirm service account email is listed

---

### Error: "Calendar API not enabled"

**Symptom:**
```
HttpError 403: Google Calendar API has not been used in project
```

**Solution:**
1. Go to Google Cloud Console
2. Navigate to "APIs & Services" → "Library"
3. Search "Google Calendar API"
4. Click "Enable"
5. Wait 1-2 minutes for activation
6. Restart your services

---

### Error: "Invalid credentials" or "Could not load credentials"

**Symptom:**
```
DefaultCredentialsError: Could not automatically determine credentials
```

**Solution:**
1. Verify JSON file is valid (open in text editor, should be valid JSON)
2. Check file permissions: `chmod 600 credentials/service-account.json`
3. Re-download credentials from Google Cloud Console if corrupted
4. Ensure you downloaded the correct service account's key

---

### Events Not Appearing in Calendar

**Possible Causes:**

1. **Wrong calendar ID:**
   - Solution: Verify `GOOGLE_CALENDAR_ID` in `.env` matches calendar
   - Use `primary` for main calendar or specific calendar ID

2. **Timezone mismatch:**
   - Solution: Check `GOOGLE_CALENDAR_TIMEZONE` matches your location
   - Event may appear at wrong time if timezone is incorrect

3. **Integration disabled:**
   - Solution: Verify `GOOGLE_CALENDAR_ENABLED=true` in `.env`
   - Check logs for "GoogleCalendarClient initialized" message

4. **Service not restarted:**
   - Solution: Restart all Lab01-MCP services after configuration changes

---

### Test Script Fails but Manual API Works

**Symptom:** `test_calendar_integration.py` fails but Google Calendar API works in Google Cloud Console

**Solution:**
1. Check Python path: `which python3`
2. Verify virtual environment is activated
3. Reinstall dependencies:
   ```bash
   pip install --force-reinstall google-api-python-client google-auth
   ```
4. Check for conflicting Google packages:
   ```bash
   pip list | grep google
   ```

---

## 🔒 Security Best Practices

### Credential Storage

1. **Never commit credentials to Git:**
   ```bash
   # Add to .gitignore
   echo "credentials/" >> .gitignore
   git rm --cached credentials/service-account.json  # If already committed
   ```

2. **Restrict file permissions:**
   ```bash
   chmod 600 credentials/service-account.json
   chown www-data:www-data credentials/service-account.json  # If using web server
   ```

3. **Use environment-specific credentials:**
   - Production: `credentials/prod-service-account.json`
   - Staging: `credentials/staging-service-account.json`
   - Development: `credentials/dev-service-account.json`

### Service Account Permissions

1. **Minimal calendar permissions:**
   - Only share specific booking calendar, not all calendars
   - Use "Make changes to events" not "Make changes and manage sharing"

2. **Rotate credentials regularly:**
   - Create new key every 90 days
   - Delete old keys from Google Cloud Console

3. **Monitor API usage:**
   - Check Google Cloud Console → "APIs & Services" → "Dashboard"
   - Set up alerts for unusual activity

### Network Security

1. **Use HTTPS only:**
   - All Google Calendar API calls use HTTPS by default
   - Ensure your application uses HTTPS in production

2. **Firewall rules:**
   - Allow outbound HTTPS to `*.googleapis.com`
   - No inbound rules needed (service account is server-to-server)

---

## 📊 API Limitations

### Google Calendar API Quotas

| Quota | Default Limit | Notes |
|-------|---------------|-------|
| **Queries per day** | 1,000,000 | Shared across all users |
| **Queries per 100 seconds** | 100 | Per service account |
| **Events per day** | Unlimited | No hard limit on event creation |

**Source:** [Google Calendar API Usage Limits](https://developers.google.com/calendar/api/guides/quota)

### Rate Limiting

The `GoogleCalendarClient` includes **automatic retry logic** with exponential backoff:
- Retries on `503 Service Unavailable` and `429 Too Many Requests`
- Max 3 retries
- Backoff: 1s → 2s → 4s

**Best Practice:** For high-volume booking systems, implement request queuing to stay within quota.

### Event Limits

- **Max attendees per event:** 200
- **Max event duration:** No hard limit
- **Max events per calendar:** Unlimited (subject to storage limits)
- **Max event title length:** 1024 characters
- **Max event description length:** 8192 characters

---

## 📚 Additional Resources

### Official Documentation

- [Google Calendar API Overview](https://developers.google.com/calendar/api/guides/overview)
- [Service Accounts Explained](https://cloud.google.com/iam/docs/service-accounts)
- [Python Quickstart Guide](https://developers.google.com/calendar/api/quickstart/python)

### Lab01-MCP Resources

- [Session Lifecycle Policy](./SESSION_LIFECYCLE_POLICY.md)
- [Booking System Documentation](../mcp_server/tools/bookings.py)
- [GoogleCalendarClient Source](../mcp_server/utils/google_calendar.py)

### Support

**Questions or Issues:**
- Technical: engineering@lab01-mcp.com
- Google Cloud: [Google Cloud Support](https://cloud.google.com/support)

---

## 🔄 Maintenance

### Quarterly Review Checklist

- [ ] Rotate service account credentials (every 90 days)
- [ ] Review API quota usage in Google Cloud Console
- [ ] Check for unused service accounts and delete
- [ ] Update dependencies: `pip install --upgrade google-api-python-client`
- [ ] Test calendar integration after dependency updates
- [ ] Review calendar sharing permissions

### Monitoring Metrics

Track these metrics in your monitoring system:
- `calendar_events_created_total` - Count of events created
- `calendar_events_failed_total` - Count of failed creations
- `calendar_api_latency_seconds` - API response time
- `calendar_quota_remaining` - Daily quota remaining

---

**Document Status:** ✅ Production Ready
**Last Updated:** 2025-10-13
**Version:** 1.0.0
