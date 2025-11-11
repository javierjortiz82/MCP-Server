#!/usr/bin/env python3
"""Quick test script to verify multilingual support implementation.

This script tests:
1. PromptManager template loading
2. Multilingual instruction presence in templates
3. Backward compatibility with user_lang parameter
4. Deprecation notice documentation

Author: Lab01-MCP Team
Created: 2025-10-18
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "agent" / "src"))

from multi_agent.prompt_manager import PromptManager


def test_template_loading():
    """Test that templates load correctly with multilingual support."""
    # Initialize PromptManager
    manager = PromptManager()

    # Test router prompt (both languages should return same template)
    router_en = manager.get_router_prompt(user_lang="en")
    router_es = manager.get_router_prompt(user_lang="es")

    if router_en == router_es:
        pass
    else:
        return False

    if "MULTILINGUAL CLASSIFICATION" in router_en:
        pass
    else:
        return False

    # Test sales prompt
    sales_en = manager.get_sales_prompt(user_lang="en")
    sales_es = manager.get_sales_prompt(user_lang="es")

    if sales_en == sales_es:
        pass
    else:
        return False

    if "AUTOMATIC LANGUAGE DETECTION" in sales_en:
        pass
    else:
        return False

    # Test booking prompt
    booking_en = manager.get_booking_prompt(user_lang="en")
    booking_es = manager.get_booking_prompt(user_lang="es")

    if booking_en == booking_es:
        pass
    else:
        return False

    if "AUTOMATIC LANGUAGE DETECTION" in booking_en:
        pass
    else:
        return False

    # Test general prompt
    general_en = manager.get_general_prompt(user_lang="en")
    general_es = manager.get_general_prompt(user_lang="es")

    if general_en == general_es:
        pass
    else:
        return False

    if "AUTOMATIC LANGUAGE DETECTION" in general_en:
        pass
    else:
        return False

    # Test template path method
    path_en = manager._get_template_path("sales_agent/sales_agent.jinja2", "en")
    path_es = manager._get_template_path("sales_agent/sales_agent.jinja2", "es")

    if path_en == path_es == "base/sales_agent/sales_agent.jinja2":
        pass
    else:
        return False

    return True


def test_documentation():
    """Verify that documentation updates are in place."""
    prompt_manager_file = (
        Path(__file__).parent / "agent" / "src" / "multi_agent" / "prompt_manager.py"
    )

    with open(prompt_manager_file, encoding="utf-8") as f:
        content = f.read()

    if ".. deprecated:: 2025-10-18" in content:
        pass
    else:
        return False

    if "As of 2025-10-18, all templates use Gemini's automatic multilingual" in content:
        pass
    else:
        return False

    return True


def main():
    """Run all tests."""
    # Test template loading
    template_success = test_template_loading()

    # Test documentation
    doc_success = test_documentation()

    # Final summary

    if template_success and doc_success:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
