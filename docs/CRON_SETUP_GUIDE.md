# Cron Job Setup Guide - Memory Management

This guide explains how to configure automated maintenance jobs for the Lab01-MCP memory system.

## Overview

The memory system requires periodic maintenance tasks:

1. **Auto-Sync Job** - Sync inactive sessions to user-level memory (every 30-60 min)
2. **Cleanup Job** - Remove expired memory blocks (daily)

---

## 1. Auto-Sync Job

**Purpose:** Automatically sync high-priority memory blocks from inactive sessions to user-level memory.

**Frequency:** Every 30-60 minutes (recommended)

**Script:** `scripts/auto_sync_cron.py`

### Configuration

```bash
# Open crontab editor
crontab -e

# Add one of these lines:

# Option 1: Every 30 minutes
*/30 * * * * /usr/bin/python3 /path/to/Lab01-MCP/scripts/auto_sync_cron.py >> /var/log/auto_sync.log 2>&1

# Option 2: Every hour
0 * * * * /usr/bin/python3 /path/to/Lab01-MCP/scripts/auto_sync_cron.py >> /var/log/auto_sync.log 2>&1

# Option 3: Every 2 hours
0 */2 * * * /usr/bin/python3 /path/to/Lab01-MCP/scripts/auto_sync_cron.py >> /var/log/auto_sync.log 2>&1
```

### Test Manually

```bash
# Run once to test
python3 scripts/auto_sync_cron.py

# Expected output:
# [2025-10-13 14:30:00] Starting auto-sync job...
# ✅ Auto-synced 3 inactive sessions:
#    - a8a32296... (user@example.com): 2 new, 1 updated
#    - b7b21185... (maria@example.com): 1 new, 0 updated
#    - c6c10074... (test@example.com): 0 new, 2 updated
```

---

## 2. Cleanup Job

**Purpose:** Remove expired memory blocks and perform comprehensive maintenance.

**Frequency:** Daily (recommended: 3:00 AM)

**Script:** `scripts/cleanup_expired_memories.py`

### Configuration

```bash
# Open crontab editor
crontab -e

# Add one of these lines:

# Option 1: Daily at 3:00 AM
0 3 * * * /usr/bin/python3 /path/to/Lab01-MCP/scripts/cleanup_expired_memories.py >> /var/log/memory_cleanup.log 2>&1

# Option 2: Twice daily (3 AM and 3 PM)
0 3,15 * * * /usr/bin/python3 /path/to/Lab01-MCP/scripts/cleanup_expired_memories.py >> /var/log/memory_cleanup.log 2>&1

# Option 3: Weekly on Sunday at 2:00 AM
0 2 * * 0 /usr/bin/python3 /path/to/Lab01-MCP/scripts/cleanup_expired_memories.py >> /var/log/memory_cleanup.log 2>&1
```

### Test Manually

```bash
# Dry-run (preview without deleting)
python3 scripts/cleanup_expired_memories.py --dry-run

# Expected output:
# ==================================================================
# MEMORY CLEANUP JOB
# ==================================================================
# Timestamp: 2025-10-13 14:30:00
# Mode: DRY RUN
#
# Initial Statistics:
#   Session Blocks: 245 active, 12 expired
#   User Blocks: 87 active, 3 expired
#   User Profiles: 42
#   Active Sessions (24h): 15
#
# Task 1/3: Auto-syncing inactive sessions...
# Would auto-sync 5 inactive sessions (dry-run)
#
# Task 2/3: Cleaning up session-level memories...
# Would delete 12 expired session memory blocks (dry-run)
#
# Task 3/3: Cleaning up user-level memories...
# Would delete 3 expired user memory blocks (dry-run)
#
# 💡 This was a DRY RUN. No data was actually deleted.

# Actual cleanup (removes expired blocks)
python3 scripts/cleanup_expired_memories.py
```

---

## 3. Complete Crontab Example

```bash
# Lab01-MCP Memory Maintenance Jobs
# Edit with: crontab -e

# Auto-sync inactive sessions every 30 minutes
*/30 * * * * /usr/bin/python3 /home/user/Lab01-MCP/scripts/auto_sync_cron.py >> /var/log/auto_sync.log 2>&1

# Full cleanup job daily at 3:00 AM
0 3 * * * /usr/bin/python3 /home/user/Lab01-MCP/scripts/cleanup_expired_memories.py >> /var/log/memory_cleanup.log 2>&1

# Log rotation (optional, weekly on Monday)
0 0 * * 1 /usr/bin/find /var/log -name "auto_sync.log" -mtime +30 -delete
0 0 * * 1 /usr/bin/find /var/log -name "memory_cleanup.log" -mtime +30 -delete
```

---

## 4. Monitoring

### View Logs

```bash
# Auto-sync logs
tail -f /var/log/auto_sync.log

# Cleanup logs
tail -f /var/log/memory_cleanup.log

# View last 50 lines
tail -n 50 /var/log/memory_cleanup.log
```

### Check Cron Status

```bash
# List all cron jobs
crontab -l

# View cron logs (Ubuntu/Debian)
grep CRON /var/log/syslog

# View cron logs (CentOS/RHEL)
grep CRON /var/log/cron
```

### Verify Jobs Are Running

```bash
# Check if auto-sync ran in last hour
grep "Starting auto-sync job" /var/log/auto_sync.log | tail -n 5

# Check if cleanup ran today
grep "MEMORY CLEANUP JOB" /var/log/memory_cleanup.log | grep "$(date +%Y-%m-%d)"
```

---

## 5. Troubleshooting

### Job Not Running

