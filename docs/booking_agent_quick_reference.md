# Booking Agent "Mis Reservas" Optimization - Quick Reference

## TL;DR

**Goal:** Reduce booking_agent from 188KB to ~13KB (93% reduction) for "mis reservas" view-only intent

**Strategy:**
1. Delete 10 modules used for CREATE/RESCHEDULE workflows (143KB)
2. Shrink remaining 6 core modules by 80%+ (60KB)
3. Keep only essential: intent detection, anti-hallucination rules, scope boundaries

**Result:** 93% reduction (exceeds 75% target)

---

## Module Status Matrix

### CRITICAL - MUST KEEP (Optimized)

| Module | Current | Target | % Reduction | Purpose |
|--------|---------|--------|-------------|---------|
| base.jinja2 | 12.2KB | 3KB | 75% | Role/identity, multilingual |
| intent_detection.jinja2 | 11.4KB | 2KB | 82% | Recognize "mis reservas" |
| tool_usage_rules.jinja2 | 15.3KB | 2KB | 87% | Anti-hallucination |
| scope_guardrails.jinja2 | 12.8KB | 1.5KB | 88% | Define scope boundaries |
| context_enrichment.jinja2 | 9.9KB | 2KB | 80% | Load context vars |

**Subtotal: 61.6KB → 10.5KB**

### OPTIONAL - KEEP IF SPACE (Optimized)

| Module | Current | Target | % Reduction | Purpose |
|--------|---------|--------|-------------|---------|
| smart_greeting.jinja2 | 9.1KB | 1.5KB | 83% | Initial greeting |
| ux_best_practices.jinja2 | 3.3KB | 1KB | 70% | Error patterns |

**Subtotal: 12.4KB → 2.5KB**

### DELETE - NOT NEEDED

| Module | Size | Why Delete |
|--------|------|-----------|
| enhanced_time_slot_selection.jinja2 | 20.6KB | Only for booking creation |
| data_validation.jinja2 | 23.8KB | Only for booking input |
| duplicate_booking_prevention.jinja2 | 25.5KB | Only for creating bookings |
| ux_conversational.jinja2 | 15.8KB | Extract minimal, delete rest |
| disambiguation_rules.jinja2 | 9.3KB | Not needed for simple intent |
| confirmation_flow.jinja2 | 2.7KB | Only for booking workflows |
| data_requirements.jinja2 | 1KB | Only for booking operations |
| flexible_dates.jinja2 | 2KB | Only for parsing booking dates |
| examples.jinja2 | 5.4KB | Keep 0.5KB, delete 4.9KB |
| ux_best_practices.jinja2 | 3.3KB | Merge into base.jinja2 |

**Total Deletions: 108.9KB**

---

## Implementation Checklist

### Phase 1: Delete (1 hour, 75KB saved)
- [ ] Delete enhanced_time_slot_selection.jinja2
- [ ] Delete data_validation.jinja2
- [ ] Delete duplicate_booking_prevention.jinja2
- [ ] Delete confirmation_flow.jinja2
- [ ] Delete data_requirements.jinja2
- [ ] Delete flexible_dates.jinja2
- [ ] Update booking_agent.jinja2 to remove 6 includes

### Phase 2: Extract & Delete (2 hours, 35KB saved)
- [ ] Extract "VER_CITAS" flow from ux_conversational.jinja2
- [ ] Extract 1 "list bookings" example from examples.jinja2
- [ ] Merge useful error patterns from ux_best_practices into base
- [ ] Delete ux_conversational.jinja2
- [ ] Delete examples.jinja2
- [ ] Delete disambiguation_rules.jinja2
- [ ] Delete ux_best_practices.jinja2

### Phase 3: Shrink (3 hours, 60KB saved)
- [ ] Rewrite tool_usage_rules.jinja2 (keep only list_customer_bookings)
- [ ] Rewrite intent_detection.jinja2 (keep only "VER_RESERVAS")
- [ ] Rewrite base.jinja2 (collapse PTCF framework)
- [ ] Rewrite scope_guardrails.jinja2 (keep only view scope)
- [ ] Rewrite context_enrichment.jinja2 (minimal context)
- [ ] Rewrite smart_greeting.jinja2 (simplify greeting)

### Phase 4: Testing & Validation (2 hours)
- [ ] Test: "¿Cuáles son mis citas?" → list_customer_bookings called
- [ ] Test: Display formatted booking list correctly
- [ ] Test: Multilingual responses (Spanish/English)
- [ ] Test: is_past flag shown correctly
- [ ] Test: Out-of-scope redirect works
- [ ] Test: Empty bookings list handled
- [ ] Test: Error handling (tool failure)
- [ ] Test: No hallucinated data in responses

