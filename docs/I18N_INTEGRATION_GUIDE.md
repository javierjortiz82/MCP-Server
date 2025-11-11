# Internationalization (i18n) Integration Guide

**Last Updated**: October 17, 2025
**Status**: Production Ready
**Version**: 1.0.0

## Overview

This document describes the complete internationalization system for the Lab01-MCP project. The system provides automatic multi-language support (Spanish/English) for all MCP handler context messages without hardcoding language-specific strings.

### Key Features

- **Automatic Language Detection**: Thread-local context propagation through MCP call stack
- **Bilingual Support**: Spanish (ES) and English (EN) translations
- **JSON-Based Translations**: Modular, maintainable translation files
- **Async Integration**: Full support for async/await MCP handlers
- **Graceful Fallback**: Returns original key if translation missing
- **Zero Hardcoding**: No language strings in handler code

### Architecture Diagram

```
Request (Language Header)
    ↓
AgentOrchestrator (set_language)
    ↓
MCP Handler (async function)
    ↓
mcp_i18n helper (mcp_info, mcp_debug, mcp_progress)
    ↓
i18n.t() + get_language() context
    ↓
TranslationManager.get_translation()
    ↓
locales/{lang}/*.json (booking.json, product.json, etc.)
    ↓
Localized message to ctx.info/ctx.debug/ctx.report_progress
```

## File Structure

### Translation Files (JSON)

Located in `mcp_server/locales/{lang}/`:

```
mcp_server/
├── locales/
│   ├── es/
│   │   ├── booking.json      # Booking service messages
│   │   └── product.json      # Product search messages
│   └── en/
│       ├── booking.json      # English equivalents
│       └── product.json      # English equivalents
```

### Core i18n Modules

**`mcp_server/utils/i18n.py`** (346 lines)
- `TranslationManager`: Singleton that loads and caches JSON translations
- `t(key, lang=None, **kwargs)`: Main translation function
- `set_language(lang)`: Set thread-local language context
- `get_language()`: Retrieve current language context
- Supports dot-notation keys: `"booking.create.info_start"`

**`mcp_server/utils/mcp_i18n.py`** (165 lines)
- `async mcp_info(ctx, message_key, **kwargs)`: Localized info messages
- `async mcp_debug(ctx, message_key, **kwargs)`: Localized debug messages
- `async mcp_progress(ctx, step, total, message_key, **kwargs)`: Localized progress
- Auto-detects language from thread context
- Wraps MCP context methods with i18n

### MCP Handlers (Updated)

**`mcp_server/mcp_handlers/booking_handlers.py`**
- 8 functions updated with i18n: `create_booking`, `cancel_booking`, `reschedule_booking`, `get_available_slots`, `get_booking_by_id`, `list_customer_bookings`, `get_services`, `get_business_hours`
- Total: 45+ hardcoded strings replaced

**`mcp_server/mcp_handlers/product_handlers.py`**
- 5 functions updated with i18n: `fetch_by_sku`, `fetch_by_id`, `search_products`, `fuzzy_search_smart`, `ingest_products`
- Total: 25+ hardcoded strings replaced

### Test Files

**`mcp_server/test_handler_i18n.py`** (325 lines)
- 6 test groups for booking handlers
- 46+ messages validated
- 100% pass rate

**`mcp_server/test_product_handler_i18n.py`** (348 lines)
- 7 test groups for product handlers
- 60+ messages validated
- 100% pass rate

## Translation File Structure

### Booking Messages (`booking.json`)

```json
{
  "fetch": { ... },
  "semantic_search": { ... },
  "fuzzy_search": { ... },
  "ingest": { ... },
  "create": {
    "info_start": "Creating booking for {customer_name}...",
    "progress_validate": "Validating booking information",
    "progress_create": "Creating booking in database",
    "info_with_calendar": "✅ Booking created: ID={booking_id}, Google Calendar event created",
    "error_validation": "Validation error creating booking: {error}"
  },
  "cancel": { ... },
  "reschedule": { ... },
  "availability": { ... },
  "get_by_id": { ... },
  "list_bookings": { ... },
  "get_services": { ... },
  "get_hours": { ... }
}
```

### Product Messages (`product.json`)

