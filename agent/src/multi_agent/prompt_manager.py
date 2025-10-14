"""Prompt Management System for Multi-Agent Architecture.

This module provides centralized prompt loading, templating, and versioning
for all agents in the multi-agent system. It replaces hardcoded prompts with
external templates and enables data-driven prompt generation.

Features:
- External Jinja2 templates for all agent prompts
- YAML-based configuration data
- Version management and A/B testing support
- MCP tools integration for dynamic database data (agents use MCP tools, not direct DB)
- Backward compatibility with existing code
- Feature flag support for gradual rollout

Architecture:
    prompts/
    ├── templates/          # Jinja2 templates for each agent
    ├── data/              # YAML configuration data
    ├── config/            # Version management
    └── README.md          # Documentation

Note:
    Agents MUST use MCP tools (get_services, get_business_hours, etc.) to access
    database data. Direct database connections in PromptManager have been removed
    to maintain architectural consistency with the MCP Server pattern.

Author: Lab01-MCP Team
Created: 2025-10-11
Version: 1.2.0 (A/B testing infrastructure for Sales Agent)
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# Jinja2 imports
try:
    from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound

    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

from gemini_agent.utils.logger import setup_logging

# Setup logger
logger = setup_logging("prompt_manager")

# A/B Testing Constants
AB_BUCKETING_MODULO = 100  # For deterministic user bucketing (0-99)
DEFAULT_TRAFFIC_SPLIT = 0.5  # 50/50 split by default

# Default Values per Agent
DEFAULT_PAGINATION_SIZE = 4
DEFAULT_SHOW_SUMMARY = False
DEFAULT_RESPONSE_DETAIL = "detailed"


class PromptManager:
    """Centralized prompt management system for multi-agent architecture.

    This class manages loading, rendering, and versioning of prompts for all
    agents in the system. It provides a unified interface for prompt management
    with support for templates, data injection, and versioning.

    The manager supports two modes:
    1. **Template Mode**: Load Jinja2 templates and render with data (preferred)
    2. **Fallback Mode**: Return legacy hardcoded prompts if templates unavailable

    Example:
        >>> manager = PromptManager()
        >>> prompt = manager.get_router_prompt()
        >>> booking_prompt = manager.get_booking_prompt(
        ...     customer_email="maria@example.com"
        ... )

    Attributes:
        prompts_dir: Root directory for prompt files
        templates_dir: Directory containing Jinja2 templates
        data_dir: Directory containing YAML data files
        config_dir: Directory containing version configs
        env: Jinja2 environment for template rendering
        config: Active configuration loaded from YAML
        use_templates: Whether to use templates or fallback mode
    """

    def __init__(
        self, prompts_dir: Path | None = None, use_templates: bool = True
    ) -> None:
        """Initialize Prompt Manager.

        Args:
            prompts_dir: Root directory for prompts (defaults to repo root/prompts/)
            use_templates: Whether to use template mode (True) or fallback mode (False)

        Raises:
            RuntimeError: If Jinja2 not available and use_templates=True
        """
        # Determine prompts directory
        if prompts_dir is None:
            # Default: /path/to/Lab01-MCP/prompts/
            repo_root = Path(__file__).parent.parent.parent.parent
            self.prompts_dir = repo_root / "prompts"
        else:
            self.prompts_dir = prompts_dir

        self.templates_dir = self.prompts_dir / "templates"
        self.data_dir = self.prompts_dir / "data"
        self.config_dir = self.prompts_dir / "config"

        # Template mode configuration
        self.use_templates = use_templates

        # Initialize Jinja2 environment if templates enabled
        if use_templates:
            if not JINJA2_AVAILABLE:
                logger.error("Jinja2 not available but use_templates=True")
                raise RuntimeError(
                    "Jinja2 is required for template mode. "
                    "Install with: pip install jinja2"
                )

            self.env = Environment(
                loader=FileSystemLoader(str(self.templates_dir)),
                trim_blocks=True,
                lstrip_blocks=True,
                autoescape=False,  # Prompts are not HTML
            )
            logger.info(f"Jinja2 environment initialized: {self.templates_dir}")
        else:
            self.env = None
            logger.info("Template mode disabled - using fallback prompts")

        # Load configuration
        self.config = self._load_config()

        logger.info(
            f"PromptManager initialized - "
            f"Mode: {'Template' if use_templates else 'Fallback'}, "
            f"Dir: {self.prompts_dir}"
        )

    def _load_config(self) -> dict[str, Any]:
        """Load active configuration from prompt_versions.yaml.

        Returns:
            Configuration dictionary with active versions and settings.
            Returns default config if file not found.
        """
        config_path = self.config_dir / "prompt_versions.yaml"

        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}")
            # Return default configuration
            return {
                "active_versions": {
                    "router": "v1.0",
                    "booking": "v1.0",
                    "general": "v1.0",
                    "sales": "v1.0",
                },
                "use_templates": self.use_templates,
                "ab_testing": {"enabled": False},
            }

        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.debug(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            logger.exception(f"Error loading config: {e}")
            return {"active_versions": {}, "use_templates": False}

    def _load_data(self, data_file: str) -> dict[str, Any]:
        """Load data from YAML file in data directory.

        Args:
            data_file: Name of YAML file (e.g., "services.yaml")

        Returns:
            Parsed YAML data as dictionary.

        Raises:
            FileNotFoundError: If data file not found
            yaml.YAMLError: If YAML parsing fails
        """
        data_path = self.data_dir / data_file

        if not data_path.exists():
            logger.error(f"Data file not found: {data_path}")
            raise FileNotFoundError(f"Data file not found: {data_path}")

        try:
            with open(data_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            logger.debug(f"Data loaded from {data_file}")
            return data
        except yaml.YAMLError as e:
            logger.exception(f"YAML parsing error in {data_file}: {e}")
            raise

    def _render_template(self, template_name: str, context: dict[str, Any]) -> str:
        """Render Jinja2 template with provided context.

        Args:
            template_name: Name of template file (e.g., "router_classification.jinja2")
            context: Dictionary of variables to inject into template

        Returns:
            Rendered prompt text

        Raises:
            TemplateNotFound: If template file not found
            RuntimeError: If template mode disabled
        """
        if not self.use_templates or self.env is None:
            raise RuntimeError("Template mode is disabled")

        try:
            template = self.env.get_template(template_name)
            rendered = template.render(**context)
            logger.debug(f"Template rendered: {template_name} ({len(rendered)} chars)")
            return rendered
        except TemplateNotFound:
            logger.error(f"Template not found: {template_name}")
            raise

    # =========================================================================
    # Router Agent Prompts
    # =========================================================================

    def get_router_prompt(self, version: str | None = None) -> str:
        """Get router classification prompt.

        Args:
            version: Specific version (e.g., "v2.0"), or None for active version

        Returns:
            Router classification prompt text

        Example:
            >>> manager = PromptManager()
            >>> prompt = manager.get_router_prompt()
            >>> "sales" in prompt.lower()
            True
        """
        if not self.use_templates:
            return self._get_router_prompt_fallback()

        try:
            version = version or self.config["active_versions"].get("router", "v1.0")
            context = {"version": version}
            return self._render_template("router_classification.jinja2", context)
        except Exception as e:
            logger.warning(f"Template render failed, using fallback: {e}")
            return self._get_router_prompt_fallback()

    def _get_router_prompt_fallback(self) -> str:
        """Fallback router prompt (legacy compatibility).

        Returns hardcoded prompt from original agent_router.py.
        """
        # Import from original module to maintain consistency
        try:
            from multi_agent.agent_router import AgentRouter

            return AgentRouter.CLASSIFICATION_PROMPT
        except ImportError:
            logger.error("Cannot import AgentRouter for fallback")
            return "Classify intent as: sales, booking, or general"

    # =========================================================================
    # Booking Agent Prompts
    # =========================================================================

    def get_booking_prompt(
        self,
        customer_email: str | None = None,
        version: str | None = None,
        services: list[dict[str, Any]] | None = None,
        show_pre_confirmation_summary: bool | None = None,
        user_id: str | None = None,
    ) -> str:
        """Get booking agent system prompt - MODULAR with A/B TESTING.

        Uses modular Jinja2 template architecture with A/B testing support
        for confirmation flow optimization.

        **A/B Testing Support**: If user_id is provided and A/B testing is enabled,
        automatically selects version and confirmation flow based on active experiments
        (e.g., direct confirmation vs pre-confirmation summary).

        Args:
            customer_email: Optional customer email for personalization
            version: Specific version, or None for active version (or from A/B test)
            services: Optional services list (if None, loads from data/services.yaml)
            show_pre_confirmation_summary: Whether to show pre-confirmation summary
                (default: from A/B test if user_id provided, else False)
            user_id: Optional user ID for A/B test bucketing (deterministic assignment)

        Returns:
            Booking agent system prompt with services data

        Example:
            >>> manager = PromptManager()
            >>> # Without A/B testing
            >>> prompt = manager.get_booking_prompt(customer_email="maria@example.com")
            >>> # With A/B testing (user gets variant A or B)
            >>> prompt = manager.get_booking_prompt(user_id="user_12345")
        """
        if not self.use_templates:
            return self._get_booking_prompt_fallback(customer_email)

        try:
            # Check if A/B testing should override version/parameters
            if user_id and not version:
                # Use A/B testing to select version and parameters
                selected_version, selected_show_summary = (
                    self._select_ab_test_version_booking(user_id=user_id)
                )
                version = selected_version
                show_pre_confirmation_summary = (
                    show_pre_confirmation_summary
                    if show_pre_confirmation_summary is not None
                    else selected_show_summary
                )
            else:
                # Use defaults or provided values
                version = version or self.config["active_versions"].get(
                    "booking", "v1.0"
                )
                show_pre_confirmation_summary = show_pre_confirmation_summary or False

            # Load services data if not provided
            if services is None:
                try:
                    services_data = self._load_data("services.yaml")
                    services = services_data.get("services", [])
                except FileNotFoundError:
                    logger.warning("services.yaml not found, using empty list")
                    services = []

            # Inject current date/time for relative date calculations
            now = datetime.now()

            context = {
                "version": version,
                "services": services,
                "customer_email": customer_email,
                "show_pre_confirmation_summary": show_pre_confirmation_summary,
                # Date/time context for flexible date parsing
                "current_date": now.strftime("%Y-%m-%d"),  # 2025-10-13
                "current_datetime": now,  # Full datetime object for Jinja2 filters
                "current_day": now.strftime("%A"),  # Sunday, Monday, etc.
                "current_day_es": self._get_spanish_day(
                    now.weekday()
                ),  # Domingo, Lunes, etc.
            }

            logger.debug(
                f"Rendering booking prompt: version={version}, "
                f"show_summary={show_pre_confirmation_summary}, user_id={user_id}"
            )

            # Use new modular template structure (booking_agent/booking_agent.jinja2)
            return self._render_template("booking_agent/booking_agent.jinja2", context)
        except Exception as e:
            logger.warning(f"Template render failed, using fallback: {e}")
            return self._get_booking_prompt_fallback(customer_email)

    def _get_booking_prompt_fallback(self, customer_email: str | None = None) -> str:
        """Fallback booking prompt (legacy compatibility)."""
        try:
            from multi_agent.booking_agent import BookingAgent

            prompt = BookingAgent.SYSTEM_PROMPT
            if customer_email:
                prompt += f"\n\nCLIENTE ACTUAL: {customer_email}"
            return prompt
        except ImportError:
            logger.error("Cannot import BookingAgent for fallback")
            return "You are a booking assistant."

    # =========================================================================
    # General Agent Prompts
    # =========================================================================

    def get_general_prompt(
        self,
        version: str | None = None,
        response_detail_level: str | None = None,
        user_id: str | None = None,
    ) -> str:
        """Get general agent system prompt - MODULAR with A/B TESTING.

        Uses modular Jinja2 template architecture with A/B testing support
        for response style optimization.

        **A/B Testing Support**: If user_id is provided and A/B testing is enabled,
        automatically selects version and response style based on active experiments
        (e.g., detailed vs concise responses).

        Args:
            version: Specific version, or None for active version (or from A/B test)
            response_detail_level: Response style "detailed" or "concise"
                (default: from A/B test if user_id provided, else "detailed")
            user_id: Optional user ID for A/B test bucketing (deterministic assignment)

        Returns:
            General agent system prompt with business info and policies

        Example:
            >>> manager = PromptManager()
            >>> # Without A/B testing
            >>> prompt = manager.get_general_prompt()
            >>> # With A/B testing (user gets variant A or B)
            >>> prompt = manager.get_general_prompt(user_id="user_12345")
        """
        if not self.use_templates:
            return self._get_general_prompt_fallback()

        try:
            # Check if A/B testing should override version/parameters
            if user_id and not version:
                # Use A/B testing to select version and parameters
                selected_version, selected_detail_level = (
                    self._select_ab_test_version_general(user_id=user_id)
                )
                version = selected_version
                response_detail_level = (
                    response_detail_level
                    if response_detail_level is not None
                    else selected_detail_level
                )
            else:
                # Use defaults or provided values
                version = version or self.config["active_versions"].get(
                    "general", "v1.0"
                )
                response_detail_level = response_detail_level or "detailed"

            # Load business info and policies
            try:
                business = self._load_data("business_info.yaml")
                policies = self._load_data("policies.yaml")
            except FileNotFoundError as e:
                logger.warning(f"Data file not found: {e}, using defaults")
                business = {"company_name": "Lab01-MCP"}
                policies = {}

            context = {
                "version": version,
                "business": business,
                "policies": policies,
                "response_detail_level": response_detail_level,
            }

            logger.debug(
                f"Rendering general prompt: version={version}, "
                f"detail_level={response_detail_level}, user_id={user_id}"
            )

            # Use new modular template structure (general_agent/general_agent.jinja2)
            return self._render_template("general_agent/general_agent.jinja2", context)
        except Exception as e:
            logger.warning(f"Template render failed, using fallback: {e}")
            return self._get_general_prompt_fallback()

    def _get_general_prompt_fallback(self) -> str:
        """Fallback general prompt (legacy compatibility)."""
        try:
            from multi_agent.general_agent import GeneralAgent

            return GeneralAgent.SYSTEM_PROMPT
        except ImportError:
            logger.error("Cannot import GeneralAgent for fallback")
            return "You are a general information assistant."

    # =========================================================================
    # Sales Agent Prompts
    # =========================================================================

    def get_sales_prompt(
        self,
        mcp_tools: list[Any] | None = None,
        pagination_page_size: int | None = None,
        version: str | None = None,
        user_id: str | None = None,
    ) -> str:
        """Get sales agent system prompt (OdiseoBot) - MODULAR with A/B TESTING.

        Uses new modular Jinja2 template architecture following industry best
        practices 2025. Prompt is split into specialized modules for easier
        maintenance, versioning, and A/B testing.

        **A/B Testing Support**: If user_id is provided and A/B testing is enabled
        in prompt_versions.yaml, automatically selects version and pagination based
        on active experiments (e.g., 4 vs 6 products pagination).

        Args:
            mcp_tools: Optional list of MCP tools (FunctionDeclaration)
            pagination_page_size: Number of products per page (default: 4, or from A/B test)
            version: Specific version, or None for active version (or from A/B test)
            user_id: Optional user ID for A/B test bucketing (deterministic assignment)

        Returns:
            Sales agent system prompt with tools context

        Example:
            >>> manager = PromptManager()
            >>> # Without A/B testing
            >>> prompt = manager.get_sales_prompt(pagination_page_size=4)
            >>> # With A/B testing (user gets variant A or B)
            >>> prompt = manager.get_sales_prompt(user_id="user_12345")
        """
        if not self.use_templates:
            return self._get_sales_prompt_fallback(mcp_tools, pagination_page_size or 4)

        try:
            # Check if A/B testing should override version/pagination
            if user_id and not version:
                # Use A/B testing to select version and pagination
                selected_version, selected_pagination = self._select_ab_test_version(
                    agent="sales", user_id=user_id
                )
                version = selected_version
                pagination_page_size = pagination_page_size or selected_pagination
            else:
                # Use defaults or provided values
                version = version or self.config["active_versions"].get("sales", "v1.0")
                pagination_page_size = pagination_page_size or 4

            # Generate tools context (similar to PromptBuilder)
            tools_context = self._generate_tools_context(mcp_tools) if mcp_tools else ""

            context = {
                "version": version,
                "tools_context": tools_context,
                "pagination_page_size": pagination_page_size,
            }

            logger.debug(
                f"Rendering sales prompt: version={version}, "
                f"pagination={pagination_page_size}, user_id={user_id}"
            )

            # Use new modular template structure (sales_agent/sales_agent.jinja2)
            return self._render_template("sales_agent/sales_agent.jinja2", context)
        except Exception as e:
            logger.warning(f"Template render failed, using fallback: {e}")
            return self._get_sales_prompt_fallback(mcp_tools, pagination_page_size or 4)

    def _get_sales_prompt_fallback(
        self, mcp_tools: list[Any] | None = None, pagination_page_size: int = 4
    ) -> str:
        """Fallback sales prompt using standalone implementation.

        This method provides a complete fallback without requiring PromptBuilder
        or settings imports, making it more robust for testing and edge cases.
        """
        try:
            # Try to use PromptBuilder if available
            from client_mcp.core.prompt_builder import PromptBuilder

            return PromptBuilder.build_dynamic_system_prompt(mcp_tools or [])
        except ImportError:
            logger.warning("PromptBuilder not available, using standalone fallback")
            # Standalone fallback - generate basic prompt with tools context
            tools_context = self._generate_tools_context(mcp_tools) if mcp_tools else ""

            base_prompt = f"""Eres Odiseo, un vendedor inteligente especializado en productos.

