-- ============================================================================
-- CONSOLIDATED INDEXES - Lab01-MCP Database
-- ============================================================================
-- All 60+ indexes consolidado en un único archivo para gestión centralizada
-- Ejecutar después de que todas las tablas y funciones sean creadas
--
-- Organización:
-- 1. Products table indexes (search, embeddings, trigrams)
-- 2. Appointments table indexes (scheduling, status)
-- 3. Email queue indexes (delivery, retry)
-- 4. Conversation indexes (sessions, messages)
-- 5. Memory system indexes (agents, users, blocks)
-- 6. Utility indexes (pagination, context)
-- ============================================================================

-- ============================================================================
-- SECTION 1: PRODUCTS TABLE INDEXES
-- ============================================================================

-- Primary lookup
CREATE INDEX IF NOT EXISTS idx_products_sku 
ON test.products(sku);

-- Categorical search
CREATE INDEX IF NOT EXISTS idx_products_tags 
ON test.products USING GIN(tags);

-- Vector similarity search (AI embeddings)
CREATE INDEX IF NOT EXISTS idx_products_embedding_ivf 
ON test.products USING ivfflat(embedding vector_cosine_ops)
WITH (lists = 100);

-- Fuzzy/trigram search on name (for typo tolerance)
CREATE INDEX IF NOT EXISTS idx_products_name_trgm_compat 
ON test.products USING GIN(normalize_text(name) gin_trgm_ops);

-- Trigram index for description search
CREATE INDEX IF NOT EXISTS idx_products_desc_trgm_compat 
ON test.products USING GIN(normalize_text(description) gin_trgm_ops);

