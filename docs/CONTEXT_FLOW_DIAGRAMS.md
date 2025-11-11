# Conversation Context Flow - Visual Diagrams

## 1. Complete Session Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SESSION LIFECYCLE                                  │
└─────────────────────────────────────────────────────────────────────────────┘

Step 1: SESSION CREATION
━━━━━━━━━━━━━━━━━━━━━━━
  Client Request
      │
      ├─ Create Session
      │   └─ POST /chat/start
      │       └─ { "customer_email": "user@example.com" }
      │
      └─ Backend: memory.create_session("user@example.com")
          └─ INSERT conversation_sessions (UUID, email, metadata)
          └─ Return: session_id (UUID)

Step 2: FIRST TURN
━━━━━━━━━━━━━━━━
  User Query: "Busco una laptop"
      │
      ├─ Router.classify_intent(query)
      │   ├─ Detect language: "es"
      │   ├─ Load memory context (user blocks, session blocks)
      │   ├─ Gemini classification (temp=0)
      │   └─ Return: Intent.SALES, language="es"
      │
      ├─ Select Agent: SalesAgent
      │   └─ SalesAgent(session_id, memory_manager, language="es")
      │       └─ conversation_history = [] (EMPTY)
      │
      ├─ Agent.generate_response("Busco una laptop", include_history=True)
      │   ├─ _build_contents() includes empty history
      │   ├─ Gemini API call
      │   ├─ _update_history()
      │   │   ├─ Append to RAM: conversation_history
      │   │   └─ Save to DB: conversation_messages
      │   └─ Return response
      │
      └─ Response saved with intent="sales"

Step 3: SAME AGENT CONTINUATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  User Query: "¿Cuánto cuesta?"
      │
      ├─ Router.classify_intent(query)
      │   └─ Intent.SALES (same agent)
      │
      ├─ SalesAgent.generate_response("¿Cuánto cuesta?")
      │   ├─ _build_contents() includes RAM history
      │   │   └─ Has previous "busco laptop" message
      │   ├─ Gemini sees context: "OK, user wants laptop"
      │   ├─ _update_history() saves to DB
      │   └─ OK: Context preserved
      │
      └─ Response with pricing

Step 4: AGENT HANDOFF
━━━━━━━━━━━━━━━━━━━━
  User Query: "Quiero agendar una demostración"
      │
      ├─ Router.classify_intent(query)
      │   └─ Intent.BOOKING (DIFFERENT AGENT!)
      │
      ├─ Select Agent: BookingAgent
      │   └─ BookingAgent(session_id, memory_manager, language="es")
      │       └─ conversation_history = [] (EMPTY!)  ← PROBLEM!
      │
      ├─ Agent.generate_response("Quiero agendar una demostración")
      │   ├─ _build_contents() uses EMPTY conversation_history
      │   ├─ Gemini sees NO context about laptop preference!
      │   ├─ Must ask "What product?" (already discussed!)
      │   └─ ❌ CONTEXT LOSS OCCURS HERE
      │
      └─ Response without context

Step 5: SESSION ARCHIVAL
━━━━━━━━━━━━━━━━━━━━━━━
  After 30 days of inactivity
      │
      ├─ archive_inactive_sessions(30)
      │   └─ UPDATE conversation_sessions SET archived=TRUE
      │
      └─ User returns: get_or_create_session()
          └─ Archived session excluded (fresh session created)

Step 6: SESSION DELETION
━━━━━━━━━━━━━━━━━━━━━━━
  After 365 days of archival
      │
      └─ cleanup_archived_sessions(365)
          └─ DELETE conversation_sessions CASCADE
          └─ All messages, blocks, transfers deleted