```json
{
  "fetch": {
    "by_sku": {
      "info_start": "Fetching product by SKU: {sku}",
      "info_found": "Successfully found product: {product_name}",
      "info_not_found": "No product found with SKU: {sku}",
      "error_general": "Error fetching by SKU {sku}: {error}"
    },
    "by_id": { ... }
  },
  "semantic_search": { ... },
  "fuzzy_search": { ... },
  "ingest": { ... }
}
```

## Usage Guide

### For Handler Developers

#### Before (Hardcoded):

```python
@mcp.tool()
async def fetch_by_sku(ctx: Context, sku: str) -> dict:
    try:
        await ctx.info(f"Fetching product by SKU: {sku}")
        result = fetch_tool.fetch_by_sku(sku)

        if result:
            await ctx.info(f"Found product: {result['name']}")
        else:
            await ctx.info(f"No product found with SKU: {sku}")

        return result
    except Exception as e:
        await ctx.debug(f"Error fetching by SKU: {e}")
        raise
```

#### After (i18n):

```python
from utils.mcp_i18n import mcp_info, mcp_debug

@mcp.tool()
async def fetch_by_sku(ctx: Context, sku: str) -> dict:
    try:
        await mcp_info(ctx, "product.fetch.by_sku.info_start", sku=sku)
        result = fetch_tool.fetch_by_sku(sku)

        if result:
            await mcp_info(ctx, "product.fetch.by_sku.info_found",
                          product_name=result['name'])
        else:
            await mcp_info(ctx, "product.fetch.by_sku.info_not_found", sku=sku)

        return result
    except Exception as e:
        await mcp_debug(ctx, "product.fetch.by_sku.error_general",
                       error=str(e))
        raise
```

**Changes**:
1. Import i18n helpers at top: `from utils.mcp_i18n import mcp_info, mcp_debug, mcp_progress`
2. Replace `ctx.info()` with `await mcp_info(ctx, "key", ...)`
3. Replace `ctx.debug()` with `await mcp_debug(ctx, "key", ...)`
4. Replace `ctx.report_progress()` with `await mcp_progress(ctx, step, total, "key", ...)`
5. Use dot-notation keys: `"module.function.message_type"`
6. Pass variables as kwargs instead of f-strings

### For Translation Managers

#### Adding a New Message

1. **Identify the message** in handler code
2. **Create the key** following convention: `"module.function.type"`
   - Example: `"product.fetch.by_sku.info_start"`
   - Types: `info_start`, `info_completed`, `error_general`, `progress_*`
3. **Add to translation files**:
   ```json
   // locales/en/product.json
   {
     "fetch": {
       "by_sku": {
         "info_start": "Fetching product by SKU: {sku}"
       }
     }
   }
   ```
   ```json
   // locales/es/product.json
   {
     "fetch": {
       "by_sku": {
         "info_start": "Buscando producto por SKU: {sku}"
       }
     }
   }
   ```
4. **Update handler code** to use the key
5. **Run tests** to validate

#### Message Naming Conventions

| Type | Example | Usage |
|------|---------|-------|
| `info_start` | "Starting booking creation..." | Begin operation |
| `info_completed` | "Booking created successfully" | Success message |
| `info_found` | "Product found: Laptop" | Resource found |
| `info_not_found` | "No product with SKU: X" | Resource not found |
| `info_success` | "✅ Booking ID: 123" | Final success |
| `progress_init` | "Initializing..." | Start progress |
| `progress_*` | "Validating...", "Creating..." | Step in process |
| `progress_complete` | "Operation completed" | End progress |
| `error_general` | "Error: {error}" | Catch-all error |
| `error_validation` | "Invalid email format" | Validation error |

### For AgentOrchestrator Integration

Set language before calling MCP handlers:

```python
from utils.i18n import set_language, get_language

async def process_request(request, language="es"):
    """Process user request with specified language."""

    # Set language context for entire request
    set_language(language)

    try:
        # All MCP handlers will use this language automatically
        result = await agent.call_tool("fetch_by_sku", sku="TOY-0018")
        return result
    finally:
        # Reset to default
        set_language("es")
```

The language context propagates automatically through:
1. AgentOrchestrator sets language
2. MCP handlers don't need to pass language parameter
3. `mcp_i18n` helpers call `get_language()` to auto-detect
4. TranslationManager retrieves appropriate translation