Tu misión es ayudar a los clientes a encontrar lo que buscan con precisión y empatía.

{tools_context}

## REGLAS DE PAGINACIÓN
- Muestra {pagination_page_size} productos por página
- Al final indica cuántos productos quedan sin mostrar
- Usa formato claro y conciso

## FORMATO DE RESPUESTA
1. Saludo empático
2. Resultados con detalles relevantes
3. Sugerencias personalizadas

Sé profesional, cordial y proactivo."""

            return base_prompt
        except Exception as e:
            logger.error(f"Fallback failed: {e}")
            return "You are Odiseo, a sales assistant."

    def _generate_tools_context(self, mcp_tools: list[Any]) -> str:
        """Generate tools context from MCP tools (standalone implementation).

        This method generates a formatted tools context from FunctionDeclaration
        objects without requiring PromptBuilder import (for better modularity).

        Args:
            mcp_tools: List of FunctionDeclaration objects

        Returns:
            Formatted tools context string
        """
        if not mcp_tools:
            return "No hay herramientas MCP disponibles actualmente."

        tools_info = [
            "## Herramientas MCP Autodescubiertas\n",
            "Las siguientes herramientas están disponibles. "
            "ANALIZA la consulta del cliente e INFIERE automáticamente cuál usar:\n",
        ]

        for i, func_decl in enumerate(mcp_tools, 1):
            # Extract from FunctionDeclaration
            tool_name = func_decl.name if hasattr(func_decl, "name") else str(func_decl)
            tool_description = (
                func_decl.description
                if hasattr(func_decl, "description")
                else "Sin descripción disponible"
            ) or "Sin descripción disponible"

            # Clean up description
            desc_lines = [
                line.strip() for line in tool_description.split("\n") if line.strip()
            ]
            first_line = desc_lines[0] if desc_lines else "Sin descripción"

            tools_info.append(f"\n### {i}. `{tool_name}`")
            tools_info.append(f"{first_line}\n")

            # Extract parameters from FunctionDeclaration.Schema
            if hasattr(func_decl, "parameters") and func_decl.parameters:
                params = func_decl.parameters
                if hasattr(params, "properties") and params.properties:
                    tools_info.append("**Parámetros**:")
                    for param_name, param_schema in params.properties.items():
                        param_type = (
                            param_schema.type.name
                            if hasattr(param_schema, "type") and param_schema.type
                            else "ANY"
                        )
                        param_desc = (
                            param_schema.description
                            if hasattr(param_schema, "description")
                            else ""
                        )
                        required_list = (
                            params.required if hasattr(params, "required") else []
                        )
                        is_required = param_name in (required_list or [])
                        required_marker = (
                            " (required)" if is_required else " (optional)"
                        )
                        tools_info.append(
                            f"  - `{param_name}` ({param_type}){required_marker}: {param_desc}"
                        )
                    tools_info.append("")

            # Additional details if available
            if len(desc_lines) > 1:
                tools_info.append(f"**Detalles**: {' '.join(desc_lines[1:3])}\n")

        # Generic instruction
        tools_info.append("\n💡 **Estrategia de Inferencia Automática**:")
        tools_info.append(
            "1. Analiza la INTENCIÓN del cliente (buscar, consultar, comparar)"
        )
        tools_info.append(
            "2. Detecta si hay MÚLTIPLES intenciones/categorías diferentes en una consulta"
        )
        tools_info.append(
            "3. Para múltiples intenciones: haz MÚLTIPLES llamadas (una por categoría)"
        )
        tools_info.append("4. Identifica PALABRAS CLAVE relevantes en cada intención")
        tools_info.append(
            "5. Selecciona la herramienta MÁS APROPIADA para cada categoría"
        )
        tools_info.append("6. Si la consulta es ambigua, PREGUNTA para clarificar")
        tools_info.append(
            "7. Si ninguna herramienta aplica, responde con tu conocimiento general"
        )

        return "\n".join(tools_info)

    # =========================================================================
    # A/B Testing Methods
    # =========================================================================

    def _get_ab_variant(
        self,
        agent: str,
        experiment_name: str,
        user_id: str | None = None,
        default_version: str = "v1.0",
        default_params: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Generic A/B test variant selection with deterministic bucketing.

        This method centralizes A/B testing logic to avoid code duplication
        across agent-specific methods.

        Args:
            agent: Agent name (e.g., 'sales', 'booking', 'general')
            experiment_name: Experiment name to look for
            user_id: Optional user identifier for consistent bucketing
            default_version: Default version if A/B testing disabled
            default_params: Default parameters if A/B testing disabled

        Returns:
            Tuple of (version, params_dict)
            - version: Selected version string (e.g., 'v1.0', 'v1.1')
            - params_dict: Parameters for selected variant

        Example:
            >>> manager = PromptManager()
            >>> version, params = manager._get_ab_variant(
            ...     agent='sales',
            ...     experiment_name='sales_pagination_6_products',
            ...     user_id='user123'
            ... )
            >>> print(version, params['pagination_page_size'])  # ('v1.1', 6)
        """
        default_params = default_params or {}

        # Check if A/B testing enabled globally
        ab_config = self.config.get("ab_testing", {})
        if not ab_config.get("enabled", False):
            return (default_version, default_params)

        # Find active experiment for this agent
        experiments = ab_config.get("experiments", [])
        active_experiment = None

        for exp in experiments:
            if (
                exp.get("agent") == agent
                and exp.get("name") == experiment_name
                and exp.get("enabled", False)
            ):
                active_experiment = exp
                break

        if not active_experiment:
            return (default_version, default_params)

        # Determine which variant to use (A or B) with deterministic bucketing
        traffic_split = active_experiment.get("traffic_split", DEFAULT_TRAFFIC_SPLIT)

        if user_id:
            # Deterministic bucketing: same user always gets same variant
            hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
            use_variant_b = (
                hash_value % AB_BUCKETING_MODULO
            ) / AB_BUCKETING_MODULO < traffic_split
        else:
            # Random bucketing if no user_id (for testing/anonymous users)
            use_variant_b = random.random() < traffic_split

        # Select version and parameters based on variant
        if use_variant_b:
            version = active_experiment.get("version_b", "v1.1")
            params = active_experiment.get("version_b_params", {})
            variant_name = "B"
        else:
            version = active_experiment.get("version_a", "v1.0")
            params = active_experiment.get("version_a_params", {})
            variant_name = "A"

        logger.info(
            f"A/B test '{active_experiment['name']}': "
            f"user={user_id}, variant={variant_name}, "
            f"version={version}, params={params}"
        )

        return (version, params)

    def _select_ab_test_version(
        self, agent: str, user_id: str | None = None
    ) -> tuple[str, int]:
        """Select version for A/B test if enabled (Sales Agent).

        Args:
            agent: Agent name (e.g., 'sales')
            user_id: Optional user identifier for consistent bucketing

        Returns:
            Tuple of (version, pagination_page_size)
            - version: 'v1.0' or 'v1.1' or default active version
            - pagination_page_size: 4 or 6 or default value

        Example:
            >>> manager = PromptManager()
            >>> version, page_size = manager._select_ab_test_version('sales')
            >>> print(version, page_size)  # ('v1.0', 4) or ('v1.1', 6)
        """
        default_version = self.config["active_versions"].get(agent, "v1.0")
        default_params = {"pagination_page_size": DEFAULT_PAGINATION_SIZE}

        version, params = self._get_ab_variant(
            agent=agent,
            experiment_name="sales_pagination_6_products",
            user_id=user_id,
            default_version=default_version,
            default_params=default_params,
        )

        pagination_page_size = params.get(
            "pagination_page_size", DEFAULT_PAGINATION_SIZE
        )
        return (version, pagination_page_size)

    def _select_ab_test_version_booking(
        self, user_id: str | None = None
    ) -> tuple[str, bool]:
        """Select version for Booking A/B test if enabled.

        Similar to _select_ab_test_version() but for booking agent.
        Returns (version, show_pre_confirmation_summary) instead of pagination.

        Args:
            user_id: Optional user identifier for consistent bucketing

        Returns:
            Tuple of (version, show_pre_confirmation_summary)
            - version: 'v1.0' or 'v1.1' or default active version
            - show_pre_confirmation_summary: False (v1.0) or True (v1.1)

        Example:
            >>> manager = PromptManager()
            >>> version, show_summary = manager._select_ab_test_version_booking(user_id="user123")
            >>> print(version, show_summary)  # ('v1.0', False) or ('v1.1', True)
        """
        default_version = self.config["active_versions"].get("booking", "v1.0")
        default_params = {"show_pre_confirmation_summary": DEFAULT_SHOW_SUMMARY}

        version, params = self._get_ab_variant(
            agent="booking",
            experiment_name="booking_confirmation_flow",
            user_id=user_id,
            default_version=default_version,
            default_params=default_params,
        )

        show_pre_confirmation_summary = params.get(
            "show_pre_confirmation_summary", DEFAULT_SHOW_SUMMARY
        )
        return (version, show_pre_confirmation_summary)

    def _select_ab_test_version_general(
        self, user_id: str | None = None
    ) -> tuple[str, str]:
        """Select version for General Agent A/B test if enabled.

        Similar to _select_ab_test_version() but for general agent.
        Returns (version, response_detail_level) instead of pagination.

        Args:
            user_id: Optional user identifier for consistent bucketing

        Returns:
            Tuple of (version, response_detail_level)
            - version: 'v1.0' or 'v1.1' or default active version
            - response_detail_level: "detailed" (v1.0) or "concise" (v1.1)

        Example:
            >>> manager = PromptManager()
            >>> version, detail_level = manager._select_ab_test_version_general(user_id="user123")
            >>> print(version, detail_level)  # ('v1.0', 'detailed') or ('v1.1', 'concise')
        """
        default_version = self.config["active_versions"].get("general", "v1.0")
        default_params = {"response_detail_level": DEFAULT_RESPONSE_DETAIL}

        version, params = self._get_ab_variant(
            agent="general",
            experiment_name="general_response_style",
            user_id=user_id,
            default_version=default_version,
            default_params=default_params,
        )

        response_detail_level = params.get(
            "response_detail_level", DEFAULT_RESPONSE_DETAIL
        )
        return (version, response_detail_level)

    def get_experiment_config(self, experiment_name: str) -> dict[str, Any] | None:
        """Get configuration for specific A/B test experiment.

        Args:
            experiment_name: Name of experiment (e.g., 'sales_pagination_6_products')

        Returns:
            Experiment configuration dict or None if not found

        Example:
            >>> manager = PromptManager()
            >>> exp = manager.get_experiment_config('sales_pagination_6_products')
            >>> print(exp['description'])
            # "Test 6-product pagination vs 4-product"
        """
        ab_config = self.config.get("ab_testing", {})
        experiments = ab_config.get("experiments", [])

        for exp in experiments:
            if exp.get("name") == experiment_name:
                return exp

        return None

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def reload_config(self) -> None:
        """Reload configuration from YAML file.

        Useful for hot-reloading config changes without restarting.
        """
        self.config = self._load_config()
        logger.info("Configuration reloaded")

    def get_active_versions(self) -> dict[str, str]:
        """Get dictionary of active prompt versions for all agents.

        Returns:
            Dictionary mapping agent name to active version

        Example:
            >>> manager = PromptManager()
            >>> versions = manager.get_active_versions()
            >>> "router" in versions
            True
        """
        return self.config.get("active_versions", {})

    def _get_spanish_day(self, weekday: int) -> str:
        """Get Spanish day name from weekday number.

        Args:
            weekday: Day of week (0=Monday, 6=Sunday)

        Returns:
            Spanish day name (e.g., "Lunes", "Martes")
        """
        spanish_days = {
            0: "Lunes",
            1: "Martes",
            2: "Miércoles",
            3: "Jueves",
            4: "Viernes",
            5: "Sábado",
            6: "Domingo",
        }
        return spanish_days.get(weekday, "Unknown")

    def __repr__(self) -> str:
        """String representation of PromptManager."""
        mode = "Template" if self.use_templates else "Fallback"
        return (
            f"PromptManager(mode={mode}, "
            f"dir={self.prompts_dir}, "
            f"versions={self.get_active_versions()})"
        )
