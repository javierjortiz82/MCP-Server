# Migration Plan: User-Centric Architecture

**Date:** 2025-11-09
**Goal:** Migrate from session-based to user-based chat history
**Approach:** Soft migration (backwards compatible)

---

## Changes Required

### 1. Database Schema Updates

```sql
-- Add user_id to conversation_messages
ALTER TABLE test.conversation_messages
ADD COLUMN user_id INTEGER REFERENCES test.demo_users(id);

-- Add index for performance
CREATE INDEX idx_messages_user_created
ON test.conversation_messages(user_id, created_at DESC);

-- Change default language to English
ALTER TABLE test.demo_users
ALTER COLUMN preferred_language SET DEFAULT 'en';

-- Backfill user_id from session metadata (for existing messages)
UPDATE test.conversation_messages cm
SET user_id = (
    SELECT (cs.metadata->>'user_id')::INTEGER
    FROM test.conversation_sessions cs
    WHERE cs.id = cm.session_id
)
WHERE cm.user_id IS NULL
  AND EXISTS (
      SELECT 1 FROM test.conversation_sessions cs
      WHERE cs.id = cm.session_id
        AND cs.metadata->>'user_id' IS NOT NULL
  );
```

### 2. Backend Changes

#### `/v1/demo` endpoint (main.py)
- Store `user_id` directly in `conversation_messages`
- Keep `session_id` for backwards compatibility
- User ID comes from Clerk JWT (server-side, secure)

#### `/v1/demo/history` endpoint (main.py)
- Query by `user_id` instead of `session_id`
- Remove session ownership check (user_id IS the ownership)
- Simpler, faster query

#### New endpoint: `/v1/user/language` (main.py)
- `GET /v1/user/language` - Get user's preferred language
- `PUT /v1/user/language` - Update user's preferred language

### 3. Frontend Changes

#### i18n Configuration (src/i18n/config.ts)
- Change default language from auto-detect to 'en'
- Load language from user preferences on login
- Save language changes to backend API

#### Remove session_id localStorage (src/services/demoAgent.ts)
- Remove `getOrCreateSessionId()` method
- Session ID no longer needed in frontend
- User ID comes from Clerk authentication

---

## Implementation Steps

### Phase 1: Database (5 min)
1. Run migration SQL (above)
2. Verify backfill worked
3. Test query performance

### Phase 2: Backend (30 min)
4. Update `/v1/demo` to store user_id
5. Update `/v1/demo/history` to query by user_id
6. Add `/v1/user/language` endpoints
7. Test with Postman/curl

### Phase 3: Frontend (20 min)
8. Update i18n to default to 'en'
9. Add language preference API calls
10. Remove session_id localStorage logic
11. Test end-to-end flow

### Phase 4: Testing (15 min)
12. Test cross-device history sync
13. Test language persistence
14. Test logout/login flow
15. Verify GDPR compliance (data export)

---

## Rollback Plan

If issues occur:

```sql
-- Rollback database changes
ALTER TABLE test.conversation_messages DROP COLUMN user_id;
ALTER TABLE test.demo_users ALTER COLUMN preferred_language SET DEFAULT 'es';
```

Then revert code changes via git.

---

## Success Criteria

- ✅ User sees same chat history on all devices
- ✅ Language defaults to English for new users
- ✅ Language preference saved to database
- ✅ No localStorage needed for session management
- ✅ Faster queries (no JOIN needed)
- ✅ GDPR compliant (easy data export/delete)
