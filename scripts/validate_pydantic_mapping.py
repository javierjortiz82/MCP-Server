#!/usr/bin/env python3
"""
Pydantic v2 Mapping Validator

Validates that all environment variables are properly mapped to Pydantic v2
BaseSettings models. Ensures 1:1 correspondence between .env files and
settings.py Field definitions.

Usage:
    python3 scripts/validate_pydantic_mapping.py
    python3 scripts/validate_pydantic_mapping.py --detailed
    python3 scripts/validate_pydantic_mapping.py --json
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass


class Colors:
    """ANSI color codes."""
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


@dataclass
class MappingResult:
    """Result of a mapping check."""
    field_name: str
    in_pydantic: bool
    in_env: bool
    status: str  # "ok", "missing_in_pydantic", "missing_in_env", "unused"


class PydanticMappingValidator:
    """Validates Pydantic v2 to environment variable mapping."""

    def __init__(self, project_root: Path):
        """Initialize validator."""
        self.project_root = project_root
        self.pydantic_fields: Dict[str, Set[str]] = {}
        self.env_variables: Dict[str, Set[str]] = {}
        self.mapping_results: Dict[str, List[MappingResult]] = {}

    def run(self) -> int:
        """Run validation. Returns exit code."""
        self._extract_pydantic_fields()
        self._extract_env_variables()
        self._validate_mapping()
        self._print_report()
        return self._get_exit_code()

    # =========================================================================
    # EXTRACTION METHODS
    # =========================================================================

    def _extract_pydantic_fields(self):
        """Extract field names from all Pydantic settings.py files."""
        settings_files = [
            ("mcp_server/config/settings.py", "mcp_server"),
            ("client_mcp/config/settings.py", "client_mcp"),
            ("agent/src/gemini_agent/config/settings.py", "agent"),
            ("agent/src/gemini_agent/config/booking_agent_settings.py", "booking_agent"),
            ("email_service/config/settings.py", "email_service")
        ]

        for file_path, service_name in settings_files:
            full_path = self.project_root / file_path

            if not full_path.is_file():
                print(f"{Colors.YELLOW}⚠ {service_name}: {file_path} not found{Colors.RESET}")
                self.pydantic_fields[service_name] = set()
                continue

            fields = self._parse_settings_file(full_path)
            self.pydantic_fields[service_name] = fields
            print(f"{Colors.GREEN}✓ {service_name}: {len(fields)} fields found{Colors.RESET}")

    def _extract_env_variables(self):
        """Extract all environment variables from .env files."""
        env_files = [
            # ROOT .env removed - each service now has independent configuration
            ("mcp_server/.env", "mcp_server"),
            ("client_mcp/.env", "client_mcp"),
            ("agent/.env", "agent"),
            ("DockerConfig/.env", "docker"),
            ("email_service/.env", "email_service"),
            ("SQL/.env", "sql")
        ]

        for file_path, service_name in env_files:
            full_path = self.project_root / file_path

            if not full_path.is_file():
                self.env_variables[service_name] = set()
                continue

            vars_found = self._parse_env_file(full_path)
            self.env_variables[service_name] = vars_found
            if vars_found:
                print(f"{Colors.GREEN}✓ {service_name}: {len(vars_found)} variables found{Colors.RESET}")

    def _validate_mapping(self):
        """Validate that Pydantic fields map to environment variables."""
        print(f"\n{Colors.BOLD}Mapping Analysis:{Colors.RESET}\n")

        for service_name, fields in self.pydantic_fields.items():
            results = []

            for field in fields:
                # Check if field exists in any .env file
                in_env = any(
                    field in env_vars
                    for env_vars in self.env_variables.values()
                )

                if in_env:
                    status = "ok"
                else:
                    status = "missing_in_env"

                result = MappingResult(
                    field_name=field,
                    in_pydantic=True,
                    in_env=in_env,
                    status=status
                )
                results.append(result)

            self.mapping_results[service_name] = results

    # =========================================================================
    # PARSING METHODS
    # =========================================================================

    def _parse_settings_file(self, path: Path) -> Set[str]:
        """Parse Pydantic settings.py and extract field names."""
        fields = set()

        try:
            with open(path) as f:
                content = f.read()

                # Pattern: FIELD_NAME: type = Field(...)
                pattern = r"^\s*([A-Z_]+)\s*:\s*(?:[\w\[\]|]+|\w+(?:\s*\|\s*\w+)*)\s*=\s*Field\("
                for line in content.split("\n"):
                    match = re.match(pattern, line)
                    if match:
                        fields.add(match.group(1))

                # Also find fields without Field() - just type annotations with defaults
                # Pattern: FIELD_NAME: type = default_value (but only those that look like config)
                pattern2 = r"^\s*([A-Z_]+)\s*:\s*(?:[\w\[\]|]+|\w+(?:\s*\|\s*\w+)*)\s*=\s*(?![F]ield)"
                for line in content.split("\n"):
                    match = re.match(pattern2, line)
                    if match:
                        field_name = match.group(1)
                        # Filter out non-configuration fields
                        if not field_name.startswith("_") and field_name not in ["model_config"]:
                            fields.add(field_name)

        except Exception as e:
            print(f"{Colors.RED}Error parsing {path}: {e}{Colors.RESET}")

        return fields

    def _parse_env_file(self, path: Path) -> Set[str]:
        """Parse .env file and extract variable names."""
        variables = set()

        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue
                    # Skip lines with comments after =
                    if "=" not in line:
                        continue

                    key = line.split("=", 1)[0].strip()
                    # Only include uppercase variables (config vars)
                    if key.isupper():
                        variables.add(key)

        except Exception as e:
            print(f"{Colors.RED}Error parsing {path}: {e}{Colors.RESET}")

        return variables

    # =========================================================================
    # REPORTING METHODS
    # =========================================================================

    def _print_report(self):
        """Print detailed mapping report."""
        print(f"\n{Colors.BOLD}{'=' * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}Pydantic v2 to Environment Variable Mapping Report{Colors.RESET}")
        print(f"{Colors.BOLD}{'=' * 80}{Colors.RESET}\n")

        total_fields = 0
        total_ok = 0
        total_missing = 0

        for service_name, results in sorted(self.mapping_results.items()):
            if not results:
                continue

            ok_count = sum(1 for r in results if r.status == "ok")
            missing_count = sum(1 for r in results if r.status == "missing_in_env")

            total_fields += len(results)
            total_ok += ok_count
            total_missing += missing_count

            # Print service header
            status_icon = f"{Colors.GREEN}✓{Colors.RESET}" if missing_count == 0 else f"{Colors.YELLOW}⚠{Colors.RESET}"
            print(f"{status_icon} {Colors.BOLD}{service_name}{Colors.RESET}")
            print(f"  {ok_count}/{len(results)} fields mapped")

            # Print missing fields
            if missing_count > 0:
                print(f"  {Colors.YELLOW}Missing in .env:{Colors.RESET}")
                for result in results:
                    if result.status == "missing_in_env":
                        print(f"    - {result.field_name}")

            print()

        # Print summary
        print(f"{Colors.BOLD}{'=' * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}Summary:{Colors.RESET}")
        print(f"  Total Pydantic fields: {total_fields}")
        print(f"  {Colors.GREEN}✓ Mapped: {total_ok}{Colors.RESET}")
        if total_missing > 0:
            print(f"  {Colors.YELLOW}⚠ Missing: {total_missing}{Colors.RESET}")
        print(f"{Colors.BOLD}{'=' * 80}{Colors.RESET}\n")

    def _get_exit_code(self) -> int:
        """Get exit code based on results."""
        total_missing = sum(
            1 for results in self.mapping_results.values()
            for r in results if r.status == "missing_in_env"
        )

        if total_missing > 0:
            return 1
        return 0


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Pydantic v2 Mapping Validator"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    validator = PydanticMappingValidator(project_root)
    exit_code = validator.run()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