-- Advanced text search indexes
CREATE INDEX IF NOT EXISTS idx_products_name_word_trgm 
ON test.products USING GIN(name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_products_desc_word_trgm 
ON test.products USING GIN(description gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_products_name_normalized_trgm 
ON test.products USING GIN(normalize_text(name) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_products_desc_normalized_trgm 
ON test.products USING GIN(normalize_text(description) gin_trgm_ops);

-- Combined search index
CREATE INDEX IF NOT EXISTS idx_products_brand_cat_normalized_trgm 
ON test.products USING GIN((normalize_text(brand) || ' ' || normalize_text(category)) gin_trgm_ops);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_products_search 
ON test.products(sku, category, brand);

-- ============================================================================
-- SECTION 2: APPOINTMENTS TABLE INDEXES
-- ============================================================================

-- Booking date lookup (most common query)
CREATE INDEX IF NOT EXISTS idx_appointments_date 
ON test.appointments(booking_date);

-- Customer email lookup
CREATE INDEX IF NOT EXISTS idx_appointments_email 
ON test.appointments(customer_email);

-- Appointment status tracking
CREATE INDEX IF NOT EXISTS idx_appointments_status 
ON test.appointments(status);

-- Google Calendar synchronization
CREATE INDEX IF NOT EXISTS idx_appointments_calendar_id 
ON test.appointments(google_calendar_event_id);

-- Composite index for availability checking (date + time + status)
CREATE INDEX IF NOT EXISTS idx_appointments_date_time_status 
ON test.appointments(booking_date, booking_time, status);

-- Combined customer and date lookup
CREATE INDEX IF NOT EXISTS idx_appointments_customer_date 
ON test.appointments(customer_email, booking_date);

-- ============================================================================
-- SECTION 3: EMAIL QUEUE INDEXES
-- ============================================================================

-- Worker polling optimization
CREATE INDEX IF NOT EXISTS idx_email_queue_worker_poll 
ON test.email_queue(status, created_at)
WHERE status IN ('pending', 'retrying');

-- Recipient tracking
CREATE INDEX IF NOT EXISTS idx_email_queue_recipient 
ON test.email_queue(recipient_email);

-- Booking relationship
CREATE INDEX IF NOT EXISTS idx_email_queue_booking 
ON test.email_queue(booking_id);

-- Status and type tracking
CREATE INDEX IF NOT EXISTS idx_email_queue_type_status 
ON test.email_queue(email_type, status);

-- Delivery tracking
CREATE INDEX IF NOT EXISTS idx_email_queue_sent 
ON test.email_queue(sent_at);

-- Retry logic optimization
CREATE INDEX IF NOT EXISTS idx_email_queue_retry 
ON test.email_queue(retry_count, next_retry_time);

-- ============================================================================
-- SECTION 4: CONVERSATION INDEXES
-- ============================================================================

-- Session lookups
CREATE INDEX IF NOT EXISTS idx_conv_sessions_session_id 
ON test.conversation_sessions(session_id);

CREATE INDEX IF NOT EXISTS idx_conv_sessions_customer_email 
ON test.conversation_sessions(customer_email);

CREATE INDEX IF NOT EXISTS idx_conv_sessions_current_agent 
ON test.conversation_sessions(current_agent);

CREATE INDEX IF NOT EXISTS idx_conv_sessions_last_activity 
ON test.conversation_sessions(last_activity_at DESC);

-- Archived session tracking
CREATE INDEX IF NOT EXISTS idx_sessions_archived 
ON test.conversation_sessions(archived_at)
WHERE archived_at IS NOT NULL;

-- TTL management
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity_archived 
ON test.conversation_sessions(last_activity_at, archived_at);

-- Anonymous sessions
CREATE INDEX IF NOT EXISTS idx_sessions_email_null 
ON test.conversation_sessions(customer_email)
WHERE customer_email IS NULL;

-- Message lookups
CREATE INDEX IF NOT EXISTS idx_conv_messages_session_id 
ON test.conversation_messages(session_id);

CREATE INDEX IF NOT EXISTS idx_conv_messages_role 
ON test.conversation_messages(role);

CREATE INDEX IF NOT EXISTS idx_conv_messages_agent 
ON test.conversation_messages(agent_name)
WHERE role = 'agent';

CREATE INDEX IF NOT EXISTS idx_conv_messages_intent 
ON test.conversation_messages(intent);

-- ============================================================================
-- SECTION 5: MEMORY SYSTEM INDEXES
-- ============================================================================

-- Agent memory blocks
CREATE INDEX IF NOT EXISTS idx_memory_blocks_session 
ON test.agent_memory_blocks(session_id);

CREATE INDEX IF NOT EXISTS idx_memory_blocks_scope 
ON test.agent_memory_blocks(scope);

CREATE INDEX IF NOT EXISTS idx_memory_blocks_label 
ON test.agent_memory_blocks(label);

CREATE INDEX IF NOT EXISTS idx_memory_blocks_priority 
ON test.agent_memory_blocks(priority DESC);

-- Expiration management
CREATE INDEX IF NOT EXISTS idx_memory_blocks_expires 
ON test.agent_memory_blocks(expires_at)
WHERE expires_at IS NOT NULL;

-- User profiles
CREATE INDEX IF NOT EXISTS idx_user_profiles_last_seen 
ON test.user_memory_profiles(last_seen DESC);

-- User memory blocks
CREATE INDEX IF NOT EXISTS idx_user_memory_blocks_email 
ON test.user_memory_profiles(customer_email);

CREATE INDEX IF NOT EXISTS idx_user_memory_blocks_email_label 
ON test.user_memory_blocks(email, label);

CREATE INDEX IF NOT EXISTS idx_user_memory_blocks_label 
ON test.user_memory_blocks(label);

CREATE INDEX IF NOT EXISTS idx_user_memory_blocks_priority 
ON test.user_memory_blocks(priority DESC);

CREATE INDEX IF NOT EXISTS idx_user_memory_blocks_expires 
ON test.user_memory_blocks(expires_at)
WHERE expires_at IS NOT NULL;

-- ============================================================================
-- SECTION 6: UTILITY INDEXES
-- ============================================================================

-- Pagination context lookups
CREATE INDEX IF NOT EXISTS idx_pagination_contexts_session 
ON test.pagination_contexts(session_id);

CREATE INDEX IF NOT EXISTS idx_pagination_contexts_customer 
ON test.pagination_contexts(customer_email);

CREATE INDEX IF NOT EXISTS idx_pagination_contexts_name 
ON test.pagination_contexts(context_name);

-- TTL management
CREATE INDEX IF NOT EXISTS idx_pagination_contexts_expires 
ON test.pagination_contexts(expires_at)
WHERE expires_at IS NOT NULL;

-- Context transfers
CREATE INDEX IF NOT EXISTS idx_context_transfers_session 
ON test.agent_context_transfers(session_id);

CREATE INDEX IF NOT EXISTS idx_context_transfers_from_to 
ON test.agent_context_transfers(from_agent, to_agent);

CREATE INDEX IF NOT EXISTS idx_context_transfers_success 
ON test.agent_context_transfers(success)
WHERE success = TRUE;

-- ============================================================================
-- SECTION 7: BUSINESS HOURS & BLOCKED TIMES
-- ============================================================================

-- Service hours lookups
CREATE INDEX IF NOT EXISTS idx_service_hours_service 
ON test.service_hours(service_type);

CREATE INDEX IF NOT EXISTS idx_service_hours_by_day 
ON test.service_hours(day_of_week);

CREATE INDEX IF NOT EXISTS idx_service_hours_lookup 
ON test.service_hours(service_type, day_of_week);

CREATE INDEX IF NOT EXISTS idx_service_hours_multi_range 
ON test.service_hours(service_type, start_time, end_time);

-- Service types
CREATE INDEX IF NOT EXISTS idx_service_types_active 
ON test.service_types(active)
WHERE active = TRUE;

-- Blocked times
CREATE INDEX IF NOT EXISTS idx_blocked_times_date 
ON test.blocked_times(block_date);

CREATE INDEX IF NOT EXISTS idx_blocked_times_date_time 
ON test.blocked_times(block_date, start_time, end_time);

-- ============================================================================
-- FINAL SUMMARY
-- ============================================================================

-- Total indexes created: 60+
-- Organized by function for maintenance and tuning
-- All indexes use IF NOT EXISTS for idempotency
-- Includes B-tree, GIN (trigram), and vector (IVFFlat) types

-- Index Statistics (for monitoring):
-- SELECT * FROM pg_stat_user_indexes ORDER BY idx_scan DESC;
-- SELECT * FROM pg_stat_user_indexes WHERE idx_scan = 0;

