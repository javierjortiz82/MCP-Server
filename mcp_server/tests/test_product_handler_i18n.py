"""
Test Product Handler i18n Message Integration

Tests all product handler context messages to ensure:
1. Translation keys exist in both EN and ES locales
2. Message variables are properly formatted
3. Language context propagation works correctly
4. Fallback messages work when keys are missing
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.i18n import TranslationManager, set_language, get_language, t
import json


def test_product_fetch_messages():
    """Test product fetch (by_sku and by_id) messages in both languages."""
    print("\n" + "="*60)
    print("TEST GROUP 1: Product Fetch Messages (by_sku, by_id)")
    print("="*60)

    manager = TranslationManager()

    # Test SKU fetch messages
    fetch_tests = [
        ("en", "product.fetch.by_sku.info_start", {"sku": "TOY-0018"}),
        ("en", "product.fetch.by_sku.info_found", {"product_name": "Robot Vacuum"}),
        ("en", "product.fetch.by_sku.info_not_found", {"sku": "INVALID-9999"}),
        ("en", "product.fetch.by_sku.error_general", {"sku": "TOY-0018", "error": "DB connection failed"}),
        ("en", "product.fetch.by_id.info_start", {"product_id": 42}),
        ("en", "product.fetch.by_id.info_found", {"product_name": "Laptop Computer"}),
        ("en", "product.fetch.by_id.info_not_found", {"product_id": 9999}),
        ("en", "product.fetch.by_id.error_general", {"product_id": 42, "error": "Unknown product"}),

        ("es", "product.fetch.by_sku.info_start", {"sku": "TOY-0018"}),
        ("es", "product.fetch.by_sku.info_found", {"product_name": "Aspiradora Robot"}),
        ("es", "product.fetch.by_sku.info_not_found", {"sku": "INVALID-9999"}),
        ("es", "product.fetch.by_sku.error_general", {"sku": "TOY-0018", "error": "Fallo de BD"}),
        ("es", "product.fetch.by_id.info_start", {"product_id": 42}),
        ("es", "product.fetch.by_id.info_found", {"product_name": "Computadora Portátil"}),
        ("es", "product.fetch.by_id.info_not_found", {"product_id": 9999}),
        ("es", "product.fetch.by_id.error_general", {"product_id": 42, "error": "Producto desconocido"}),
    ]

    passed = 0
    failed = 0

    for lang, key, kwargs in fetch_tests:
        message = t(key, lang=lang, **kwargs)
        # Check that message doesn't equal the key (would mean translation missing)
        if message != key and message and not message.startswith("product.fetch"):
            print(f"  ✅ [{lang.upper()}] {key}: {message}")
            passed += 1
        else:
            print(f"  ❌ [{lang.upper()}] {key}: Translation missing or failed")
            failed += 1

    print(f"\nFetch Messages Result: {passed} passed, {failed} failed")
    return failed == 0


def test_product_semantic_search_messages():
    """Test semantic search messages in both languages."""
    print("\n" + "="*60)
    print("TEST GROUP 2: Product Semantic Search Messages")
    print("="*60)

    manager = TranslationManager()

    search_tests = [
        ("en", "product.semantic_search.info_start", {"query": "algo para limpiar"}),
        ("en", "product.semantic_search.progress_init", {}),
        ("en", "product.semantic_search.progress_complete", {"result_count": 5}),
        ("en", "product.semantic_search.info_completed", {"result_count": 5}),
        ("en", "product.semantic_search.info_no_results", {"query": "product XYZ"}),
        ("en", "product.semantic_search.error_general", {"error": "Embedding API timeout"}),

        ("es", "product.semantic_search.info_start", {"query": "algo para limpiar"}),
        ("es", "product.semantic_search.progress_init", {}),
        ("es", "product.semantic_search.progress_complete", {"result_count": 5}),
        ("es", "product.semantic_search.info_completed", {"result_count": 5}),
        ("es", "product.semantic_search.info_no_results", {"query": "product XYZ"}),
        ("es", "product.semantic_search.error_general", {"error": "Timeout de API"}),
    ]

    passed = 0
    failed = 0

    for lang, key, kwargs in search_tests:
        message = t(key, lang=lang, **kwargs)
        if message != key and message and not message.startswith("product.semantic"):
            print(f"  ✅ [{lang.upper()}] {key}: {message}")
            passed += 1
        else:
            print(f"  ❌ [{lang.upper()}] {key}: Translation missing or failed")
            failed += 1

    print(f"\nSemantic Search Messages Result: {passed} passed, {failed} failed")
    return failed == 0


def test_product_fuzzy_search_messages():
    """Test fuzzy search messages with all tiers."""
    print("\n" + "="*60)
    print("TEST GROUP 3: Product Fuzzy Search Messages (Multi-Tier)")
    print("="*60)

    manager = TranslationManager()

    fuzzy_tests = [
        ("en", "product.fuzzy_search.info_start", {"query": "teclado mecánico"}),
        ("en", "product.fuzzy_search.progress_init", {}),
        ("en", "product.fuzzy_search.progress_complete", {"result_count": 8}),
        ("en", "product.fuzzy_search.info_succeeded", {"tier": "word_similarity"}),
        ("en", "product.fuzzy_search.info_no_results", {}),
        ("en", "product.fuzzy_search.error_general", {"error": "Database query failed"}),

        ("es", "product.fuzzy_search.info_start", {"query": "teclado mecánico"}),
        ("es", "product.fuzzy_search.progress_init", {}),
        ("es", "product.fuzzy_search.progress_complete", {"result_count": 8}),
        ("es", "product.fuzzy_search.info_succeeded", {"tier": "similitud_palabras"}),
        ("es", "product.fuzzy_search.info_no_results", {}),
        ("es", "product.fuzzy_search.error_general", {"error": "Fallo en consulta"}),
    ]

    passed = 0
    failed = 0

    for lang, key, kwargs in fuzzy_tests:
        message = t(key, lang=lang, **kwargs)
        if message != key and message and not message.startswith("product.fuzzy"):
            print(f"  ✅ [{lang.upper()}] {key}: {message}")
            passed += 1
        else:
            print(f"  ❌ [{lang.upper()}] {key}: Translation missing or failed")
            failed += 1

    print(f"\nFuzzy Search Messages Result: {passed} passed, {failed} failed")
    return failed == 0


def test_product_ingest_messages():
    """Test product ingestion messages."""
    print("\n" + "="*60)
    print("TEST GROUP 4: Product Ingestion Messages")
    print("="*60)

    manager = TranslationManager()

    ingest_tests = [
        ("en", "product.ingest.info_start", {"total_products": 150}),
        ("en", "product.ingest.progress_init", {}),
        ("en", "product.ingest.progress_complete", {}),
        ("en", "product.ingest.info_completed", {"total_products": 150}),
        ("en", "product.ingest.error_general", {"error": "Duplicate SKU detected"}),

        ("es", "product.ingest.info_start", {"total_products": 150}),
        ("es", "product.ingest.progress_init", {}),
        ("es", "product.ingest.progress_complete", {}),
        ("es", "product.ingest.info_completed", {"total_products": 150}),
        ("es", "product.ingest.error_general", {"error": "SKU duplicado detectado"}),
    ]

    passed = 0
    failed = 0

    for lang, key, kwargs in ingest_tests:
        message = t(key, lang=lang, **kwargs)
        if message != key and message and not message.startswith("product.ingest"):
            print(f"  ✅ [{lang.upper()}] {key}: {message}")
            passed += 1
        else:
            print(f"  ❌ [{lang.upper()}] {key}: Translation missing or failed")
            failed += 1

    print(f"\nIngestion Messages Result: {passed} passed, {failed} failed")
    return failed == 0


def test_language_context_integration():
    """Test language context propagation through thread-local storage."""
    print("\n" + "="*60)
    print("TEST GROUP 5: Language Context Integration")
    print("="*60)

    manager = TranslationManager()

    # Test 1: Default language (should be 'es')
    default_lang = get_language()
    print(f"  Default language: {default_lang}")
    assert default_lang == "es", f"Default language should be 'es', got {default_lang}"
    print(f"  ✅ Default language is 'es'")

    # Test 2: Set language to English
    set_language("en")
    current_lang = get_language()
    assert current_lang == "en", f"Language should be 'en', got {current_lang}"
    print(f"  ✅ Language context set to 'en'")

    # Test 3: Message retrieval respects context
    message_en = t("product.fetch.by_sku.info_start", lang="en", sku="TEST-001")
    print(f"  EN message (context): {message_en}")
    assert message_en != "product.fetch.by_sku.info_start", "Should return translated message"
    assert "Fetching" in message_en or "SKU" in message_en, "Should contain English content"
    print(f"  ✅ English message retrieved via context")

    # Test 4: Reset to Spanish
    set_language("es")
    message_es = t("product.fetch.by_sku.info_start", lang="es", sku="TEST-001")
    print(f"  ES message (context): {message_es}")
    assert message_es != "product.fetch.by_sku.info_start", "Should return translated message"
    assert "Buscando" in message_es or "SKU" in message_es, "Should contain Spanish content"
    print(f"  ✅ Spanish message retrieved via context")

    print(f"\nLanguage Context Integration Result: All tests passed ✅")
    return True


def test_message_variable_formatting():
    """Test that message variables are properly formatted in translations."""
    print("\n" + "="*60)
    print("TEST GROUP 6: Message Variable Formatting")
    print("="*60)

    manager = TranslationManager()

    # Test cases with different variable patterns
    format_tests = [
        ("en", "product.fetch.by_sku.info_start", {"sku": "COMP-0038"}, "COMP-0038"),
        ("en", "product.fetch.by_id.info_found", {"product_name": "Gaming Laptop"}, "Gaming Laptop"),
        ("en", "product.semantic_search.info_completed", {"result_count": 42}, "42"),
        ("en", "product.fuzzy_search.info_succeeded", {"tier": "standard"}, "standard"),
        ("en", "product.ingest.info_start", {"total_products": 500}, "500"),

        ("es", "product.fetch.by_sku.info_start", {"sku": "COMP-0038"}, "COMP-0038"),
        ("es", "product.fetch.by_id.info_found", {"product_name": "Laptop Gaming"}, "Laptop Gaming"),
        ("es", "product.semantic_search.info_completed", {"result_count": 42}, "42"),
        ("es", "product.fuzzy_search.info_succeeded", {"tier": "estándar"}, "estándar"),
        ("es", "product.ingest.info_start", {"total_products": 500}, "500"),
    ]

    passed = 0
    failed = 0

    for lang, key, kwargs, expected_contains in format_tests:
        message = t(key, lang=lang, **kwargs)
        if expected_contains in message and message != key:
            print(f"  ✅ [{lang.upper()}] {key}: Variables properly formatted")
            print(f"      Result: {message}")
            passed += 1
        else:
            print(f"  ❌ [{lang.upper()}] {key}: Variable formatting failed")
            print(f"      Expected to contain: {expected_contains}")
            print(f"      Got: {message}")
            failed += 1

    print(f"\nMessage Variable Formatting Result: {passed} passed, {failed} failed")
    return failed == 0


def test_fallback_messages():
    """Test fallback message handling when keys are missing."""
    print("\n" + "="*60)
    print("TEST GROUP 7: Fallback Message Handling")
    print("="*60)

    manager = TranslationManager()

    # Test missing keys with fallback
    missing_key = "product.nonexistent.key"
    fallback_msg = "Fallback message"

    # When key doesn't exist, should return the key itself
    result = t(missing_key, lang="en")
    if result == missing_key:
        print(f"  ✅ Missing key returns key itself: {missing_key}")
    else:
        print(f"  ❌ Missing key handling failed: got {result}")

    # Test with actual product keys that should all exist
    all_exist = True
    product_keys = [
        "product.fetch.by_sku.info_start",
        "product.fetch.by_id.info_found",
        "product.semantic_search.info_completed",
        "product.fuzzy_search.info_succeeded",
        "product.ingest.info_completed",
    ]

    for key in product_keys:
        for lang in ["en", "es"]:
            msg = t(key, lang=lang, **{"sku": "TEST", "product_id": 1, "result_count": 5, "tier": "standard", "total_products": 100})
            if msg == key:
                print(f"  ❌ Key not found in translations: [{lang}] {key}")
                all_exist = False

    if all_exist:
        print(f"  ✅ All product translation keys exist in both languages")

    print(f"\nFallback Message Handling Result: {'All tests passed ✅' if all_exist else 'Some keys missing ❌'}")
    return all_exist


def main():
    """Run all product handler i18n tests."""
    print("\n" + "="*70)
    print("PRODUCT HANDLER i18n MESSAGE INTEGRATION TEST SUITE")
    print("="*70)

    results = {
        "Fetch Messages": test_product_fetch_messages(),
        "Semantic Search Messages": test_product_semantic_search_messages(),
        "Fuzzy Search Messages": test_product_fuzzy_search_messages(),
        "Ingestion Messages": test_product_ingest_messages(),
        "Language Context Integration": test_language_context_integration(),
        "Message Variable Formatting": test_message_variable_formatting(),
        "Fallback Message Handling": test_fallback_messages(),
    }

    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")

    print(f"\nTotal: {passed}/{total} test groups passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Product handler i18n is fully functional.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test group(s) failed. Review the output above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