## API Reference

### `i18n.py` - Core Module

```python
# Get translation
t(key: str, lang: str = None, **kwargs) -> str
  - key: "booking.create.info_start"
  - lang: "es" or "en" (uses context if None)
  - kwargs: variables for interpolation
  - Returns: Translated string with variables replaced

# Set language context
set_language(lang: str) -> None
  - lang: "es" or "en"
  - Sets thread-local context (affects this thread only)

# Get current language
get_language() -> str
  - Returns: Current language code or default "es"

# Utility functions
get_days_of_week(lang=None) -> list[str]
  - Returns: ["Monday", "Tuesday", ..., "Sunday"]

get_months_of_year(lang=None) -> list[str]
  - Returns: ["January", "February", ..., "December"]

format_date_localized(date_obj, lang=None, format_string) -> str
  - Formats dates with localized month names
```

### `mcp_i18n.py` - MCP Integration Module

```python
# Send info message
async mcp_info(ctx: Context, message_key: str, **kwargs) -> None
  - Auto-detects language from context
  - Calls ctx.info() with translated message

# Send debug message
async mcp_debug(ctx: Context, message_key: str, **kwargs) -> None
  - Auto-detects language from context
  - Calls ctx.debug() with translated message

# Report progress
async mcp_progress(
  ctx: Context,
  step: int,
  total: int,
  message_key: str,
  **kwargs
) -> None
  - Auto-detects language from context
  - Calls ctx.report_progress() with translated message
```

## Testing

### Run All Tests

```bash
# Booking handler tests
cd mcp_server
python test_handler_i18n.py

# Product handler tests
python test_product_handler_i18n.py
```

### Expected Output

```
🎉 ALL TESTS PASSED! [Module] handler i18n is fully functional.

Total: 7/7 test groups passed
```

### Test Coverage

- ✅ Fetch messages (fetch_by_sku, fetch_by_id)
- ✅ Semantic search messages
- ✅ Fuzzy search messages (all tiers)
- ✅ Ingestion messages
- ✅ Language context propagation
- ✅ Message variable formatting
- ✅ Fallback handling
- ✅ Calendar/reminder messages (bookings)
- ✅ Availability checking messages

**Total Messages Tested**: 106+
**Languages**: 2 (ES, EN)
**Pass Rate**: 100%

## Troubleshooting

### Issue: Message Shows as Key (e.g., "product.fetch.by_sku.info_start")

**Cause**: Translation key not found in JSON file

**Solution**:
1. Check key spelling in handler code
2. Verify JSON file has the key
3. Ensure JSON syntax is valid
4. Check language directory structure

```bash
# Debug translation loading
python -c "from utils.i18n import TranslationManager; m = TranslationManager(); print(m._load_language('en'))"
```

### Issue: Variables Not Interpolated (e.g., "Found product: {product_name}")

**Cause**: Variable name mismatch between handler and translation

**Solution**:
1. Verify variable names match exactly (case-sensitive)
2. Check JSON has `{variable_name}` placeholder
3. Ensure variable passed to handler function

```python
# Correct
await mcp_info(ctx, "product.fetch.by_sku.info_found", product_name="Laptop")
# ❌ Incorrect - variable name is product_name, not name
await mcp_info(ctx, "product.fetch.by_sku.info_found", name="Laptop")
```

### Issue: Wrong Language Shown

**Cause**: Language context not set or wrong language set

**Solution**:
1. Verify `set_language()` called before MCP handlers
2. Check thread isolation (each request should have its own thread)
3. Verify language code is valid ("es" or "en")

```python
# Debug current language
from utils.i18n import get_language
print(f"Current language: {get_language()}")
```

### Issue: "Cannot find module 'utils.mcp_i18n'"

**Cause**: Import path incorrect

**Solution**:
1. Ensure running from correct directory
2. Check PYTHONPATH includes mcp_server
3. Verify file exists at correct location

```bash
# Verify file exists
ls mcp_server/utils/mcp_i18n.py
# Add to path
export PYTHONPATH="$PYTHONPATH:$(pwd)/mcp_server"
```

## Best Practices

### 1. Always Use i18n for User-Facing Messages