---

## Critical Success Rules for "Mis Reservas"

**DO:**
- ✅ ALWAYS call list_customer_bookings() first
- ✅ ONLY display data from tool response
- ✅ CHECK is_past flag (can't modify past bookings)
- ✅ Handle multilingual input/output
- ✅ Show clear error messages if tool fails
- ✅ Format bookings readably (date, time, service, status)

**DON'T:**
- ❌ NEVER invent booking data
- ❌ NEVER offer create/cancel/reschedule options (out of scope)
- ❌ NEVER show hardcoded service/time examples
- ❌ NEVER reinvent dates without tool confirmation
- ❌ NEVER silently fail - always inform user

---

## File Changes Summary

### Delete These Files (10 total)
```
booking_agent/modules/enhanced_time_slot_selection.jinja2
booking_agent/modules/data_validation.jinja2
booking_agent/modules/duplicate_booking_prevention.jinja2
booking_agent/modules/ux_conversational.jinja2
booking_agent/modules/disambiguation_rules.jinja2
booking_agent/modules/confirmation_flow.jinja2
booking_agent/modules/data_requirements.jinja2
booking_agent/modules/flexible_dates.jinja2
booking_agent/modules/examples.jinja2
booking_agent/modules/ux_best_practices.jinja2
```

### Keep These Files (6 total)
```
booking_agent/base.jinja2 (SHRINK)
booking_agent/modules/scope_guardrails.jinja2 (SHRINK)
booking_agent/modules/context_enrichment.jinja2 (SHRINK)
booking_agent/modules/smart_greeting.jinja2 (SHRINK)
booking_agent/modules/intent_detection.jinja2 (SHRINK)
booking_agent/modules/tool_usage_rules.jinja2 (SHRINK)
```

### Update This File
```
booking_agent/booking_agent.jinja2
- Remove 10 include statements
- Keep only 6 include statements
```

---

## Sample "Mis Reservas" Prompt Structure

```jinja2
{# BOOKING AGENT - MIS RESERVAS ONLY (Optimized v3.0) #}

{% include 'booking_agent/base.jinja2' %}
{# Identity: Specialist for viewing bookings #}

{% include 'booking_agent/modules/scope_guardrails.jinja2' %}
{# Scope: View-only, no create/cancel/reschedule #}

{% include 'booking_agent/modules/context_enrichment.jinja2' %}
{# Context: customer_email, current_date #}

{% include 'booking_agent/modules/smart_greeting.jinja2' %}
{# Greeting: "Aquí están tus reservas" #}

{% include 'booking_agent/modules/intent_detection.jinja2' %}
{# Intent: Only "mis reservas" pattern matching #}

{% include 'booking_agent/modules/tool_usage_rules.jinja2' %}
{# Rules: Only list_customer_bookings, no hallucinations #}

=== EXECUTION FLOW ===
1. Load context (customer_email)
2. Detect intent ("mis reservas"?)
3. Call list_customer_bookings(customer_email)
4. Format and display booking list
5. Check is_past flag for each booking
6. Separate future vs past bookings
7. Ask if user needs anything else
```

---

## Optimization Impact

| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| File Count | 16 modules | 6 modules | 10 deleted |
| Total Size | 188KB | 13KB | 175KB (93%) |
| Estimated Tokens | ~2,000 | ~700 | 65% reduction |
| Latency | Baseline | ~65% faster | Token processing time |
| Scope | Full CRUD | View-only | 91% simpler |
| Maintenance | 16 files | 6 files | Easier |

---

## Risk Assessment

**Risk Level:** LOW

**Why:**
- Read-only operation (no state changes)
- Single workflow (view bookings only)
- Clear intent (easy to detect)
- Tool-backed (uses real data)
- Extensive testing possible

**Rollback Time:** < 5 minutes (restore from backup)

---

## Success Metrics

- [ ] Total size: ~13KB (target achieved)
- [ ] "¿Cuáles son mis citas?" works correctly
- [ ] list_customer_bookings called exactly once
- [ ] No hallucinated data in responses
- [ ] Multilingual responses verified
- [ ] Error handling validated
- [ ] is_past flag handling correct
- [ ] Zero token waste on create/reschedule/cancel logic

---

**Documentation:** `/home/javort/Lab01-MCP/docs/booking_agent_optimization_analysis.md`
**Executive Summary:** `/home/javort/Lab01-MCP/docs/booking_agent_executive_summary.txt`
**Last Updated:** 2025-10-20
**Target:** Reduce to ~25KB (includes safety buffer)