```

## 2. RAM vs Database Memory Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MEMORY LAYER ARCHITECTURE                               │
└─────────────────────────────────────────────────────────────────────────────┘

                          RESPONSE GENERATION PIPELINE

┌────────────────┐
│  User Query    │
└────────┬───────┘
         │
    ┌────▼─────────────────────────────────────────────────────────────┐
    │ BaseAgent.generate_response(query, include_history=True)         │
    └────┬─────────────────────────────────────────────────────────────┘
         │
    ┌────▼─────────────────────────────────────────────────────────────┐
    │ _build_contents(query, include_history)                          │
    │                                                                   │
    │ ┌─────────────────────────────────────────────────────────────┐  │
    │ │ Build Conversation Contents for Gemini:                   │  │
    │ │                                                             │  │
    │ │ 1. Model acknowledgment                                    │  │
    │ │ 2. IF include_history:                                     │  │
    │ │    ├─ contents.extend(self.conversation_history)          │  │
    │ │    │   └─ This is RAM memory (list[types.Content])        │  │
    │ │    │   └─ Max 20 items (auto-trimmed)                     │  │
    │ │    │   └─ ISSUE: Empty after agent handoff!              │  │
    │ │    └─ Does NOT load from database!                        │  │
    │ │ 3. Current user query                                      │  │
    │ │                                                             │  │
    │ └─────────────────────────────────────────────────────────────┘  │
    │                                                                   │
    └────┬─────────────────────────────────────────────────────────────┘
         │
         │  ┌──────────────────────────────────────────────┐
         │  │ RAM MEMORY (conversation_history)           │
         │  │                                              │
         │  │ Max 20 items (10 turns):                    │
         │  │ ├─ Turn 1: [user message, model response]   │
         │  │ ├─ Turn 2: [user message, model response]   │
         │  │ ├─ Turn 3: [user message, model response]   │
         │  │ └─ ...                                       │
         │  │                                              │
         │  │ Updated by:                                 │
         │  │ └─ _update_history()                        │
         │  │    └─ Called after Gemini response          │
         │  │    └─ Appends user + model messages         │
         │  │                                              │
         │  │ Issues:                                     │
         │  │ ├─ Empty after agent handoff                │
         │  │ ├─ Not auto-loaded from database            │
         │  │ └─ Must manually call load_history_from_db()│
         │  └──────────────────────────────────────────────┘
         │
         │  ┌──────────────────────────────────────────────┐
         │  │ DATABASE MEMORY (PostgreSQL)                 │
         │  │                                              │
         │  │ conversation_messages table:                 │
         │  │ ├─ id (SERIAL)                              │
         │  │ ├─ session_id (UUID)                        │
         │  │ ├─ role ('user' or 'model')                 │
         │  │ ├─ agent_name (who generated it)            │
         │  │ ├─ intent ('sales', 'booking', 'general')   │
         │  │ ├─ message_text                             │
         │  │ ├─ tool_calls (JSONB)                       │
         │  │ ├─ response_time_ms                         │
         │  │ ├─ token_count                              │
         │  │ └─ created_at                               │
         │  │                                              │
         │  │ Populated by:                               │
         │  │ └─ _update_history()                        │
         │  │    └─ memory_manager.save_message()         │
         │  │    └─ Only if _memory_enabled               │
         │  │                                              │
         │  │ Retrieved by:                               │
         │  │ └─ load_history_from_db(limit)              │
         │  │    └─ NOT called automatically!             │
         │  └──────────────────────────────────────────────┘
         │
    ┌────▼─────────────────────────────────────────────────────────────┐
    │ Gemini API Call                                                  │
    │ ├─ system_instruction (from get_system_prompt)                   │
    │ ├─ contents (from _build_contents)                               │
    │ └─ config (generation parameters)                                │
    └────┬─────────────────────────────────────────────────────────────┘
         │
    ┌────▼─────────────────────────────────────────────────────────────┐
    │ Response Processing                                              │
    │ ├─ Extract response text                                         │
    │ ├─ Extract tool calls                                            │
    │ └─ Call _update_history(user_content, model_content)            │
    │     ├─ Append to RAM: conversation_history                      │
    │     │   └─ For next turn's context                              │
    │     │                                                             │
    │     └─ IF _memory_enabled: save_message()                       │
    │         └─ PostgreSQL persistence (long-term)                   │
    │             ├─ Save user message                                │
    │             ├─ Save model message                               │
    │             └─ Link to session_id                               │
    │                                                                  │
    └────┬─────────────────────────────────────────────────────────────┘
         │
    ┌────▼─────────────────────────────────────────────────────────────┐
    │ Return Response                                                  │
    └─────────────────────────────────────────────────────────────────┘

MEMORY LAYERS SUMMARY:
━━━━━━━━━━━━━━━━━━━━━
┌──────────────────────────────────────────────────────────────────┐
│ LAYER 1: RAM (conversation_history) - FAST, TEMPORARY            │
│ ├─ Stores: last 20 items max                                     │
│ ├─ Scope: Per agent instance                                     │
│ ├─ Update: _update_history() (after each response)               │
│ ├─ Query: _build_contents() (for context window)                 │
│ ├─ Loss: Empty after agent handoff ← CRITICAL ISSUE              │
│ └─ Fix: Auto-load from DB on init                               │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ LAYER 2: DATABASE (PostgreSQL) - DURABLE, QUERYABLE              │
│ ├─ Stores: ALL messages ever sent (unlimited)                    │
│ ├─ Scope: Per session_id (cross-agent!)                          │
│ ├─ Populate: _update_history() → save_message()                  │
│ ├─ Query: get_recent_messages(session_id, limit)                 │
│ ├─ Load: load_history_from_db() ← Manual, not auto!              │
│ └─ Fix: Call automatically after agent init                      │
└──────────────────────────────────────────────────────────────────┘

POTENTIAL FLOW (After Fixes):
━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Agent initialized with session_id
2. ✅ _auto_load_history_from_db() called
   └─ Loads last 10 messages
   └─ Populates conversation_history (RAM)
3. generate_response() builds contents
   └─ _build_contents() uses populated history
   └─ Gemini sees previous context
4. Response generated with full context
```

