"""System prompt building with dynamic MCP tools context.

This module handles dynamic system prompt construction by:
- Loading base template from settings
- Generating tools context from autodiscovered MCP tools
- Injecting pagination configuration
- Providing fallback prompts
"""

from google.genai import types

from config.settings import settings
from utils.logger import get_logger

logger = get_logger("PromptBuilder", settings.LOG_LEVEL)


class PromptBuilder:
    """Builder for dynamic system prompts with MCP tools context.

    This class handles system prompt construction by:
    - Loading base system prompt template
    - Generating dynamic tools context from FunctionDeclarations
    - Injecting configuration values (pagination page size)
    - Providing fallback prompt on errors

    Attributes:
        None (stateless builder)
    """

    @staticmethod
    def build_dynamic_system_prompt(mcp_tools: list[types.FunctionDeclaration]) -> str:
        """Build system prompt with autodiscovered MCP tools context.

        Args:
            mcp_tools: List of FunctionDeclaration objects from MCP

        Returns:
            Complete system prompt with tools information

        Example:
            >>> tools = [FunctionDeclaration(name="search", description="Search")]
            >>> prompt = PromptBuilder.build_dynamic_system_prompt(tools)
            >>> "Herramientas MCP" in prompt
            True
        """
        try:
            # Load base system prompt
            system_prompt_template = settings.get_system_prompt()

            # Generate dynamic tools context from discovered tools
            tools_context = (
                PromptBuilder.generate_tools_context(mcp_tools)
                if mcp_tools
                else "No hay herramientas MCP disponibles actualmente."
            )

            # Inject tools context and pagination config into prompt
            final_prompt = (
                system_prompt_template
                .replace("{TOOLS_CONTEXT}", tools_context)
                .replace("{PAGINATION_PAGE_SIZE}", str(settings.PAGINATION_PAGE_SIZE))
            )

            logger.debug(f"Sistema prompt construido: {len(final_prompt)} caracteres")
            return final_prompt

        except FileNotFoundError as e:
            logger.warning(f"Archivo de prompt no encontrado: {e}")
            # Fallback to basic prompt
            return PromptBuilder.get_fallback_prompt()
        except Exception as e:
            logger.exception(f"Error construyendo sistema prompt: {e}")
            return PromptBuilder.get_fallback_prompt()

    @staticmethod
    def generate_tools_context(mcp_tools: list[types.FunctionDeclaration]) -> str:
        """Generate DYNAMIC tools context from discovered MCP tools (FunctionDeclaration).

        100% no-hardcoding implementation. Generates generic instructions.

        Args:
            mcp_tools: List of FunctionDeclaration objects

        Returns:
            Formatted tools context for injection into system prompt

        Example:
            >>> tools = [FunctionDeclaration(name="search", description="Search products")]
            >>> context = PromptBuilder.generate_tools_context(tools)
            >>> "search" in context
            True
        """
        if not mcp_tools:
            return "No hay herramientas MCP disponibles actualmente."

        tools_info = [
            "## Herramientas MCP Autodescubiertas\n",
            "Las siguientes herramientas están disponibles. "
            "ANALIZA la consulta del cliente e INFIERE automáticamente cuál usar:\n",
        ]

        for i, func_decl in enumerate(mcp_tools, 1):
            # ✅ Extract from FunctionDeclaration (not callable)
            tool_name = func_decl.name
            tool_description = func_decl.description or "Sin descripción disponible"

            # Clean up description
            desc_lines = [line.strip() for line in tool_description.split("\n") if line.strip()]
            first_line = desc_lines[0] if desc_lines else "Sin descripción"

            tools_info.append(f"\n### {i}. `{tool_name}`")
            tools_info.append(f"{first_line}\n")

            # ✅ Extract parameters from FunctionDeclaration.Schema
            if func_decl.parameters and func_decl.parameters.properties:
                tools_info.append("**Parámetros**:")
                for param_name, param_schema in func_decl.parameters.properties.items():
                    param_type = param_schema.type.name if param_schema.type else "ANY"
                    param_desc = param_schema.description or ""
                    is_required = param_name in (func_decl.parameters.required or [])
                    required_marker = " (required)" if is_required else " (optional)"
                    tools_info.append(f"  - `{param_name}` ({param_type}){required_marker}: {param_desc}")
                tools_info.append("")

            # Additional details if available
            if len(desc_lines) > 1:
                tools_info.append(f"**Detalles**: {' '.join(desc_lines[1:3])}\n")

        # ✅ CRITICAL: Generic instruction, NO hardcoded tool names
        tools_info.append("\n💡 **Estrategia de Inferencia Automática**:")
        tools_info.append("1. Analiza la INTENCIÓN del cliente (buscar, consultar, comparar)")
        tools_info.append("2. Detecta si hay MÚLTIPLES intenciones/categorías diferentes en una consulta")
        tools_info.append("3. Para múltiples intenciones: haz MÚLTIPLES llamadas (una por categoría)")
        tools_info.append("4. Identifica PALABRAS CLAVE relevantes en cada intención")
        tools_info.append("5. Selecciona la herramienta MÁS APROPIADA para cada categoría")
        tools_info.append("6. Si la consulta es ambigua, PREGUNTA para clarificar")
        tools_info.append("7. Si ninguna herramienta aplica, responde con tu conocimiento general")

        return "\n".join(tools_info)

    @staticmethod
    def get_fallback_prompt() -> str:
        """Get fallback system prompt if loading fails.

        Returns:
            Basic fallback system prompt

        Example:
            >>> prompt = PromptBuilder.get_fallback_prompt()
            >>> "Odiseo Bot" in prompt
            True
        """
        return """Eres Odiseo Bot, un vendedor inteligente especializado en búsqueda de productos.

Tu misión: Ayudar a los clientes a encontrar exactamente lo que buscan usando búsqueda
inteligente y recomendaciones personalizadas.

Características:
- Cordial y profesional
- Empático con las necesidades del cliente
- Proactivo en sugerencias
- Experto en productos

Usa las herramientas MCP disponibles para buscar productos según la consulta del cliente.
"""
