# Google Gemini Vague Query Handling - Implementation Guide
**Date**: 2025-11-03
**Based on**: Google Gemini API Official Documentation
**Status**: 📋 Analysis & Recommendations

## 🎯 Google Gemini Best Practices for Vague Queries

### Core Principles from Google Gemini Docs

Based on official Google Gemini API documentation and best practices:

#### 1. **Clarity is Everything**
- Ambiguous instructions lead to illogical or repetitive responses
- **Solution**: Provide clear and specific instructions that prevent ambiguity
- **Implementation**: Use explicit decision trees and disambiguation rules in system prompts

#### 2. **Ask Clarifying Questions**
- When user queries are ambiguous (not enough info), ask for clarification
- **Key**: Gemini 2.5 Pro can identify ambiguities and ask clarifying questions naturally
- **Implementation**: Add explicit prompts to ask follow-up questions

#### 3. **Make Ambiguity Costly, Correctness Cheap**
- Structure prompts so ambiguity avoidance is rewarded
- Correctness should be the easiest path to take
- **Implementation**: Guide model toward disambiguated responses through examples and rules

#### 4. **Use System Instructions Effectively**
- System instructions process BEFORE user prompts
- Define how the model should behave and respond
- Perfect for: Role definition, goals, rules, context
- **NOT for**: Sensitive data, passwords, private keys

#### 5. **Explicit Decision Points**
- Translate goals into executable outlines with **explicit decision points**
- Use decision trees to guide the model
- Each decision should have clear criteria

#### 6. **Function Calling with Ambiguity**
- Use `temperature = 0` or low value for function calling
- Let model intelligently determine if a tool is needed
- Model should ask clarification questions BEFORE calling tools if needed

#### 7. **Enable Reasoning**
- Enabling "thinking" mode allows model to reason through requests
- Better for function call performance
- Recommended for: Complex disambiguation, multiple intent scenarios

---

## 📊 Current State Analysis of Templates

### Template Inventory
| Template | Type | Vague Query Handling | Rating |
|----------|------|---------------------|--------|
| router_classification | Intent Router | Basic keyword matching | ⭐⭐⭐ |
| booking_agent | Domain Agent | ✅ Now has explicit rules (v2025-11-03) | ⭐⭐⭐⭐ |
| sales_agent | Domain Agent | Implicit via quality_rules | ⭐⭐⭐ |
| general_agent | Domain Agent | Simple FAQ format | ⭐⭐ |

### Findings by Template

#### ✅ ROUTER_CLASSIFICATION.jinja2 (v1.0)
**Current State**:
- Has context awareness for conversation flow
- Identifies when user is responding to booking request
- Clear classification rules
- **Missing**: Explicit handling of ambiguous classification scenarios

**Improvement Opportunities**:
1. Add section for "Ambiguous Classification Cases"
2. Define confidence levels (certain vs uncertain)
3. Guide when to return "uncertain" vs forcing a classification
4. Add examples of conflicting signals (sales + booking intent)

---

#### ⭐ SALES_AGENT/sales_agent.jinja2
**Current State**:
- Has good role definition with quality principles
- Has anti-hallucination module
- Has quality_rules for product filtering
- Implements semantic matching logic
- **Missing**: Explicit vague query handling section

**Improvement Opportunities**:
1. Add "Handling Vague Product Queries" section
   - Example: "quiero algo para regalar" (too vague)
   - Example: "necesito un laptop pero barato" (conflicting requirements)
   - Example: "algo con buena relación precio-calidad" (subjective)

2. Add clarification strategy:
   - Ask for: budget, use case, brand preference, features
   - Use numbered options for categories
   - Guide through multi-step qualification

3. Add handling for budget ambiguity:
   - "barato" means different things to different people
   - Ask: "¿Cuál es tu presupuesto máximo?"
   - Show range examples

4. Add handling for quality ambiguity:
   - "bueno" is subjective
   - Ask: "¿Qué es importante para ti? (velocidad, durabilidad, precio, marca)"
   - Show tradeoff examples

---

#### ⚠️ GENERAL_AGENT.jinja2
**Current State**:
- Simple template-based FAQ responses
- Loads business info and policies
- No dynamic logic
- **Missing**: Handling of vague policy/info queries

**Improvement Opportunities**:
1. Add "Handling Vague Information Queries" section
   - Example: "¿Qué es caro?" (relative term)
   - Example: "¿Cuándo envían?" (depends on destination, product)
   - Example: "¿Tienen esto?" (too vague, what is "esto"?)

2. Add disambiguation for common vague questions:
   - Shipping: "¿A dónde envían?" → Ask location
   - Products: "¿Tienen X?" → Ask to clarify X
   - Hours: "¿Cuándo atienden?" → Show full schedule + online 24/7
   - Prices: "¿Cuánto cuesta?" → Ask what product
   - Policies: "¿Puedo devolver?" → Show different scenarios

3. Add proactive information:
   - When user asks vague question, offer multiple scenarios
   - Example: "¿Qué es tu horario?" → "Atendemos de lunes a viernes..."

---

## 🚀 Recommended Improvements by Priority

### PRIORITY 1: ROUTER (Medium Impact, High Reusability)
**Status**: ⏳ Recommended
**Effort**: 30 min

Create: `router_classification_vague_handling.md`
```
1. Add "Ambiguous Classification Cases" section
2. Define 3 scenarios:
   - Clear classification (high confidence)
   - Ambiguous classification (multiple signals)
   - Uncertain classification (not enough info)
3. Add examples and decision rules
4. Add instruction: When uncertain, lean toward booking (more specific)
```

**Files to Update**:
- `prompts/templates/base/router_classification.jinja2`
- `prompts/templates/router_classification.jinja2`

---