## 3. Agent Handoff Problem

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENT HANDOFF FLOW                                  │
└─────────────────────────────────────────────────────────────────────────────┘

CURRENT BEHAVIOR (PROBLEMATIC):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Turn N (SalesAgent Context)
════════════════════════════
  RAM (conversation_history):
  ┌──────────────────────────────┐
  │ Turn 1: "Busco laptop"       │
  │ "Tenemos XPS 13"             │
  │ Turn 2: "¿Cuánto cuesta?"    │
  │ "$999 en oferta"             │
  └──────────────────────────────┘
             ↓
  Agent: SalesAgent
  DB: conversation_messages (2 user turns, 2 model turns)

Turn N+1 (Handoff Point)
════════════════════════
  User: "Quiero agendar una demostración"
  
  Router.classify_intent()
  └─ Intent.BOOKING (different agent!)
  
  ❌ SELECT NEW AGENT: BookingAgent
     └─ BookingAgent.__init__(session_id, memory_manager)
     └─ self.conversation_history = [] ← EMPTY!
     └─ No auto-load from database
  
  RAM (conversation_history):
  ┌──────────────────────────────┐
  │ (EMPTY)                      │
  └──────────────────────────────┘
  
  DB: conversation_messages (still has all previous turns)
  
Turn N+1 (Response Generation)
══════════════════════════════
  BookingAgent.generate_response()
  
  _build_contents():
  └─ contents = []
  └─ + model_ack
  └─ + [conversation_history] ← EMPTY!
  └─ + current_query
  
  Result: Contents sent to Gemini have NO HISTORY
  ❌ Gemini response: "What product are you interested in?"
     (User already mentioned laptop!)

FIXED BEHAVIOR (PROPOSED):
━━━━━━━━━━━━━━━━━━━━━━━━

Turn N+1 (Fixed Handoff Point)
══════════════════════════════
  Router.classify_intent()
  └─ Intent.BOOKING
  
  ✅ SELECT NEW AGENT: BookingAgent
     └─ BookingAgent.__init__(session_id, memory_manager)
     │
     └─ _auto_load_history_from_db()  ← NEW!
        ├─ Query: get_recent_messages(session_id, limit=10)
        ├─ Results: [
        │   {"role": "user", "message_text": "Busco laptop"},
        │   {"role": "model", "message_text": "Tenemos XPS 13"},
        │   {"role": "user", "message_text": "¿Cuánto cuesta?"},
        │   {"role": "model", "message_text": "$999 en oferta"}
        │ ]
        └─ Populate: self.conversation_history
  
  RAM (conversation_history):
  ┌──────────────────────────────┐
  │ Turn 1: "Busco laptop"       │
  │ "Tenemos XPS 13"             │
  │ Turn 2: "¿Cuánto cuesta?"    │
  │ "$999 en oferta"             │
  └──────────────────────────────┘
  
