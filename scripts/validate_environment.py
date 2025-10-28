#!/usr/bin/env python3
"""
Lab01-MCP Environment Validation Script

Comprehensive pre-deployment environment validation ensuring:
- All required files and directories exist
- Environment variables are correctly configured
- Services can communicate (same DB, correct ports)
- Pydantic v2 configuration mapping is complete
- Docker infrastructure is properly set up

Based on best practices from:
- Terraform validate (declarative validation)
- Docker Compose config (YAML validation)
- 12-factor app (external config validation)

Usage:
    python3 scripts/validate_environment.py          # Normal mode
    python3 scripts/validate_environment.py --strict # Strict mode (fail on warnings)
    python3 scripts/validate_environment.py --json   # JSON output
    python3 scripts/validate_environment.py --quiet  # Minimal output

Exit codes:
    0 = All validations passed
    1 = Warnings found (non-blocking)
    2 = Errors found (blocking)
"""

import json
import os
import re
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import yaml


# Color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


@dataclass
class ValidationIssue:
    """Represents a validation issue (error, warning, or info)."""
    level: str  # "error", "warning", "info", "success"
    category: str
    message: str
    variable: Optional[str] = None
    file: Optional[str] = None
    suggestion: Optional[str] = None


class EnvironmentValidator:
    """Main validator for Lab01-MCP environment configuration."""

    def __init__(self, project_root: Path, strict: bool = False, quiet: bool = False):
        """Initialize validator with project root path."""
        self.project_root = project_root
        self.strict = strict
        self.quiet = quiet
        self.issues: List[ValidationIssue] = []
        self.env_vars: Dict[str, Dict[str, str]] = {}  # {file: {var: value}}
        self.docker_compose_vars: Dict[str, str] = {}
        self.pydantic_fields: Dict[str, List[str]] = {}

    def run(self) -> int:
        """Run all validations. Returns exit code."""
        if not self.quiet:
            self._print_header()

        # Run all validations
        self._validate_docker_installation()
        self._validate_directory_structure()
        self._validate_env_files()
        self._validate_docker_compose()
        self._validate_pydantic_mapping()
        self._validate_critical_variables()
        self._validate_service_configuration()
        self._validate_variable_format()
        self._validate_cross_references()
        self._validate_database_credentials_consistency()
        self._validate_embedding_model_consistency()
        self._validate_log_level_consistency()
        self._validate_error_pattern_consistency()
        self._validate_retry_strategy_consistency()
        self._validate_google_api_key_existence()
        self._validate_rate_limiting_consistency()

        # Print results
        if not self.quiet:
            self._print_results()
        else:
            self._print_summary()

        return self._get_exit_code()

    # =========================================================================
    # VALIDATION METHODS
    # =========================================================================

    def _validate_docker_installation(self):
        """Check if Docker and docker-compose are installed and running."""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self._add_issue(
                    ValidationIssue("success", "Docker", "Docker is installed")
                )
            else:
                self._add_issue(
                    ValidationIssue("error", "Docker", "Docker installation check failed")
                )
        except FileNotFoundError:
            self._add_issue(
                ValidationIssue("error", "Docker", "Docker is not installed")
            )

        # Check docker-compose
        try:
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self._add_issue(
                    ValidationIssue("success", "Docker", "docker-compose is installed")
                )
            else:
                self._add_issue(
                    ValidationIssue("error", "Docker", "docker-compose check failed")
                )
        except FileNotFoundError:
            self._add_issue(
                ValidationIssue("error", "Docker", "docker-compose is not installed")
            )

        # Check if Docker daemon is running
        try:
            subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                timeout=5,
                check=True
            )
            self._add_issue(
                ValidationIssue("success", "Docker", "Docker daemon is running")
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            self._add_issue(
                ValidationIssue("warning", "Docker", "Docker daemon may not be running"),
            )

    def _validate_directory_structure(self):
        """Validate that required directories exist."""
        required_dirs = [
            "mcp_server",
            "client_mcp",
            "agent",
            "email_service",
            "DockerConfig",
            "SQL",
            "scripts",
            "docs"
        ]

        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.is_dir():
                self._add_issue(
                    ValidationIssue("success", "Structure", f"Directory '{dir_name}' exists")
                )
            else:
                self._add_issue(
                    ValidationIssue("error", "Structure", f"Directory '{dir_name}' not found")
                )

    def _validate_env_files(self):
        """Validate that .env files exist and are readable."""
        env_files = {
            # ROOT .env removed - each service now has independent configuration
            "mcp_server/.env": "mcp_server",
            "client_mcp/.env": "client_mcp",
            "agent/.env": "agent",
            "email_service/.env": "email_service",
            "DockerConfig/.env": "docker",
            "SQL/.env": "sql"
        }

        for env_file, service in env_files.items():
            env_path = self.project_root / env_file
            if env_path.is_file():
                self._add_issue(
                    ValidationIssue("success", "Files", f"{env_file} exists")
                )
                # Parse env file
                self._parse_env_file(env_path, service)
            else:
                self._add_issue(
                    ValidationIssue("warning", "Files", f"{env_file} not found", file=env_file)
                )

    def _validate_docker_compose(self):
        """Validate docker-compose.yml syntax and structure."""
        docker_compose_path = self.project_root / "DockerConfig" / "docker-compose.yml"

        if not docker_compose_path.is_file():
            self._add_issue(
                ValidationIssue("error", "Docker", "docker-compose.yml not found")
            )
            return

        self._add_issue(
            ValidationIssue("success", "Docker", "docker-compose.yml found")
        )

        # Validate YAML syntax
        try:
            with open(docker_compose_path) as f:
                compose_config = yaml.safe_load(f)
            self._add_issue(
                ValidationIssue("success", "Docker", "docker-compose.yml YAML syntax valid")
            )
        except yaml.YAMLError as e:
            self._add_issue(
                ValidationIssue("error", "Docker", f"docker-compose.yml YAML error: {e}")
            )
            return

        # Extract environment variable references
        if "services" in compose_config:
            for service_name, service_config in compose_config["services"].items():
                if "environment" in service_config:
                    for var, value in service_config["environment"].items():
                        if isinstance(value, str) and "${" in value:
                            # Extract variable name
                            match = re.search(r"\$\{([^:}]+)", value)
                            if match:
                                self.docker_compose_vars[match.group(1)] = service_name

    def _validate_pydantic_mapping(self):
        """Validate Pydantic v2 settings mapping."""
        settings_files = [
            ("mcp_server/config/settings.py", "mcp_server"),
            ("client_mcp/config/settings.py", "client_mcp"),
            ("agent/src/gemini_agent/config/settings.py", "agent"),
            ("email_service/config/settings.py", "email_service")
        ]

        for settings_file, service_name in settings_files:
            settings_path = self.project_root / settings_file
            if not settings_path.is_file():
                self._add_issue(
                    ValidationIssue("warning", "Pydantic", f"{service_name}: {settings_file} not found")
                )
                continue

            # Parse Field definitions from settings.py
            fields = self._extract_pydantic_fields(settings_path)
            self.pydantic_fields[service_name] = fields

            self._add_issue(
                ValidationIssue(
                    "success",
                    "Pydantic",
                    f"{service_name}: Found {len(fields)} Pydantic fields"
                )
            )

    def _validate_critical_variables(self):
        """Validate that critical variables are defined in each service."""
        critical_vars_by_service = {
            "mcp_server": ["GOOGLE_API_KEY", "DATABASE_URL", "SCHEMA_NAME", "EMBEDDING_MODEL"],
            "email_service": ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "DATABASE_URL", "SCHEMA_NAME"],
            "agent": ["GOOGLE_API_KEY", "MODEL"],
            "client_mcp": ["GOOGLE_API_KEY", "DATABASE_URL", "MCP_HOST", "MCP_PORT", "SCHEMA_NAME"],
            "sql": ["GOOGLE_API_KEY", "DATABASE_URL", "SCHEMA_NAME"]
        }

        # Check each service has its critical variables
        for service_name, required_vars in critical_vars_by_service.items():
            service_env = self.env_vars.get(service_name, {})

            for var in required_vars:
                if var in service_env:
                    value = service_env[var]
                    if value.startswith("your") or value.startswith("CHANGE_ME"):
                        self._add_issue(
                            ValidationIssue(
                                "error",
                                "Critical Vars",
                                f"{service_name}: {var} not configured (placeholder value)",
                                variable=var,
                                suggestion=f"Set actual value in {service_name}/.env"
                            )
                        )
                    else:
                        self._add_issue(
                            ValidationIssue("success", "Critical Vars", f"{service_name}: {var} is configured")
                        )
                else:
                    self._add_issue(
                        ValidationIssue(
                            "warning",
                            "Critical Vars",
                            f"{service_name}: {var} is missing (may use default)",
                            variable=var,
                            suggestion=f"Add {var} to {service_name}/.env if needed"
                        )
                    )

    def _validate_service_configuration(self):
        """Validate individual service configurations."""
        # Map Docker service names to their .env file sources
        services_config = {
            "postgres": ("docker", ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]),
            "mcp_server": ("mcp_server", ["GOOGLE_API_KEY", "EMBEDDING_MODEL", "DATABASE_URL", "SCHEMA_NAME"]),
            "email_service": ("email_service", ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "DATABASE_URL"]),
            "agent": ("agent", ["GOOGLE_API_KEY", "MODEL"]),
            "client_mcp": ("client_mcp", ["GOOGLE_API_KEY", "DATABASE_URL", "MCP_HOST", "MCP_PORT"])
        }

        for service, (env_source, required_vars) in services_config.items():
            service_env = self.env_vars.get(env_source, {})

            for var in required_vars:
                if var in service_env:
                    self._add_issue(
                        ValidationIssue(
                            "success",
                            f"Service: {service}",
                            f"{var} configured in {env_source}/.env"
                        )
                    )
                else:
                    self._add_issue(
                        ValidationIssue(
                            "warning",
                            f"Service: {service}",
                            f"{var} not found in {env_source}/.env (may use default)",
                            variable=var
                        )
                    )

    def _validate_variable_format(self):
        """Validate format of specific variables across all services."""
        # Collect all environment variables from all services
        all_vars = {}
        for service_name, env_dict in self.env_vars.items():
            all_vars.update(env_dict)

        # Validate DATABASE_URL (should exist in mcp_server, client_mcp, email_service, sql)
        for service_name in ["mcp_server", "client_mcp", "email_service", "sql"]:
            service_env = self.env_vars.get(service_name, {})
            if "DATABASE_URL" in service_env:
                db_url = service_env["DATABASE_URL"]
                if not re.match(r"postgresql://[^:]+:[^@]+@[^:]+:\d+/\w+", db_url):
                    self._add_issue(
                        ValidationIssue(
                            "error",
                            "Format",
                            f"{service_name}: DATABASE_URL has invalid format",
                            variable="DATABASE_URL",
                            suggestion="Format: postgresql://user:pass@host:port/db"
                        )
                    )
                else:
                    self._add_issue(
                        ValidationIssue("success", "Format", f"{service_name}: DATABASE_URL format is valid")
                    )

        # Validate GOOGLE_API_KEY (should exist in mcp_server, agent, client_mcp, sql)
        for service_name in ["mcp_server", "agent", "client_mcp", "sql"]:
            service_env = self.env_vars.get(service_name, {})
            if "GOOGLE_API_KEY" in service_env:
                api_key = service_env["GOOGLE_API_KEY"]
                if api_key.startswith("AIza") and len(api_key) > 30:
                    self._add_issue(
                        ValidationIssue("success", "Format", f"{service_name}: GOOGLE_API_KEY format looks valid")
                    )
                elif not api_key.startswith("your"):
                    self._add_issue(
                        ValidationIssue(
                            "warning",
                            "Format",
                            f"{service_name}: GOOGLE_API_KEY format may be invalid"
                        )
                    )

        # Validate port numbers
        port_checks = [
            ("client_mcp", "MCP_PORT"),
            ("agent", "AGENT_PORT"),
            ("docker", "PGADMIN_PORT"),
            ("docker", "POSTGRES_PORT")
        ]
        for service_name, port_var in port_checks:
            service_env = self.env_vars.get(service_name, {})
            if port_var in service_env:
                try:
                    port = int(service_env[port_var])
                    if 1 <= port <= 65535:
                        self._add_issue(
                            ValidationIssue("success", "Format", f"{service_name}: {port_var} is valid ({port})")
                        )
                    else:
                        self._add_issue(
                            ValidationIssue("error", "Format", f"{service_name}: {port_var} out of range")
                        )
                except ValueError:
                    self._add_issue(
                        ValidationIssue("error", "Format", f"{service_name}: {port_var} is not a number")
                    )

    def _validate_cross_references(self):
        """Validate that services reference same database and correct ports."""
        # Get DockerConfig/.env (infrastructure)
        docker_env = self.env_vars.get("docker", {})

        # Check DATABASE_URL port consistency across services
        db_urls = {}
        for service_name in ["mcp_server", "client_mcp", "email_service", "sql"]:
            service_env = self.env_vars.get(service_name, {})
            if "DATABASE_URL" in service_env:
                db_urls[service_name] = service_env["DATABASE_URL"]

        # Extract database names and ports from all DATABASE_URLs
        db_names = set()
        db_ports = set()
        for service_name, db_url in db_urls.items():
            # Extract database name
            db_name_match = re.search(r"/(\w+)(?:\s|$)", db_url)
            if db_name_match:
                db_names.add(db_name_match.group(1))

            # Extract port
            port_match = re.search(r":(\d+)/", db_url)
            if port_match:
                db_ports.add(port_match.group(1))

        # Check that all services use same database name
        if len(db_names) > 1:
            self._add_issue(
                ValidationIssue(
                    "error",
                    "Cross-ref",
                    f"Services use different databases: {', '.join(sorted(db_names))}",
                    suggestion="All services should use same database name"
                )
            )
        elif len(db_names) == 1:
            self._add_issue(
                ValidationIssue("success", "Cross-ref", f"All services use database: {db_names.pop()}")
            )

        # Check port consistency
        if len(db_ports) > 1:
            self._add_issue(
                ValidationIssue(
                    "warning",
                    "Cross-ref",
                    f"Services use different database ports: {', '.join(sorted(db_ports))}",
                    suggestion="Verify if this is intentional (different environments)"
                )
            )
        elif len(db_ports) == 1 and "POSTGRES_PORT" in docker_env:
            db_port = db_ports.pop()
            postgres_port = docker_env["POSTGRES_PORT"]
            if db_port == postgres_port:
                self._add_issue(
                    ValidationIssue("success", "Cross-ref", f"Database port is consistent ({db_port})")
                )
            else:
                self._add_issue(
                    ValidationIssue(
                        "warning",
                        "Cross-ref",
                        f"Port mismatch: DATABASE_URL uses {db_port}, POSTGRES_PORT is {postgres_port}",
                        suggestion="Ensure ports match for local development"
                    )
                )

        # Validate all services in docker-compose use same database
        self._validate_service_db_consistency(db_urls.get("mcp_server", ""), list(db_names)[0] if db_names else None)

        # Check port conflicts across all services
        ports_used = {}
        port_checks = [
            ("docker", "POSTGRES_PORT"),
            ("docker", "PGADMIN_PORT"),
            ("client_mcp", "MCP_PORT"),
            ("agent", "AGENT_PORT")
        ]
        for service_name, port_var in port_checks:
            service_env = self.env_vars.get(service_name, {})
            if port_var in service_env:
                port = service_env[port_var]
                if port in ports_used:
                    self._add_issue(
                        ValidationIssue(
                            "error",
                            "Cross-ref",
                            f"Port conflict: {port} used by both {ports_used[port]} and {service_name}:{port_var}"
                        )
                    )
                else:
                    ports_used[port] = f"{service_name}:{port_var}"

        if not any(i.level == "error" for i in self.issues if i.category == "Cross-ref" and "conflict" in i.message.lower()):
            self._add_issue(
                ValidationIssue("success", "Cross-ref", "No port conflicts detected")
            )

    def _validate_service_db_consistency(self, root_database_url: str, root_db_name: str):
        """Validate that all services in docker-compose.yml use same database."""
        import yaml

        docker_compose_path = self.project_root / "DockerConfig" / "docker-compose.yml"
        if not docker_compose_path.is_file():
            return

        try:
            with open(docker_compose_path) as f:
                compose_raw = f.read()
        except Exception:
            return

        try:
            compose_config = yaml.safe_load(compose_raw)
        except Exception:
            compose_config = {}

        if "services" not in compose_config:
            return

        service_db_refs = {}
        services_checked = 0

        for service_name, service_config in compose_config.get("services", {}).items():
            if "environment" not in service_config:
                continue

            env_vars = service_config["environment"]
            if not isinstance(env_vars, dict):
                continue

            # Get the DATABASE_URL reference for this service
            service_db_url = env_vars.get("DATABASE_URL")
            if service_db_url:
                services_checked += 1
                service_db_refs[service_name] = service_db_url

        # If all services are using ${DATABASE_URL} interpolation (string pattern)
        if services_checked > 0:
            # Check if all services use variable reference (starts with ${)
            uses_interpolation = all(
                isinstance(v, str) and "${" in v
                for v in service_db_refs.values()
            )

            if uses_interpolation:
                # All services use variable interpolation - good!
                self._add_issue(
                    ValidationIssue(
                        "success",
                        "Cross-ref",
                        f"All {services_checked} services use database variable interpolation"
                    )
                )
            else:
                # Some services use hardcoded database URL - check for consistency
                db_names = set()
                for service_name, db_url in service_db_refs.items():
                    if isinstance(db_url, str):
                        # Try to extract database name
                        db_match = re.search(r"/(\w+)(?:\s|$)", db_url)
                        if db_match:
                            db_names.add(db_match.group(1))
                        else:
                            db_names.add("unknown")

                if len(db_names) > 1:
                    self._add_issue(
                        ValidationIssue(
                            "error",
                            "Cross-ref",
                            f"Services use different databases: {', '.join(sorted(db_names))}",
                            variable="DATABASE_URL",
                            suggestion="All services should use same DATABASE_URL from environment"
                        )
                    )
                elif root_db_name and db_names:
                    if root_db_name in db_names or "unknown" in db_names:
                        self._add_issue(
                            ValidationIssue(
                                "success",
                                "Cross-ref",
                                f"All services use same database: {root_db_name}"
                            )
                        )

    def _validate_database_credentials_consistency(self):
        """Validate that all services use consistent database credentials and schema."""
        # Services that should have DATABASE_URL
        db_services = ["mcp_server", "client_mcp", "email_service", "sql"]

        # Extract all DATABASE_URL components
        db_components = {}
        schemas = {}

        for service_name in db_services:
            service_env = self.env_vars.get(service_name, {})

            if "DATABASE_URL" in service_env:
                db_url = service_env["DATABASE_URL"]
                # Extract: postgresql://username:password@host:port/database
                match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(\w+)', db_url)
                if match:
                    username, password, host, port, dbname = match.groups()
                    db_components[service_name] = {
                        "username": username,
                        "password": password,
                        "host": host,
                        "port": port,
                        "database": dbname
                    }

            # Extract SCHEMA_NAME
            if "SCHEMA_NAME" in service_env:
                schemas[service_name] = service_env["SCHEMA_NAME"]

        if not db_components:
            return  # No services with DATABASE_URL found

        # Compare usernames
        usernames = set(comp["username"] for comp in db_components.values())
        if len(usernames) > 1:
            self._add_issue(
                ValidationIssue(
                    "error",
                    "DB Credentials",
                    f"Services use different database usernames: {', '.join(sorted(usernames))}",
                    variable="DATABASE_URL",
                    suggestion="All services should use same database username"
                )
            )
        elif len(usernames) == 1:
            self._add_issue(
                ValidationIssue("success", "DB Credentials", f"All services use username: {usernames.pop()}")
            )

        # Compare passwords
        passwords = set(comp["password"] for comp in db_components.values())
        if len(passwords) > 1:
            self._add_issue(
                ValidationIssue(
                    "error",
                    "DB Credentials",
                    f"Services use different database passwords ({len(passwords)} different)",
                    variable="DATABASE_URL",
                    suggestion="All services should use same database password"
                )
            )
        elif len(passwords) == 1:
            self._add_issue(
                ValidationIssue("success", "DB Credentials", "All services use same password")
            )

        # Compare hosts
        hosts = set(comp["host"] for comp in db_components.values())
        if len(hosts) > 1:
            self._add_issue(
                ValidationIssue(
                    "warning",
                    "DB Credentials",
                    f"Services use different database hosts: {', '.join(sorted(hosts))}",
                    suggestion="Verify if this is intentional (different environments)"
                )
            )
        elif len(hosts) == 1:
            self._add_issue(
                ValidationIssue("success", "DB Credentials", f"All services use host: {hosts.pop()}")
            )

        # Compare SCHEMA_NAME
        if schemas:
            schema_values = set(schemas.values())
            if len(schema_values) > 1:
                self._add_issue(
                    ValidationIssue(
                        "error",
                        "DB Credentials",
                        f"Services use different SCHEMA_NAME values: {', '.join(sorted(schema_values))}",
                        variable="SCHEMA_NAME",
                        suggestion="All services should use same SCHEMA_NAME"
                    )
                )
            elif len(schema_values) == 1:
                self._add_issue(
                    ValidationIssue("success", "DB Credentials", f"All services use schema: {schema_values.pop()}")
                )

    def _validate_embedding_model_consistency(self):
        """Validate EMBEDDING_MODEL consistency across services (WARNING only).

        Different embedding models may be intentional for testing or migration purposes.
        """
        # Services that use EMBEDDING_MODEL
        embedding_services = ["mcp_server", "sql"]

        embedding_models = {}
        for service_name in embedding_services:
            service_env = self.env_vars.get(service_name, {})
            if "EMBEDDING_MODEL" in service_env:
                embedding_models[service_name] = service_env["EMBEDDING_MODEL"]

        if not embedding_models:
            return  # No services with EMBEDDING_MODEL found

        # Check consistency
        model_values = set(embedding_models.values())
        if len(model_values) > 1:
            models_list = [f"{svc}={model}" for svc, model in embedding_models.items()]
            self._add_issue(
                ValidationIssue(
                    "warning",
                    "Embedding Model",
                    f"Services use different embedding models: {', '.join(models_list)}",
                    variable="EMBEDDING_MODEL",
                    suggestion="Verify this is intentional (different models = incompatible vector searches)"
                )
            )
        elif len(model_values) == 1:
            self._add_issue(
                ValidationIssue("success", "Embedding Model", f"All services use: {model_values.pop()}")
            )

    def _validate_log_level_consistency(self):
        """Validate LOG_LEVEL consistency across all services."""
        # All services that have LOG_LEVEL
        log_services = ["mcp_server", "agent", "client_mcp", "email_service", "sql"]

        log_levels = {}
        for service_name in log_services:
            service_env = self.env_vars.get(service_name, {})
            if "LOG_LEVEL" in service_env:
                log_levels[service_name] = service_env["LOG_LEVEL"].upper()

        if not log_levels:
            return

        # Check consistency
        level_values = set(log_levels.values())
        if len(level_values) > 1:
            levels_list = [f"{svc}={level}" for svc, level in log_levels.items()]
            self._add_issue(
                ValidationIssue(
                    "warning",
                    "Log Level",
                    f"Services use different LOG_LEVEL: {', '.join(levels_list)}",
                    variable="LOG_LEVEL",
                    suggestion="Consider using same LOG_LEVEL in production (recommended: INFO or WARNING)"
                )
            )
        elif len(level_values) == 1:
            self._add_issue(
                ValidationIssue("success", "Log Level", f"All services use LOG_LEVEL: {level_values.pop()}")
            )

    def _validate_error_pattern_consistency(self):
        """Validate error pattern detection consistency across services."""
        # Services that use error patterns
        pattern_services = ["agent", "client_mcp"]

        cache_patterns = {}
        rate_limit_patterns = {}

        for service_name in pattern_services:
            service_env = self.env_vars.get(service_name, {})
            if "CACHE_ERROR_PATTERNS" in service_env:
                cache_patterns[service_name] = service_env["CACHE_ERROR_PATTERNS"]
            if "RATE_LIMIT_ERROR_PATTERNS" in service_env:
                rate_limit_patterns[service_name] = service_env["RATE_LIMIT_ERROR_PATTERNS"]

        # Validate CACHE_ERROR_PATTERNS consistency
        if cache_patterns:
            pattern_values = set(cache_patterns.values())
            if len(pattern_values) > 1:
                self._add_issue(
                    ValidationIssue(
                        "warning",
                        "Error Patterns",
                        f"Services use different CACHE_ERROR_PATTERNS",
                        variable="CACHE_ERROR_PATTERNS",
                        suggestion="Use same patterns for consistent cache error detection"
                    )
                )
            elif len(pattern_values) == 1:
                self._add_issue(
                    ValidationIssue("success", "Error Patterns", "CACHE_ERROR_PATTERNS is consistent")
                )

        # Validate RATE_LIMIT_ERROR_PATTERNS consistency
        if rate_limit_patterns:
            pattern_values = set(rate_limit_patterns.values())
            if len(pattern_values) > 1:
                self._add_issue(
                    ValidationIssue(
                        "warning",
                        "Error Patterns",
                        f"Services use different RATE_LIMIT_ERROR_PATTERNS",
                        variable="RATE_LIMIT_ERROR_PATTERNS",
                        suggestion="Use same patterns for consistent rate limit detection"
                    )
                )
            elif len(pattern_values) == 1:
                self._add_issue(
                    ValidationIssue("success", "Error Patterns", "RATE_LIMIT_ERROR_PATTERNS is consistent")
                )

    def _validate_retry_strategy_consistency(self):
        """Validate retry configuration consistency across services."""
        # Services with retry configuration
        retry_services = {
            "agent": ["RETRY_MAX_ATTEMPTS", "RETRY_INITIAL_DELAY_MS"],
            "client_mcp": ["RETRY_MAX_ATTEMPTS", "RETRY_INITIAL_DELAY_MS"],
            "email_service": ["EMAIL_RETRY_MAX_ATTEMPTS"]  # Different naming convention
        }

        max_attempts = {}
        initial_delays = {}

        for service_name, retry_vars in retry_services.items():
            service_env = self.env_vars.get(service_name, {})

            # Check RETRY_MAX_ATTEMPTS or EMAIL_RETRY_MAX_ATTEMPTS
            if "RETRY_MAX_ATTEMPTS" in service_env:
                max_attempts[service_name] = service_env["RETRY_MAX_ATTEMPTS"]
            elif "EMAIL_RETRY_MAX_ATTEMPTS" in service_env:
                max_attempts[service_name] = service_env["EMAIL_RETRY_MAX_ATTEMPTS"]

            # Check RETRY_INITIAL_DELAY_MS
            if "RETRY_INITIAL_DELAY_MS" in service_env:
                initial_delays[service_name] = service_env["RETRY_INITIAL_DELAY_MS"]

        # Validate max attempts consistency
        if max_attempts:
            attempt_values = set(max_attempts.values())
            if len(attempt_values) > 1:
                attempts_list = [f"{svc}={val}" for svc, val in max_attempts.items()]
                self._add_issue(
                    ValidationIssue(
                        "warning",
                        "Retry Config",
                        f"Services use different retry max attempts: {', '.join(attempts_list)}",
                        suggestion="Consider using consistent retry strategy across services"
                    )
                )
            elif len(attempt_values) == 1:
                self._add_issue(
                    ValidationIssue("success", "Retry Config", f"All services use retry max attempts: {attempt_values.pop()}")
                )

        # Validate initial delay consistency
        if initial_delays:
            delay_values = set(initial_delays.values())
            if len(delay_values) > 1:
                delays_list = [f"{svc}={val}ms" for svc, val in initial_delays.items()]
                self._add_issue(
                    ValidationIssue(
                        "warning",
                        "Retry Config",
                        f"Services use different retry initial delays: {', '.join(delays_list)}",
                        suggestion="Consider using consistent retry backoff strategy"
                    )
                )
            elif len(delay_values) == 1:
                self._add_issue(
                    ValidationIssue("success", "Retry Config", f"All services use retry initial delay: {delay_values.pop()}ms")
                )

    def _validate_google_api_key_existence(self):
        """Validate that GOOGLE_API_KEY exists in required services (WARNING only).

        Different API keys per service may be intentional for independent quota tracking.
        """
        # Services that require GOOGLE_API_KEY
        api_key_services = ["mcp_server", "agent", "client_mcp", "sql"]

        services_with_key = []
        services_without_key = []

        for service_name in api_key_services:
            service_env = self.env_vars.get(service_name, {})
            if "GOOGLE_API_KEY" in service_env:
                api_key = service_env["GOOGLE_API_KEY"]
                if api_key and not api_key.startswith("your"):
                    services_with_key.append(service_name)
                else:
                    services_without_key.append(service_name)
            else:
                services_without_key.append(service_name)

        # Report services with keys (success)
        if services_with_key:
            self._add_issue(
                ValidationIssue(
                    "success",
                    "API Keys",
                    f"{len(services_with_key)}/{len(api_key_services)} services have GOOGLE_API_KEY configured"
                )
            )

        # Report services without keys (warning)
        if services_without_key:
            self._add_issue(
                ValidationIssue(
                    "warning",
                    "API Keys",
                    f"Services missing GOOGLE_API_KEY: {', '.join(services_without_key)}",
                    variable="GOOGLE_API_KEY",
                    suggestion="Add GOOGLE_API_KEY to service .env files (or verify if intentional)"
                )
            )

        # Note: We do NOT compare API key values - different keys per service is intentional

    def _validate_rate_limiting_consistency(self):
        """Validate rate limiting configuration consistency across services."""
        # Services with rate limiting
        rate_limit_services = ["agent", "client_mcp"]

        rate_limiting_enabled = {}
        max_concurrent = {}

        for service_name in rate_limit_services:
            service_env = self.env_vars.get(service_name, {})

            if "ENABLE_RATE_LIMITING" in service_env:
                # Convert to boolean
                value = service_env["ENABLE_RATE_LIMITING"]
                rate_limiting_enabled[service_name] = value.lower() in ["true", "1", "yes"]

            if "MAX_CONCURRENT_REQUESTS" in service_env:
                max_concurrent[service_name] = service_env["MAX_CONCURRENT_REQUESTS"]

        # Validate ENABLE_RATE_LIMITING consistency
        if rate_limiting_enabled:
            enabled_values = set(rate_limiting_enabled.values())
            if len(enabled_values) > 1:
                config_list = [f"{svc}={val}" for svc, val in rate_limiting_enabled.items()]
                self._add_issue(
                    ValidationIssue(
                        "warning",
                        "Rate Limiting",
                        f"Services have different ENABLE_RATE_LIMITING: {', '.join(config_list)}",
                        suggestion="Consider consistent rate limiting policy across services"
                    )
                )
            elif len(enabled_values) == 1:
                status = "enabled" if enabled_values.pop() else "disabled"
                self._add_issue(
                    ValidationIssue("success", "Rate Limiting", f"Rate limiting is {status} across services")
                )

        # Validate MAX_CONCURRENT_REQUESTS consistency
        if max_concurrent:
            concurrent_values = set(max_concurrent.values())
            if len(concurrent_values) > 1:
                config_list = [f"{svc}={val}" for svc, val in max_concurrent.items()]
                self._add_issue(
                    ValidationIssue(
                        "info",
                        "Rate Limiting",
                        f"Services use different MAX_CONCURRENT_REQUESTS: {', '.join(config_list)}",
                        suggestion="Different limits may be intentional based on service workload"
                    )
                )
            elif len(concurrent_values) == 1:
                self._add_issue(
                    ValidationIssue("success", "Rate Limiting", f"All services use MAX_CONCURRENT_REQUESTS: {concurrent_values.pop()}")
                )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _parse_env_file(self, env_path: Path, service: str):
        """Parse a .env file and extract variables."""
        env_vars = {}
        try:
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)

                        # Remove inline comments (everything after # that's not in quotes)
                        # Simple approach: if # exists and not inside quotes, split there
                        if "#" in value:
                            # Check if # is inside quotes
                            in_quotes = False
                            quote_char = None
                            for i, char in enumerate(value):
                                if char in ['"', "'"] and (i == 0 or value[i-1] != "\\"):
                                    if not in_quotes:
                                        in_quotes = True
                                        quote_char = char
                                    elif char == quote_char:
                                        in_quotes = False
                                elif char == "#" and not in_quotes:
                                    value = value[:i]
                                    break

                        # Remove quotes if present and strip whitespace
                        value = value.strip().strip('"\'').strip()
                        env_vars[key.strip()] = value
        except Exception as e:
            self._add_issue(
                ValidationIssue("error", "Files", f"Failed to parse {env_path}: {e}")
            )

        self.env_vars[service] = env_vars

    def _extract_pydantic_fields(self, settings_path: Path) -> List[str]:
        """Extract Pydantic Field names from settings.py file."""
        fields = []
        try:
            with open(settings_path) as f:
                content = f.read()
                # Find all Field(...) definitions
                pattern = r"(\w+):\s*(?:[\w\[\]|]+)\s*=\s*Field\("
                matches = re.findall(pattern, content)
                fields = list(set(matches))  # Remove duplicates
        except Exception as e:
            pass  # Silently fail, will be reported elsewhere

        return sorted(fields)

    def _add_issue(self, issue: ValidationIssue):
        """Add a validation issue to the list."""
        self.issues.append(issue)

    def _get_exit_code(self) -> int:
        """Determine exit code based on issues."""
        error_count = sum(1 for i in self.issues if i.level == "error")
        warning_count = sum(1 for i in self.issues if i.level == "warning")

        if error_count > 0:
            return 2
        if warning_count > 0 and self.strict:
            return 1
        return 0

    # =========================================================================
    # OUTPUT METHODS
    # =========================================================================

    def _print_header(self):
        """Print validation header."""
        print("\n" + "=" * 70)
        print(f"{Colors.BOLD}{Colors.BLUE}Lab01-MCP Environment Validation{Colors.RESET}")
        print("=" * 70 + "\n")

    def _print_results(self):
        """Print detailed validation results."""
        # Group issues by category
        by_category = defaultdict(list)
        for issue in self.issues:
            by_category[issue.category].append(issue)

        # Print each category
        for category in sorted(by_category.keys()):
            issues = by_category[category]
            print(f"{Colors.BOLD}{Colors.CYAN}[{category}]{Colors.RESET}")
            for issue in issues:
                self._print_issue(issue)
            print()

        # Print summary
        self._print_summary()

    def _print_issue(self, issue: ValidationIssue):
        """Print a single issue."""
        if issue.level == "success":
            icon = f"{Colors.GREEN}✓{Colors.RESET}"
        elif issue.level == "error":
            icon = f"{Colors.RED}✗{Colors.RESET}"
        elif issue.level == "warning":
            icon = f"{Colors.YELLOW}⚠{Colors.RESET}"
        else:
            icon = "ℹ"

        print(f"  {icon} {issue.message}")

        if issue.suggestion:
            print(f"    {Colors.CYAN}→ {issue.suggestion}{Colors.RESET}")

    def _print_summary(self):
        """Print validation summary."""
        errors = sum(1 for i in self.issues if i.level == "error")
        warnings = sum(1 for i in self.issues if i.level == "warning")
        success = sum(1 for i in self.issues if i.level == "success")

        print(f"\n{Colors.BOLD}{'=' * 70}{Colors.RESET}")
        print(f"{Colors.BOLD}Summary:{Colors.RESET}")
        print(f"  {Colors.GREEN}✓ {success} passed{Colors.RESET}")
        if warnings > 0:
            print(f"  {Colors.YELLOW}⚠ {warnings} warnings{Colors.RESET}")
        if errors > 0:
            print(f"  {Colors.RED}✗ {errors} errors{Colors.RESET}")
        print(f"{Colors.BOLD}{'=' * 70}{Colors.RESET}\n")

        # Print variable mapping table
        if self.env_vars:
            self._print_variable_mapping()

    def _print_variable_mapping(self):
        """Print mapping of variables to files and services."""
        print(f"{Colors.BOLD}{Colors.CYAN}Variable Source Mapping{Colors.RESET}")
        print(f"{Colors.BOLD}{'-' * 70}{Colors.RESET}")

        all_vars = set()
        for env_dict in self.env_vars.values():
            all_vars.update(env_dict.keys())

        print(f"{'Variable':<30} | {'Source File':<20} | {'Used By'}")
        print("-" * 70)

        for var in sorted(all_vars):
            source = "unknown"
            for file_name, env_dict in self.env_vars.items():
                if var in env_dict:
                    source = file_name
                    break

            services = []
            if var in self.docker_compose_vars:
                services.append(self.docker_compose_vars[var])

            services_str = ", ".join(services) if services else "?"
            print(f"{var:<30} | {source:<20} | {services_str}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Lab01-MCP Environment Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit codes:
  0 = All validations passed
  1 = Warnings found (non-blocking)
  2 = Errors found (blocking)
        """
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output (summary only)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    # Determine project root
    project_root = Path(__file__).parent.parent

    # Run validator
    validator = EnvironmentValidator(
        project_root,
        strict=args.strict,
        quiet=args.quiet
    )
    exit_code = validator.run()

    # Output JSON if requested
    if args.json:
        output = {
            "exit_code": exit_code,
            "issues": [asdict(issue) for issue in validator.issues],
            "env_vars": validator.env_vars,
            "summary": {
                "errors": sum(1 for i in validator.issues if i.level == "error"),
                "warnings": sum(1 for i in validator.issues if i.level == "warning"),
                "passed": sum(1 for i in validator.issues if i.level == "success")
            }
        }
        print(json.dumps(output, indent=2))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
