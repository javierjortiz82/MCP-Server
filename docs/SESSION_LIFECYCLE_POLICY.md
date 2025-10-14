# Session Lifecycle & Data Retention Policy

**Version:** 1.0.0
**Effective Date:** 2025-10-13
**Author:** Lab01-MCP Team
**Last Updated:** 2025-10-13

## 📋 Table of Contents

- [Overview](#overview)
- [Legal Context](#legal-context)
- [Session Lifecycle Stages](#session-lifecycle-stages)
- [Retention Timelines](#retention-timelines)
- [Exceptions](#exceptions)
- [Automated Cleanup](#automated-cleanup)
- [GDPR Compliance](#gdpr-compliance)
- [Monitoring](#monitoring)
- [Configuration](#configuration)

---

## 🎯 Overview

This document defines the data retention and session lifecycle policy for the Lab01-MCP platform, ensuring compliance with GDPR, CCPA, and industry best practices while balancing business needs and system performance.

**Key Principles:**
- **Data Minimization:** Retain only necessary data
- **Time-Limited Storage:** Automatic expiration of old data
- **User Rights:** Support for "Right to be Forgotten"
- **Transparency:** Clear lifecycle stages and timelines
- **Performance:** Optimize queries with soft delete

---

## ⚖️ Legal Context

### GDPR (General Data Protection Regulation)
- **Article 5(1)(e):** Stored only as long as necessary
- **Article 17:** Right to erasure ("Right to be Forgotten")
- **Article 25:** Data protection by design and default

### CCPA (California Consumer Privacy Act)
- **Section 1798.105:** Consumer's right to deletion
- **Section 1798.120:** Right to opt-out

### Industry Standards
- **NIST Privacy Framework:** Minimize data collection and retention
- **ISO 27001:** Information security management

---

## 🔄 Session Lifecycle Stages

### Stage 1: Active (0-90 days)
**Status:** `archived = FALSE`, last_activity_at < 90 days

**Characteristics:**
- User can return and continue conversation
- Full context preserved
- All features available
- Included in active queries

**Actions:**
- Save new messages
- Update last_activity_at
- Extract memory blocks
- Track agent handoffs

---

### Stage 2: Inactive/Synced (30+ minutes)
**Status:** `archived = FALSE`, last_activity_at > 30 minutes

**Characteristics:**
- Session still active but not recently used
- High-priority memory blocks synced to user profile
- User can still resume session

**Actions (Automatic):**
- Call `auto_sync_inactive_sessions(30)`
- Promote priority >= 7 blocks to user memory
- Preserve session for potential return

---

### Stage 3: Archived (90-365 days)
**Status:** `archived = TRUE`

**Characteristics:**
- User hasn't returned for 90+ days
- Excluded from active queries (performance optimization)
- Data preserved for audit/analytics
- Can be restored if needed

**Actions:**
- Call `archive_inactive_sessions(90)`
- Set `archived = TRUE`
- Update `updated_at` timestamp
- Generate audit log

**User Experience:**
- If user returns: New session created automatically
- User memory blocks preserved: Continuity maintained

---

### Stage 4: Permanently Deleted (365+ days)
**Status:** N/A (deleted)

**Characteristics:**
- Archived for 365+ days
- No business value
- Compliance with retention limits

**Actions:**
- Call `cleanup_archived_sessions(365)`
- Delete session + messages + memory blocks (CASCADE)
- Delete context transfers
- Generate deletion log

**Irreversible:** Cannot be recovered after deletion

---

## ⏰ Retention Timelines

### Default Timelines

| Data Type | Retention Period | Configuration |
|-----------|------------------|---------------|
| **Active Sessions (with email)** | 90 days inactivity | `SESSION_SOFT_ARCHIVE_DAYS=90` |
| **Archived Sessions** | 365 days after archiving | `SESSION_HARD_DELETE_DAYS=365` |
| **Anonymous Sessions (no email)** | 30 days inactivity | `SESSION_ANONYMOUS_DELETE_DAYS=30` |
| **Session Memory Blocks** | 90 days (TTL) | `MEMORY_TTL_DAYS=90` |
| **User Memory Blocks** | 180 days (TTL) | `ttl_days=180` (user-level) |

### Total Retention Periods

| Scenario | Maximum Retention |
|----------|-------------------|
| **Active session with email** | 90 days inactive → archive<br>+ 365 days archived<br>= **455 days total** |
| **Anonymous session** | **30 days total** |
| **User memory (cross-session)** | **180 days from creation** |

---

## 🔐 Exceptions

### 1. Sessions with Confirmed Bookings
**Retention:** 2 years from booking date

**Reason:**
- Legal requirement for financial records
- Audit trail for completed transactions
- Customer service history

**Implementation:**
```sql
-- Preserve sessions with confirmed bookings
WHERE archived = TRUE
  AND updated_at < CURRENT_TIMESTAMP - INTERVAL '365 days'
  AND NOT EXISTS (
      SELECT 1 FROM bookings.appointments
      WHERE session_id = conversation_sessions.id
      AND status IN ('confirmed', 'completed')
      AND booking_date > CURRENT_TIMESTAMP - INTERVAL '2 years'
  )
```

### 2. User Explicitly Requested Deletion (GDPR)
**Retention:** Immediate deletion

**Process:**
```bash
# Use GDPR deletion tool
python3 scripts/gdpr_delete_user_data.py --email user@example.com --confirm
```

### 3. Legal Hold / Investigation
**Retention:** Indefinite until hold lifted

**Implementation:**
- Manual flag in `conversation_sessions.metadata`
- Excluded from automated cleanup
- Documented in audit log

---

## 🤖 Automated Cleanup

### Cron Job Schedule

**Recommended:** Daily at 3:00 AM
```bash
0 3 * * * /usr/bin/python3 /path/to/scripts/cleanup_expired_memories.py >> /var/log/memory_cleanup.log 2>&1
```

### Tasks Executed (in order)

1. **Auto-sync inactive sessions** (>30 min)
   - Promote high-priority memory to user profile
   - Maintains continuity across sessions

2. **Cleanup expired session memory blocks** (TTL: 90 days)
   - Remove low-priority expired blocks
   - Free up database space

3. **Cleanup expired user memory blocks** (TTL: 180 days)
   - Remove old cross-session memories
   - Maintain only relevant long-term memory

4. **Archive inactive sessions** (90 days)
   - Soft delete inactive sessions
   - Improve query performance

5. **Delete archived sessions** (365 days)
   - Hard delete old archived sessions
   - GDPR compliance

6. **Delete anonymous sessions** (30 days)
   - Fast cleanup of low-value sessions
   - Reduce database bloat

### Dry Run (Recommended First)
```bash
# Preview what would be deleted
python3 scripts/cleanup_expired_memories.py --dry-run
```

---

## 🛡️ GDPR Compliance

### Right to be Forgotten (Article 17)

**User Request Process:**

1. **Verify identity** (authentication required)
2. **Export data** (optional, recommended)
   ```bash
   python3 scripts/gdpr_delete_user_data.py --email user@example.com --export
   ```
3. **Delete all data** (irreversible)
   ```bash
   python3 scripts/gdpr_delete_user_data.py --email user@example.com --confirm
   ```

**Data Deleted:**
- All conversation sessions
- All conversation messages
- All session-level memory blocks
- All user-level memory blocks
- User memory profile
- Agent context transfers

**Timeline:** Within 30 days of verified request

### Data Portability (Article 20)

**Export Format:** JSON
**Includes:**
- Session metadata
- Complete message history
- Memory blocks
- User profile
- Context transfers

**Command:**
```bash
python3 scripts/gdpr_delete_user_data.py --email user@example.com --export
```

---

## 📊 Monitoring

### Key Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| **sessions_eligible_archive** | Sessions > 90 days inactive | > 1000 |
| **sessions_eligible_delete** | Archived sessions > 365 days | > 500 |
| **anonymous_sessions** | Sessions without email | > 5000 |
| **active_sessions_7d** | Sessions active in last 7 days | Trend analysis |
| **memory_blocks_expired** | Expired but not deleted blocks | > 10000 |

### Query Retention Stats

```sql
-- Get current retention statistics
SELECT * FROM test.get_session_retention_stats();
```

**Returns:**
- active_sessions: Count & percentage
- archived_sessions: Count & percentage
- anonymous: Count & percentage
- with_email: Count & percentage
- active_7d: Recent activity
- active_30d: Monthly activity
- eligible_archive: Ready for archiving
- eligible_delete: Ready for deletion

### Monitoring Dashboard (Recommended)

```bash
# View statistics
python3 scripts/odiseo_memory.py stats

# View recent sessions
python3 scripts/odiseo_memory.py sessions

# Session retention breakdown
python3 scripts/odiseo_memory.py sessions --include-archived
```

---

## ⚙️ Configuration

### Environment Variables (.env)

```env
# Session Lifecycle Configuration
SESSION_SOFT_ARCHIVE_DAYS=90          # Days before archiving
SESSION_HARD_DELETE_DAYS=365          # Days before deletion
SESSION_PRESERVE_WITH_EMAIL_DAYS=180  # Keep email sessions longer
SESSION_ANONYMOUS_DELETE_DAYS=30      # Delete anonymous faster

# Memory Configuration
MEMORY_TTL_DAYS=90                    # Session memory TTL
MEMORY_AUTO_CLEANUP_ENABLED=true      # Enable automatic cleanup
```

### Settings (Python)

**File:** `mcp_server/config/settings.py`

```python
from config.settings import settings

# Get lifecycle config
config = settings.get_session_lifecycle_config()

print(f"Archive after: {config['soft_archive_days']} days")
print(f"Delete after: {config['hard_delete_days']} days")
```

### Database Functions

**Available Functions:**

1. **archive_inactive_sessions(days)**
   ```sql
   SELECT * FROM test.archive_inactive_sessions(90);
   ```

2. **cleanup_archived_sessions(days)**
   ```sql
   SELECT test.cleanup_archived_sessions(365);
   ```

3. **cleanup_anonymous_sessions(days)**
   ```sql
   SELECT test.cleanup_anonymous_sessions(30);
   ```

4. **get_session_retention_stats()**
   ```sql
   SELECT * FROM test.get_session_retention_stats();
   ```

---

## 📚 Related Documentation

- [GDPR Compliance Guide](./GDPR_COMPLIANCE.md) (TBD)
- [Migration 005 Details](../mcp_server/migrations/005_add_session_lifecycle.sql)
- [Cleanup Job Documentation](../scripts/cleanup_expired_memories.py)
- [GDPR Deletion Tool](../scripts/gdpr_delete_user_data.py)
- [Memory Manager API](../mcp_server/utils/memory_manager.py)

---

## 🔄 Review & Updates

**Review Frequency:** Quarterly

**Responsible:** Engineering Team + Legal/Compliance

**Changelog:**
- 2025-10-13: v1.0.0 - Initial policy
- Next review: 2025-01-13

---

## 📞 Contact

**Questions or Concerns:**
- Technical: engineering@lab01-mcp.com
- Compliance: compliance@lab01-mcp.com
- Privacy: privacy@lab01-mcp.com

---

**Document Status:** ✅ Production Ready
**Last Updated:** 2025-10-13
**Version:** 1.0.0