Turn N+1 (Fixed Response Generation)
═════════════════════════════════════
  BookingAgent.generate_response()
  
  _build_contents():
  └─ contents = []
  └─ + model_ack
  └─ + [conversation_history] ← POPULATED!
  └─ + current_query
  
  Result: Contents sent to Gemini INCLUDE HISTORY
  ✅ Gemini response: "Perfect! I'll book a demo for your XPS 13 laptop.
                       What date works best?"
     (Continuity maintained!)
```

## 4. Memory Block Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MEMORY BLOCK HIERARCHY                                  │
└─────────────────────────────────────────────────────────────────────────────┘

TWO-TIER SYSTEM:
════════════════

TIER 1: SESSION-LEVEL MEMORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Table: agent_memory_blocks
┌─────────────────────────────────────────┐
│ Session-Specific Context                │
├─────────────────────────────────────────┤
│ session_id: abc-123-def                 │
│ block_label: "product_interest"         │
│ block_value: "XPS 13, interested in..." │
│ priority: 8                             │
│ agent_scope: "sales"                    │
│ ttl_days: 90                            │
│ expires_at: 2025-01-09                  │
└─────────────────────────────────────────┘

Purpose:
├─ Short-term context within session
├─ Booking details, product interests
├─ Agent-scoped preferences
└─ Auto-expires after 90 days

Retrieval:
└─ get_active_memory_blocks(session_id, agent_scope)
   ├─ Only active (non-expired) blocks
   ├─ Filtered by agent_scope
   ├─ Sorted by priority DESC
   └─ ← Used by AgentRouter only!


TIER 2: USER-LEVEL MEMORY
━━━━━━━━━━━━━━━━━━━━━━━━

Table: user_memory_blocks
┌─────────────────────────────────────────┐
│ Cross-Session User Context              │
├─────────────────────────────────────────┤
│ customer_email: maria@example.com       │
│ block_label: "preferred_agent"          │
│ block_value: "SalesAgent (prefers..."   │
│ priority: 9 (higher than session)       │
│ agent_scope: "shared"                   │
│ ttl_days: 180                           │
│ source_session_ids: [abc-123, def-456]  │
│ expires_at: 2026-05-10                  │
└─────────────────────────────────────────┘

Purpose:
├─ Long-term user preferences
├─ Preferences across MULTIPLE sessions
├─ Persistent customer profile
└─ Auto-expires after 180 days (6 months)

Retrieval:
└─ get_user_memory_blocks(customer_email, agent_scope)
   ├─ By customer email (not session!)
   ├─ Spans multiple sessions
   ├─ Used for cross-session personalization
   └─ ← Used by AgentRouter only!


SYNC MECHANISM:
━━━━━━━━━━━━━━━

Promotes high-value session blocks to user profile:

┌──────────────────────┐
│ Session Blocks       │
│                      │
│ ┌────────────────┐   │
│ │ label: XPS 13  │   │
│ │ priority: 8    │   │
│ │ scope: sales   │   │
│ └────┬───────────┘   │
│      │               │
│      ├─ Is priority  │
│      │  >= 7? ✓      │
│      │               │
│      ├─ Is scope     │
│      │  'shared'? ✗  │
│      │  → SKIP!      │
│      │               │
└──────────────────────┘

Filters for promotion:
├─ priority >= 7 (threshold)
├─ agent_scope == "shared"
└─ ttl_days extended (90→180)

Called by:
└─ sync_session_to_user_memory(session_id)
   ├─ When session ends
   ├─ When user archival occurs
   └─ Manually triggered


EXAMPLE MEMORY BLOCKS:
━━━━━━━━━━━━━━━━━━━━

Session-Level (agent_memory_blocks):
┌──────────────────────────────────────────────┐
│ Session: abc-123-def                         │
├──────────────────────────────────────────────┤
│ 1. product_interest                          │
│    "XPS 13 laptop, RTX 4060"                 │
│    priority: 8, scope: "sales"               │
│                                              │
│ 2. booking_date                              │
│    "2025-01-15 14:00"                        │
│    priority: 9, scope: "booking"             │
│                                              │
│ 3. customer_name                             │
│    "María García"                            │
│    priority: 6, scope: "shared"              │
└──────────────────────────────────────────────┘

User-Level (user_memory_blocks):
┌──────────────────────────────────────────────┐
│ Email: maria@example.com                     │
├──────────────────────────────────────────────┤
│ 1. preferred_language                        │
│    "es"                                      │
│    priority: 10, scope: "shared"             │
│    source: session-abc, session-def          │
│                                              │
│ 2. product_preference                        │
│    "Laptops for work/gaming hybrid"          │
│    priority: 8, scope: "shared"              │
│    source: session-abc                       │
│                                              │
│ 3. loyalty_status                            │
│    "Premium member since 2023"               │
│    priority: 9, scope: "shared"              │
│    source: session-abc, session-ghi, ...     │
└──────────────────────────────────────────────┘


CURRENT USAGE:
━━━━━━━━━━━━━

Router Loading:
└─ AgentRouter._get_memory_context()
   ├─ Loads session blocks
   ├─ Loads user blocks
   ├─ Formats as text
   └─ ✓ Includes in classification prompt

Agent Usage:
└─ ❌ Agents DON'T load blocks
   └─ Don't include in system prompts
   └─ Don't use for personalization
   └─ Waste of collected data!

PROPOSED FIX:
┌──────────────────────────────────────────┐
│ Agent.get_system_prompt()                │
│                                          │
│ Include memory blocks:                   │
│ ├─ Retrieve session-level blocks         │
│ ├─ Retrieve user-level blocks            │
│ ├─ Format with context                   │
│ └─ Append to system prompt                │
│                                          │
│ Result: Personalized agent behavior      │
└──────────────────────────────────────────┘
```