**Check crontab syntax:**
```bash
crontab -l | grep -E "auto_sync|cleanup"
```

**Verify Python path:**
```bash
which python3
# Use the full path in crontab (e.g., /usr/bin/python3)
```

**Check permissions:**
```bash
ls -la /home/user/Lab01-MCP/scripts/*.py
# Should be executable (rwxr-xr-x)
```

**Test manually:**
```bash
cd /home/user/Lab01-MCP
python3 scripts/auto_sync_cron.py
# Should run without errors
```

### Database Connection Errors

**Verify .env file:**
```bash
cat /home/user/Lab01-MCP/mcp_server/.env | grep DATABASE_URL
# Should have valid connection string
```

**Test database connection:**
```bash
python3 -c "
from multi_agent import MEMORY_AVAILABLE, MemoryManager
print('Memory available:', MEMORY_AVAILABLE)
memory = MemoryManager()
print('Connection OK')
"
```

### Insufficient Permissions

**Create log directory:**
```bash
sudo mkdir -p /var/log/lab01_mcp
sudo chown $USER:$USER /var/log/lab01_mcp
```

**Update crontab paths:**
```bash
# Use user-writable log directory
*/30 * * * * python3 /home/user/Lab01-MCP/scripts/auto_sync_cron.py >> /home/user/logs/auto_sync.log 2>&1
```

---

## 6. Best Practices

### Frequency Recommendations

| Environment | Auto-Sync | Cleanup |
|-------------|-----------|---------|
| **Development** | Every 2 hours | Weekly |
| **Staging** | Every hour | Daily |
| **Production** | Every 30 min | Daily |

### Log Rotation

```bash
# Install logrotate config
sudo tee /etc/logrotate.d/lab01-mcp << EOF
/var/log/auto_sync.log /var/log/memory_cleanup.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    create 0644 user user
}
EOF
```

### Alerting

**Email on failure (requires configured mail):**
```bash
# Add to crontab
MAILTO=admin@example.com

0 3 * * * /usr/bin/python3 /path/to/scripts/cleanup_expired_memories.py >> /var/log/memory_cleanup.log 2>&1 || echo "Cleanup job failed" | mail -s "Lab01-MCP Cleanup Failed" admin@example.com
```

**Slack webhook on failure:**
```bash
# Create wrapper script
cat > /home/user/Lab01-MCP/scripts/cleanup_with_alert.sh << 'EOF'
#!/bin/bash
python3 /home/user/Lab01-MCP/scripts/cleanup_expired_memories.py
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    curl -X POST "https://hooks.slack.com/services/YOUR/WEBHOOK/URL" \
         -H 'Content-Type: application/json' \
         -d '{"text":"Lab01-MCP Cleanup Job Failed!"}'
fi

exit $EXIT_CODE
EOF

chmod +x /home/user/Lab01-MCP/scripts/cleanup_with_alert.sh
```

---

## 7. Performance Tuning

### Large Databases (>100k sessions)

**Adjust batch size in SQL function:**
```sql
-- Edit migration 004_add_auto_sync_trigger.sql
-- Change LIMIT 100 to LIMIT 1000 for faster batch processing
LIMIT 1000  -- Process max 1000 sessions per call
```

**Run cleanup more frequently:**
```bash
# Every 6 hours instead of daily
0 */6 * * * python3 /path/to/scripts/cleanup_expired_memories.py
```

### Low-Resource Environments

**Reduce auto-sync frequency:**
```bash
# Every 2 hours instead of 30 minutes
0 */2 * * * python3 /path/to/scripts/auto_sync_cron.py
```

**Run cleanup during off-peak hours:**
```bash
# 3:00 AM on weekends only
0 3 * * 0,6 python3 /path/to/scripts/cleanup_expired_memories.py
```

---

## 8. Manual Operations

### Force sync specific session

```bash
python3 -c "
from multi_agent import MemoryManager
memory = MemoryManager()
result = memory.sync_session_to_user_memory('YOUR_SESSION_ID')
print(f'Synced: {result[\"synced_blocks\"]} new, {result[\"updated_blocks\"]} updated')
"
```

### Check pending sessions

```bash
python3 -c "
from multi_agent import MemoryManager
from utils.db import fetchall
memory = MemoryManager()
query = f'''
SELECT session_id, customer_email, last_activity_at
FROM {memory.schema}.conversation_sessions
WHERE customer_email IS NOT NULL
  AND last_activity_at < NOW() - INTERVAL '\''30 minutes'\''
LIMIT 10
'''
sessions = fetchall(query)
print(f'Found {len(sessions)} inactive sessions')
for s in sessions:
    print(f'  - {s[\"session_id\"][:8]}... ({s[\"customer_email\"]})')
"
```

---

## Summary

**Minimal Setup (Quick Start):**
```bash
# 1. Make scripts executable
chmod +x scripts/auto_sync_cron.py scripts/cleanup_expired_memories.py

# 2. Add to crontab
crontab -e

# 3. Add these two lines:
*/30 * * * * /usr/bin/python3 /home/user/Lab01-MCP/scripts/auto_sync_cron.py >> ~/auto_sync.log 2>&1
0 3 * * * /usr/bin/python3 /home/user/Lab01-MCP/scripts/cleanup_expired_memories.py >> ~/cleanup.log 2>&1
```

**Production Setup:**
- Auto-sync: Every 30 minutes
- Cleanup: Daily at 3 AM
- Log rotation: 30 days
- Monitoring: Check logs daily
- Alerting: Email/Slack on failure

---

For questions or issues, see `docs/NOTAS_CLAUDE.md` section "FASE 6: CROSS-SESSION MEMORY".
