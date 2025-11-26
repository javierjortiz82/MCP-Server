#!/usr/bin/env python3
"""Integration Validation Script for Demo Agent.

This script validates all integration points between the Demo Agent
and the MCP-Server ecosystem.

Usage:
    python scripts/validate_integration.py

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.0.0
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ============================================================================
# Color codes for terminal output
# ============================================================================

COLORS = {
    "GREEN": "\033[92m",
    "RED": "\033[91m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "END": "\033[0m",
}


def print_header(text: str) -> None:
    """Print a colored header."""
    print(f"\n{COLORS['BLUE']}{'=' * 80}")
    print(f"{text:^80}")
    print(f"{'=' * 80}{COLORS['END']}\n")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{COLORS['GREEN']}✅ {text}{COLORS['END']}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{COLORS['RED']}❌ {text}{COLORS['END']}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{COLORS['YELLOW']}⚠️  {text}{COLORS['END']}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{COLORS['BLUE']}ℹ️  {text}{COLORS['END']}")


# ============================================================================
# Validation Functions
# ============================================================================


def check_demo_agent_files() -> tuple[bool, list[str]]:
    """Check if all demo_agent module files exist."""
    print_header("1. Checking Demo Agent Files")

    required_files = [
        "demo_agent/__init__.py",
        "demo_agent/__main__.py",
        "demo_agent/agent.py",
        "demo_agent/main.py",
        "demo_agent/gemini_client.py",
        "demo_agent/logger.py",
        "demo_agent/config/settings.py",
        "demo_agent/db/connection.py",
        "demo_agent/db/models.py",
        "demo_agent/rate_limiter/token_bucket.py",
        "demo_agent/security/fingerprint.py",
        "demo_agent/security/ip_limiter.py",
        "demo_agent/security/captcha_handler.py",
        "demo_agent/models/requests.py",
        "demo_agent/models/responses.py",
        "demo_agent/tests/test_token_bucket.py",
        "demo_agent/tests/test_fingerprint.py",
        "demo_agent/tests/test_ip_limiter.py",
        "demo_agent/tests/test_captcha_handler.py",
    ]

    errors = []
    for file_path in required_files:
        full_path = Path(__file__).parent.parent.parent / file_path
        if full_path.exists():
            print_success(f"File exists: {file_path}")
        else:
            print_error(f"File missing: {file_path}")
            errors.append(f"Missing: {file_path}")

    return len(errors) == 0, errors


def check_prompt_manager_integration() -> tuple[bool, list[str]]:
    """Check if PromptManager integration is in place."""
    print_header("2. Checking PromptManager Integration")

    errors = []

    try:
        prompt_manager_file = (
            Path(__file__).parent.parent.parent
            / "agent/src/multi_agent/prompt_manager.py"
        )
        if not prompt_manager_file.exists():
            print_error(f"PromptManager file not found: {prompt_manager_file}")
            errors.append("PromptManager not found")
            return False, errors

        content = prompt_manager_file.read_text()

        # Check for get_demo_prompt method
        if "def get_demo_prompt(" in content:
            print_success("✓ get_demo_prompt() method exists in PromptManager")
        else:
            print_error("✗ get_demo_prompt() method NOT found in PromptManager")
            errors.append("get_demo_prompt() method missing")

        # Check for demo FAQ configuration
        if "demo_faqs" in content:
            print_success("✓ Demo FAQs configuration found")
        else:
            print_error("✗ Demo FAQs configuration NOT found")
            errors.append("Demo FAQs config missing")

    except Exception as e:
        print_error(f"Error checking PromptManager: {e}")
        errors.append(f"PromptManager check failed: {e}")

    return len(errors) == 0, errors


def check_database_schema_files() -> tuple[bool, list[str]]:
    """Check if database migration files exist."""
    print_header("3. Checking Database Schema Files")

    required_files = [
        "SQL/01_ddl/demo/01_demo_usage.sql",
        "SQL/01_ddl/demo/02_demo_audit_log.sql",
        "SQL/01_ddl/demo/03_demo_sessions.sql",
    ]

    errors = []
    for file_path in required_files:
        full_path = Path(__file__).parent.parent.parent / file_path
        if full_path.exists():
            print_success(f"SQL file exists: {file_path}")
        else:
            print_error(f"SQL file missing: {file_path}")
            errors.append(f"Missing SQL: {file_path}")

    # Check if demo tables are in deployment script
    try:
        deploy_script = (
            Path(__file__).parent.parent.parent
            / "SQL/05_orchestration/01_deploy.sql"
        )
        content = deploy_script.read_text()

        if "demo_usage" in content and "demo_audit_log" in content:
            print_success("✓ Demo tables referenced in deployment script")
        else:
            print_error("✗ Demo tables NOT found in deployment script")
            errors.append("Demo tables not in deploy.sql")

    except Exception as e:
        print_error(f"Error checking deployment script: {e}")
        errors.append(f"Deployment script check failed: {e}")

    return len(errors) == 0, errors


def check_docker_configuration() -> tuple[bool, list[str]]:
    """Check if Docker configuration is in place."""
    print_header("4. Checking Docker Configuration")

    errors = []

    try:
        docker_compose_file = (
            Path(__file__).parent.parent.parent
            / "DockerConfig/docker-compose.demo.yml"
        )
        if not docker_compose_file.exists():
            print_error(f"Docker Compose file not found: {docker_compose_file}")
            errors.append("docker-compose.demo.yml missing")
            return False, errors

        content = docker_compose_file.read_text()

        # Check for required service definition
        required_configs = [
            ("demo-agent service", "demo-agent:"),
            ("Port mapping", "8082:8082"),
            ("Health check", "healthcheck:"),
            ("Database URL", "DATABASE_URL"),
            ("Network definition", "mcp-network"),
        ]

        for name, pattern in required_configs:
            if pattern in content:
                print_success(f"✓ {name} configured")
            else:
                print_error(f"✗ {name} NOT configured")
                errors.append(f"{name} missing")

    except Exception as e:
        print_error(f"Error checking Docker config: {e}")
        errors.append(f"Docker config check failed: {e}")

    return len(errors) == 0, errors


def check_configuration_files() -> tuple[bool, list[str]]:
    """Check if configuration files are in place."""
    print_header("5. Checking Configuration Files")

    errors = []

    # Check .env.example
    try:
        env_file = (
            Path(__file__).parent.parent / ".env.example"
        )
        if env_file.exists():
            print_success("✓ .env.example file exists")
            content = env_file.read_text()
            required_vars = [
                "DATABASE_URL",
                "GEMINI_API_KEY",
                "RECAPTCHA_SECRET_KEY",
                "DEMO_MAX_TOKENS",
            ]
            for var in required_vars:
                if var in content:
                    print_success(f"  ✓ {var} configured")
                else:
                    print_warning(f"  ⚠️  {var} not in .env.example")
        else:
            print_error("✗ .env.example file missing")
            errors.append(".env.example missing")
    except Exception as e:
        print_error(f"Error checking .env.example: {e}")
        errors.append(f".env.example check failed: {e}")

    # Check prompt_versions.yaml
    try:
        prompt_versions_file = (
            Path(__file__).parent.parent.parent
            / "prompts/config/prompt_versions.yaml"
        )
        if prompt_versions_file.exists():
            content = prompt_versions_file.read_text()
            if "demo:" in content:
                print_success("✓ Demo agent configured in prompt_versions.yaml")
            else:
                print_error("✗ Demo agent NOT configured in prompt_versions.yaml")
                errors.append("Demo not in prompt_versions.yaml")
        else:
            print_error("✗ prompt_versions.yaml missing")
            errors.append("prompt_versions.yaml missing")
    except Exception as e:
        print_error(f"Error checking prompt_versions.yaml: {e}")
        errors.append(f"prompt_versions.yaml check failed: {e}")

    return len(errors) == 0, errors


def check_template_files() -> tuple[bool, list[str]]:
    """Check if Jinja2 template files exist."""
    print_header("6. Checking Template Files")

    required_files = [
        "prompts/templates/demo_agent/demo_agent.jinja2",
        "prompts/templates/demo_agent/modules/demo_instructions.jinja2",
        "prompts/data/demo_faqs.yaml",
    ]

    errors = []
    for file_path in required_files:
        full_path = Path(__file__).parent.parent.parent / file_path
        if full_path.exists():
            print_success(f"Template exists: {file_path}")
        else:
            print_error(f"Template missing: {file_path}")
            errors.append(f"Missing template: {file_path}")

    return len(errors) == 0, errors


def check_code_quality() -> tuple[bool, list[str]]:
    """Check if code quality artifacts exist."""
    print_header("7. Checking Code Quality Artifacts")

    errors = []

    # Check for test coverage
    test_dir = Path(__file__).parent.parent / "tests"
    if test_dir.exists():
        test_files = list(test_dir.glob("test_*.py"))
        if len(test_files) >= 4:
            print_success(f"✓ {len(test_files)} test files found")
        else:
            print_warning(f"⚠️  Only {len(test_files)} test files found (expected 4)")
    else:
        print_error("✗ Tests directory not found")
        errors.append("Tests directory missing")

    # Check for requirements.txt
    req_file = Path(__file__).parent.parent / "requirements.txt"
    if req_file.exists():
        print_success("✓ requirements.txt exists")
    else:
        print_error("✗ requirements.txt missing")
        errors.append("requirements.txt missing")

    # Check for pyproject.toml
    pyproject_file = Path(__file__).parent.parent / "pyproject.toml"
    if pyproject_file.exists():
        print_success("✓ pyproject.toml exists")
    else:
        print_error("✗ pyproject.toml missing")
        errors.append("pyproject.toml missing")

    return len(errors) == 0, errors


def check_documentation() -> tuple[bool, list[str]]:
    """Check if documentation files exist."""
    print_header("8. Checking Documentation")

    errors = []

    required_docs = [
        "docs/DEMO_AGENT_CODE_REVIEW.md",
        "docs/DEMO_AGENT_ITERACION_2.md",
        "docs/DEMO_AGENT_ITERACION_4.md",
        "demo_agent/README.md",
    ]

    for file_path in required_docs:
        full_path = Path(__file__).parent.parent.parent / file_path
        if full_path.exists():
            print_success(f"Doc exists: {file_path}")
        else:
            print_warning(f"Doc missing (optional): {file_path}")

    return len(errors) == 0, errors


# ============================================================================
# Main Validation Flow
# ============================================================================


def main() -> int:
    """Run all integration validation checks."""
    print_header("Demo Agent Integration Validation")
    print_info("Starting comprehensive integration validation...\n")

    checks = [
        ("Demo Agent Files", check_demo_agent_files),
        ("PromptManager Integration", check_prompt_manager_integration),
        ("Database Schema Files", check_database_schema_files),
        ("Docker Configuration", check_docker_configuration),
        ("Configuration Files", check_configuration_files),
        ("Template Files", check_template_files),
        ("Code Quality", check_code_quality),
        ("Documentation", check_documentation),
    ]

    results = []
    for name, check_func in checks:
        try:
            success, errors = check_func()
            results.append((name, success, errors))
        except Exception as e:
            print_error(f"Unexpected error in {name}: {e}")
            results.append((name, False, [str(e)]))

    # Print summary
    print_header("Integration Validation Summary")

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    for name, success, errors in results:
        if success:
            print_success(f"{name}: PASSED")
        else:
            print_error(f"{name}: FAILED")
            for error in errors:
                print_info(f"  → {error}")

    print(f"\n{COLORS['BLUE']}{'=' * 80}")
    print(
        f"Results: {COLORS['GREEN']}{passed}/{total} checks passed{COLORS['BLUE']}"
    )
    print(f"{'=' * 80}{COLORS['END']}\n")

    if passed == total:
        print_success("✅ All integration checks PASSED!")
        print_info(
            "Demo Agent is fully integrated with MCP-Server ecosystem."
        )
        return 0
    else:
        print_error(f"❌ {total - passed} checks FAILED")
        print_warning(
            "Please fix the issues above before proceeding with deployment."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