## 5. Context Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                    CONTEXT DATA FLOW                                 │
└──────────────────────────────────────────────────────────────────────┘

                    ┌─ START SESSION ─┐
                    │                 │
                    ▼                 ▼
            [Generate session_id]
                    │
                    ├─ conversation_sessions table
                    │  ├─ id (UUID)
                    │  ├─ customer_email
                    │  ├─ metadata { language, source, device }
                    │  └─ current_agent
                    │
                    ▼

        ┌─ TURN N: USER MESSAGE ─┐
        │                        │
        └─────────┬──────────────┘
                  │
        ┌─────────▼────────────────────────────────────┐
        │ AGENT ROUTER: classify_intent(query)         │
        │                                              │
        │ 1. detect_user_language(query) ──────────┐  │
        │    └─ Language "es" or "en"              │  │
        │                                          │  │
        │ 2. _get_memory_context() ────────────┐   │  │
        │    ├─ SELECT * FROM               │   │  │
        │    │  agent_memory_blocks          │   │  │
        │    │  WHERE session_id AND         │   │  │
        │    │  priority >= threshold        │   │  │
        │    │                               │   │  │
        │    └─ SELECT * FROM               │   │  │
        │       user_memory_blocks           │   │  │
        │       WHERE customer_email         │   │  │
        │       ──────────────────────────   │   │  │
        │    └─ Format as text context   ◄──┴───┘  │
        │                                          │
        │ 3. Gemini classification               │  │
        │    (temp=0, deterministic)             │  │
        │    └─ Returns Intent enum              │  │
        │                                        │  │
        └─────────┬──────────────────────────────┴──┘
                  │
        Returns: (Intent, language)
                  │
                  ├─ Intent.SALES ─┐
                  ├─ Intent.BOOKING ├─ SELECT AGENT
                  └─ Intent.GENERAL ─┘
                  │
                  ▼

        ┌─ AGENT SELECTION ─┐
        │                   │
        └────────┬──────────┘
                 │
                 ├─ SalesAgent(session_id, memory_manager, language)
                 │  └─ conversation_history = [] (EMPTY!)
                 │
                 ├─ BookingAgent(session_id, memory_manager, language)
                 │  └─ conversation_history = [] (EMPTY!)
                 │
                 └─ GeneralAgent(session_id, memory_manager, language)
                    └─ conversation_history = [] (EMPTY!)
                 │
                 ▼

        ┌─ AGENT: generate_response(query, include_history=True) ─┐
        │                                                          │
        │ 1. _build_contents(query, include_history)             │
        │    └─ contents.extend(conversation_history)            │
        │       ↓                                                 │
        │    RAM HISTORY (Empty after handoff! ←ISSUE)           │
        │                                                          │
        │ 2. Gemini API call with contents + system prompt       │
        │                                                          │
        │ 3. Response processing                                 │
        │                                                          │
        │ 4. _update_history() ─┐                                │
        │    ├─ Append to RAM:   │                               │
        │    │  conversation_history                             │
        │    │                   │                               │
        │    └─ IF memory_enabled:  │                            │
        │       memory_manager.save_message() │                  │
        │       │                             │                  │
        │       └─→ INSERT conversation_messages ◄──┐            │
        │          ├─ session_id                   │            │
        │          ├─ role ('user'/'model')        │            │
        │          ├─ agent_name                   │            │
        │          ├─ intent                       │            │
        │          ├─ message_text                 │            │
        │          ├─ tool_calls                   │            │
        │          └─ response_time_ms             │            │
        │                                         │            │
        └─────────────────────────────────────────┘            │
                     │                                         │
        ┌────────────▼──────────────────────────────────────┐  │
        │ DATABASE: conversation_messages                  │  │
        │ ┌──────────────────────────────────────────────┐ │  │
        │ │ Turn 1: User "Busco laptop"                │ │  │
        │ │ Turn 1: Model "Tenemos XPS 13..."          │ │  │
        │ │ Turn 2: User "¿Cuánto cuesta?"             │ │  │
        │ │ Turn 2: Model "$999 en oferta"             │ │  │
        │ │ Turn 3: User "Quiero agendar"              │ │  │
        │ │ Turn 3: Model "¿Qué fecha?"                │ │  │
        │ │ ...                                        │ │  │
        │ └──────────────────────────────────────────────┘ │  │
        │                                                  │  │
        │ ← Available but NOT auto-loaded! ◄──────────────┴──┘
        └──────────────────────────────────────────────────┘
                     │
                     ▼
        ┌─ TURN N+1: NEXT QUERY ─┐
        │                        │
        └────────┬───────────────┘
                 │
        ┌────────▼──────────────────────────────┐
        │ IF same agent:                       │
        │ └─ RAM history populated by        │
        │    previous _update_history()      │
        │ └─ generate_response() uses RAM    │
        │ └─ ✓ Context preserved             │
        │                                     │
        │ IF different agent:                │
        │ └─ RAM history empty               │
        │ └─ generate_response() uses empty  │
        │ └─ ❌ Context lost!                │
        └────────┬──────────────────────────┘
                 │
                 └─ Proposed Fix:
                    _auto_load_history_from_db()
                    └─ Load from database
                    └─ Populate RAM
                    └─ Context preserved


CONTEXT AVAILABILITY MATRIX:
════════════════════════════

Where is context available?
┌──────────────────────────────────────────────────────────┐
│                  │ Same Agent │ Handoff   │ New Session  │
├──────────────────┼────────────┼───────────┼──────────────┤
│ RAM History      │ ✓ Yes      │ ✗ No      │ ✗ No         │
│ DB History       │ ✓ Yes      │ ✓ Yes*    │ ✓ Yes*       │
│ Memory Blocks    │ ✓ Yes*     │ ✓ Yes*    │ ✓ Yes        │
│ Language Pref    │ ✓ Yes      │ ? Maybe*  │ ✓ Yes        │
│ Intent Context   │ ✓ Yes      │ ? Maybe*  │ ? Maybe*     │
└──────────────────┼────────────┼───────────┼──────────────┘
     ✓ = Available and used
     ✗ = Available but not used
     ? = Available but unclear if used
     * = Requires manual loading/passing
```