### PRIORITY 2: SALES AGENT (High Impact, Most Used)
**Status**: ⏳ Recommended
**Effort**: 1-2 hours

Create: `sales_agent/modules/vague_query_handling.jinja2`
```
1. Section: "Handling Vague Product Queries"
2. Define 5 common vague patterns:
   - Budget ambiguity ("algo barato")
   - Quality ambiguity ("algo bueno")
   - Purpose ambiguity ("para regalar")
   - Subjective terms ("moderno", "económico")
   - Missing specifics ("una cosa para...")

3. For each pattern:
   - Examples of vague queries
   - Clarification questions to ask
   - Follow-up options to show
   - Tool calling strategy

4. Add examples section with 6-8 vague query examples
```

**Guiding Principle**: Make clarification the "cheap" path, specificity the "rewarded" path

**Files to Update**:
- `prompts/templates/sales_agent/sales_agent.jinja2` (add include)
- Create: `prompts/templates/sales_agent/modules/vague_query_handling.jinja2`

---

### PRIORITY 3: GENERAL AGENT (Medium Impact, Common Use)
**Status**: ⏳ Recommended
**Effort**: 45 min - 1 hour

Enhance current template:
```
1. Add "Handling Vague Information Queries" section in general_agent.jinja2
2. Define disambiguation strategies for:
   - Location-dependent info (shipping, hours)
   - Product-dependent info (pricing, returns)
   - Relative terms (expensive, fast, good)

3. Add inline decision rules:
   - If customer asks "¿Cuándo envían?" → Ask location first
   - If customer asks "¿Cuál es la política?" → List all policies with links
   - If customer asks "¿Cuánto cuesta?" → Ask what product
```

**Files to Update**:
- `prompts/templates/base/general_agent.jinja2` (primary)
- `prompts/templates/general_agent.jinja2` (production)

---

## 📝 Implementation Template

### For ALL Templates - Standard Vague Query Section

```jinja2
{# ═══════════════════════════════════════════════════════ #}
{# HANDLING VAGUE/AMBIGUOUS QUERIES (Google Gemini Best Practice) #}
{# Based: Google Gemini API Docs - Prompt Design Strategies #}
{# ═══════════════════════════════════════════════════════ #}

## 🎯 Principle: Make Ambiguity Costly, Correctness Cheap

When user queries are VAGUE:
- ❌ DO NOT respond with generic fallback
- ✅ ASK CLARIFYING QUESTIONS (explicitly)
- ✅ OFFER STRUCTURED OPTIONS (numbered)
- ✅ SHOW EXAMPLES (provide context)

## 📊 Vague Query Patterns & Responses

### Pattern 1: [SPECIFIC TO AGENT]
- **Example**: "[vague query example]"
- **Ambiguity**: [what's missing]
- **Clarification Questions**:
  1. Question 1?
  2. Question 2?
- **Recommended Tool Call**: [which tool to call after clarification]

### Pattern N: ...

## 🔄 Decision Tree for Ambiguous Input

```
START
  ├─ Is query specific enough to proceed?
  │  ├─ YES → Proceed with tool call
  │  └─ NO → Go to "Ask Clarification"
  │
  └─ Ask Clarification
     ├─ Show numbered options (1️⃣ 2️⃣ 3️⃣)
     ├─ Wait for user selection
     └─ Then proceed with tool call
```

## ✅ Success Criteria
- User receives OPTIONS, not errors
- Clarification questions are EXPLICIT
- Options are NUMBERED and ACTIONABLE
- Model WAITS for response before tool calling
```

---

## 🔗 Google Gemini Best Practices Applied

| Gemini Best Practice | Implementation in Project |
|----------------------|---------------------------|
| **Clarity is Everything** | Explicit decision trees in templates |
| **Ask Clarifying Questions** | New vague_query_handling modules |
| **Make Ambiguity Costly** | Guide toward specificity with examples |
| **System Instructions** | Use system prompts to define behavior |
| **Explicit Decision Points** | Add decision trees for ambiguous input |
| **Function Calling + Ambiguity** | Ask before calling, low temperature |
| **Enable Reasoning** | Include reasoning_instructions module |

---

## 📈 Expected Impact

### User Experience
- ✅ No more generic "couldn't process" errors
- ✅ Clear guidance on what to provide
- ✅ Options instead of errors
- ✅ Natural clarification flow

### Code Quality
- ✅ All templates follow same pattern
- ✅ Easy to maintain and update
- ✅ Based on official Google guidelines
- ✅ Reusable components

### Metrics to Track
- Clarification questions asked (count)
- User satisfaction with guidance
- Successful disambiguation rate
- Error reduction

---

## 🗓️ Implementation Roadmap

```
Phase 1 (Done):
✅ Booking Agent - Added explicit vague query handling
✅ Documentation - This guide

Phase 2 (Recommended):
⏳ Router - Add ambiguous classification handling
⏳ Sales Agent - Add vague product query module
⏳ General Agent - Add vague info query section

Phase 3 (Future):
📅 Add A/B testing variants
📅 Add metrics/analytics
📅 Add confidence levels to responses
📅 Add multi-language support validation
```

---

## 🔗 References

**Official Google Gemini Documentation**:
- [Prompt Design Strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies)
- [System Instructions](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/system-instructions)
- [Function Calling](https://ai.google.dev/gemini-api/docs/function-calling)

**Key Principles**:
- Make ambiguity costly (discourage it through structure)
- Make correctness cheap (easy path to right answer)
- Use explicit decision points (guide model thinking)
- Ask clarifying questions (Gemini 2.5 can do this naturally)
- Enable reasoning (for complex disambiguation)

---

**Author**: Claude Code
**Last Updated**: 2025-11-03 19:00 UTC
**Status**: 📋 Analysis Complete - Implementation Ready