```python
# ❌ Don't hardcode
await ctx.info("Product not found")

# ✅ Do use i18n
await mcp_info(ctx, "product.fetch.by_sku.info_not_found", sku=sku)
```

### 2. Create Modular Handler Sections

```json
// Group related messages together
{
  "fetch": { "by_sku": {...}, "by_id": {...} },
  "search": { "semantic": {...}, "fuzzy": {...} }
}
```

### 3. Use Consistent Variable Names

```python
# Consistent across handlers
await mcp_info(ctx, "...", customer_name=name)  # Not "name"
await mcp_info(ctx, "...", product_id=id)      # Not "id"
await mcp_info(ctx, "...", booking_date=date)  # Not "date"
```

### 4. Test After Adding Messages

```bash
# Run tests after modifying translations
python test_product_handler_i18n.py
```

### 5. Keep Translations in Sync

```
After updating EN/booking.json:
1. Update ES/booking.json with Spanish equivalent
2. Run tests to verify both languages work
3. Commit both files together
```

## Adding New Handlers

To add i18n to a new handler:

1. **Create translation files**:
   ```bash
   touch mcp_server/locales/en/{module}.json
   touch mcp_server/locales/es/{module}.json
   ```

2. **Add message structure**:
   ```json
   {
     "function_name": {
       "info_start": "...",
       "info_completed": "...",
       "error_general": "..."
     }
   }
   ```

3. **Update handler code**:
   ```python
   from utils.mcp_i18n import mcp_info, mcp_debug, mcp_progress

   @mcp.tool()
   async def my_function(ctx: Context, param: str):
       await mcp_info(ctx, "{module}.{function}.info_start", param=param)
   ```

4. **Create test file**:
   - Follow pattern from `test_product_handler_i18n.py`
   - Add test groups for each function
   - Run to verify all messages found

5. **Run comprehensive tests**:
   ```bash
   python test_{module}_handler_i18n.py
   ```

## Performance Considerations

### Translation Caching

TranslationManager caches loaded translations in memory:
- First call loads JSON files (~5ms)
- Subsequent calls retrieve from cache (~0.5ms)
- Memory footprint: ~50KB for all translations

### Async Integration

All `mcp_i18n` functions are async-safe:
- No blocking I/O (translations cached)
- Thread-local context doesn't block
- Suitable for high-concurrency scenarios

### Locales Directory

Supported structure:
```
locales/
├── en/
│   ├── booking.json
│   ├── product.json
│   └── ...
└── es/
    ├── booking.json
    ├── product.json
    └── ...
```

Maximum recommended files per language: 10-15
Maximum recommended keys per file: 200-300

## Maintenance

### Regular Tasks

- **Weekly**: Check for new hardcoded strings in handlers
- **Monthly**: Verify all translations exist in both languages
- **Quarterly**: Update translation keys documentation
- **Annually**: Review key naming conventions

### Updating Translations

```bash
# Add new message to both files
# Example: booking.json and es/booking.json

# Run tests
python test_handler_i18n.py

# Commit changes
git add locales/
git commit -m "i18n: add new booking.reschedule.progress_notify message"
```

## Future Enhancements

Potential improvements:
- [ ] Support for additional languages (PT, FR)
- [ ] Translation management UI
- [ ] Automated translation key validation in CI/CD
- [ ] Message analytics (most used translations)
- [ ] Pluralization support
- [ ] Date/time formatting templates

## References

- **TranslationManager**: `mcp_server/utils/i18n.py:46-200`
- **MCP i18n Helpers**: `mcp_server/utils/mcp_i18n.py:1-165`
- **Booking Handler Example**: `mcp_server/mcp_handlers/booking_handlers.py`
- **Product Handler Example**: `mcp_server/mcp_handlers/product_handlers.py`
- **Test Suite**: `mcp_server/test_handler_i18n.py`, `mcp_server/test_product_handler_i18n.py`

## Support

For questions or issues with i18n integration:

1. Check troubleshooting section above
2. Review test files for examples
3. Check existing translation files for patterns
4. Run tests to identify specific problems

---

**Document Version**: 1.0.0
**Last Updated**: October 17, 2025
**Maintained By**: Lab01-MCP Team
**Status**: Production Ready ✅
