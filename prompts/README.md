# Lab01-MCP Prompt Management System

A modular, version-controlled prompt management system for the multi-agent AI architecture.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [File Structure](#file-structure)
- [Creating Templates](#creating-templates)
- [Data Files](#data-files)
- [Versioning](#versioning)
- [A/B Testing](#ab-testing)
- [Database Integration](#database-integration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## 🎯 Overview

The Prompt Management System provides a centralized, **modular** approach to managing AI agent prompts for Lab01-MCP's multi-agent system. It replaces hardcoded prompts with external Jinja2 templates and YAML configuration files, enabling:

- **Modular Architecture**: 36+ reusable components across booking, sales, and general agents
- **Separation of Concerns**: Code vs content separation with module-based organization
- **Version Control**: Multiple prompt versions coexist with base/rollback copies
- **A/B Testing**: Compare different prompt strategies and module combinations
- **Database Integration**: Load dynamic data (services, hours) with intelligent caching
- **Hot Reload**: Update prompts without redeployment

### Key Benefits

✅ **No Code Changes**: Update prompts by editing templates
✅ **Versionable**: Git-track prompts independently from code
✅ **Testable**: Run A/B experiments on prompt variations
✅ **Maintainable**: Non-technical staff can edit content
✅ **Consistent**: Single source of truth for business data

## 🏗️ Architecture

```
prompts/
├── templates/                    # Jinja2 prompt templates (modular)
│   ├── router_classification.jinja2  # Router agent (flat)
│   ├── booking_agent/                # Booking agent (modular)
│   │   ├── booking_agent.jinja2      # Main template
│   │   ├── base.jinja2               # Base template
│   │   └── modules/                  # 25+ reusable modules
│   ├── general_agent/                # General agent (modular)
│   │   ├── general_agent.jinja2      # Main template
│   │   ├── base.jinja2               # Base template
│   │   └── modules/                  # 3 reusable modules
│   ├── sales_agent/                  # Sales agent (modular)
│   │   ├── sales_agent.jinja2        # Main template
│   │   ├── base.jinja2               # Base template
│   │   └── modules/                  # 8 reusable modules
│   └── base/                         # Base versions for rollback
│       ├── router_classification.jinja2
│       ├── booking_agent/
│       ├── general_agent/
│       └── sales_agent/
├── data/                         # YAML configuration data
│   ├── business_info.yaml        # Company info, hours, contact
│   └── policies.yaml             # Payment, shipping, returns
├── config/                       # Version management
│   └── prompt_versions.yaml      # Active versions & A/B testing
└── README.md                     # This file
```

### Components

1. **PromptManager** (`agent/src/multi_agent/prompt_manager.py`)
   - Loads and renders Jinja2 templates
   - Manages versions and A/B testing
   - Integrates with database for dynamic data

2. **Templates** (`templates/`)
   - **Modular Architecture**: Templates organized by agent with reusable modules
   - **Main Templates**: Orchestrate modules via `{% include %}` directives
   - **Base Templates**: Foundation templates for inheritance
   - **Module Library**: 36+ specialized components across all agents
     - Booking Agent: 25+ modules (UX, validation, intelligence)
     - Sales Agent: 8 modules (display, navigation, quality)
     - General Agent: 3 modules (info, policies, style)
   - Support variables, loops, conditionals, template inheritance

3. **Data Files** (`data/`)
   - YAML files for configuration data
   - Services, business info, policies
   - Can be auto-generated from database

4. **Configuration** (`config/prompt_versions.yaml`)
   - Active version management
   - A/B testing configuration
   - Feature flags

## 🚀 Getting Started

### Prerequisites

```bash
# Install required dependencies
pip install jinja2>=3.1.0 pyyaml>=6.0.0
```

### Installation

The Prompt Management System is already integrated into the project. No additional installation required.

### Basic Usage

```python
from multi_agent.prompt_manager import PromptManager

# Initialize manager
manager = PromptManager()

# Get prompts for each agent
router_prompt = manager.get_router_prompt()
booking_prompt = manager.get_booking_prompt(customer_email="maria@example.com")
general_prompt = manager.get_general_prompt()
sales_prompt = manager.get_sales_prompt(mcp_tools=tools, pagination_page_size=4)
```

### Feature Flag

Enable/disable template mode in `.env` or `config/prompt_versions.yaml`:

```yaml
use_templates: true   # true = use templates, false = use legacy hardcoded prompts
```

## 💻 Usage

### Loading a Prompt

```python
from multi_agent.prompt_manager import PromptManager

# Initialize
manager = PromptManager()

# Load router prompt
prompt = manager.get_router_prompt()
print(prompt)
```

### Using Custom Data

```python
# Load booking prompt with custom services
custom_services = [
    {
        "name": "consultation",
        "display_name": "Consulta General",
        "duration_minutes": 30,
        "price": 50.00
    }
]

prompt = manager.get_booking_prompt(services=custom_services)
```

### Loading from Database

```python
import psycopg2

# Connect to database
conn = psycopg2.connect(DATABASE_URL)

# Load services from DB
services = await manager.load_services_from_db(conn)

# Use in booking prompt
prompt = manager.get_booking_prompt(services=services)
```

## 📁 File Structure

### Templates Directory (Modular Architecture)

```
templates/
├── router_classification.jinja2         # Intent classification (flat structure)
│
├── booking_agent/                       # Booking agent (MODULAR)
│   ├── booking_agent.jinja2             # Main template (orchestrates modules)
│   ├── base.jinja2                      # Base template (foundation)
│   └── modules/                         # 25+ reusable components
│       ├── confirmation_flow.jinja2
│       ├── context_enrichment.jinja2
│       ├── data_validation.jinja2
│       ├── duplicate_booking_prevention.jinja2
│       ├── enhanced_time_slot_selection.jinja2
│       ├── error_recovery_strategies.jinja2
│       ├── examples.jinja2
│       ├── flexible_dates.jinja2
│       ├── intelligent_recommendations.jinja2
│       ├── intent_detection.jinja2
│       ├── progressive_confirmation_flow.jinja2
│       ├── reasoning_instructions.jinja2
│       ├── reminder_protocols.jinja2
│       ├── rescheduling_intelligence.jinja2
│       ├── scope_guardrails.jinja2
│       ├── smart_greeting.jinja2
│       ├── time_selection_ux.jinja2
│       ├── timezone_handling.jinja2
│       ├── tool_usage_rules.jinja2
│       ├── ux_best_practices.jinja2
│       ├── ux_conversational.jinja2
│       └── ... (25+ total modules)
│
├── general_agent/                       # General agent (MODULAR)
│   ├── general_agent.jinja2             # Main template
│   ├── base.jinja2                      # Base template
│   └── modules/                         # 3 reusable components
│       ├── business_info.jinja2
│       ├── policies.jinja2
│       └── response_style.jinja2
│
├── sales_agent/                         # Sales agent (MODULAR)
│   ├── sales_agent.jinja2               # Main template
│   ├── base.jinja2                      # Base template (legacy compatibility)
│   └── modules/                         # 8 reusable components
│       ├── agent_role.jinja2
│       ├── anti_hallucination.jinja2
│       ├── display_rules.jinja2
│       ├── examples.jinja2
│       ├── pagination_navigation.jinja2
│       ├── quality_rules.jinja2
│       ├── response_format.jinja2
│       └── tools_context.jinja2
│
└── base/                                # Base versions (for rollback)
    ├── router_classification.jinja2
    ├── booking_agent/ (complete copy)
    ├── general_agent/ (complete copy)
    └── sales_agent/ (complete copy)
```

### Data Directory

```
data/
├── business_info.yaml   # Company info, hours, contact details
└── policies.yaml        # Payment, shipping, returns, warranty policies

Note: Services data is now loaded directly from the database (test.service_types)
      via PromptManager.load_services_from_db() - See database_integration section
```

### Config Directory

```
config/
└── prompt_versions.yaml   # Active versions, A/B testing config
```

## 🎨 Creating Templates

### Template Syntax (Jinja2)

Jinja2 uses `{{ variable }}` for variables and `{% statement %}` for logic.

#### Variables

```jinja2
Hello, {{ customer_name }}!
Your email is: {{ customer_email }}
```

#### Conditionals

```jinja2
{% if customer_email %}
CLIENTE ACTUAL: {{ customer_email }}
{% else %}
No customer email provided.
{% endif %}
```

#### Loops

```jinja2
SERVICIOS DISPONIBLES:
{% for service in services %}
{{ loop.index }}. {{ service.display_name }} ({{ service.duration_minutes }} min)
   - {{ service.description }}
   - Precio: ${{ "%.2f"|format(service.price) }}
{% endfor %}
```

### Creating a New Template

1. **Create file** in `templates/`:

```bash
touch templates/new_agent.jinja2
```

2. **Write template** with Jinja2 syntax:

```jinja2
{#
New Agent Prompt
================
Purpose: Description of agent purpose

Variables:
  - version: Template version
  - custom_var: Custom variable description
#}

You are a specialized agent for {{ purpose }}.

Your tasks:
{% for task in tasks %}
- {{ task }}
{% endfor %}
```

3. **Add method** to PromptManager:

```python
def get_new_agent_prompt(
    self,
    version: Optional[str] = None,
    **context: Any
) -> str:
    """Get new agent prompt."""
    if not self.use_templates:
        return self._get_new_agent_fallback()

    version = version or self.config['active_versions'].get('new_agent', 'v1.0')
    return self._render_template("new_agent.jinja2", context)
```

4. **Update config** in `config/prompt_versions.yaml`:

```yaml
active_versions:
  new_agent: v1.0
```

### Working with Modular Templates

The booking, general, and sales agents use a **modular architecture** where functionality is split into reusable modules.

#### Structure

```
agent_name/
├── agent_name.jinja2      # Main template (orchestrates modules)
├── base.jinja2            # Base template (foundation)
└── modules/               # Reusable components
    ├── module1.jinja2
    ├── module2.jinja2
    └── ...
```

#### Including Modules

Main templates use `{% include %}` to compose modules:

```jinja2
{# booking_agent/booking_agent.jinja2 #}
{% include 'booking_agent/modules/scope_guardrails.jinja2' %}
{% include 'booking_agent/modules/data_validation.jinja2' %}
{% include 'booking_agent/modules/ux_conversational.jinja2' %}
```

#### Creating a New Module

1. **Create module file**:
```bash
touch templates/booking_agent/modules/new_feature.jinja2
```

2. **Write module content**:
```jinja2
{# New Feature Module #}
## NEW FEATURE

Description of the new feature...
```

3. **Include in main template**:
```jinja2
{# In booking_agent/booking_agent.jinja2 #}
{% include 'booking_agent/modules/new_feature.jinja2' %}
```

4. **Test**: Render the booking prompt and verify the module is included

#### Module Best Practices

- **Single Responsibility**: Each module handles ONE specific concern
- **Self-Contained**: Modules should work independently
- **Clear Names**: Use descriptive names (e.g., `duplicate_booking_prevention.jinja2`)
- **Comments**: Document module purpose and dependencies
- **Backup Copies**: Keep `.backup` versions before major changes

## 📄 Data Files

### ~~services.yaml~~ (DEPRECATED)

**Status**: REMOVED - Services are now loaded directly from database (`test.service_types`)

The `services.yaml` file has been removed as services are now dynamically loaded from the database using:
```python
services = await manager.load_services_from_db(conn)
```

See [Database Integration](#database-integration) section for details.

### business_info.yaml

Company information, hours, contact details.

```yaml
company_name: Lab01-MCP
description: Tienda especializada en tecnología
hours:
  "Lunes a Viernes": "9:00 AM - 6:00 PM"
  "Sábado": "10:00 AM - 2:00 PM"
  "Domingo": "Cerrado"
contact:
  email: support@lab01-mcp.com
  phone: "+1-555-LAB-0001"
```

### policies.yaml

Policies for payment, shipping, returns, warranty.

```yaml
payment_methods:
  accepted:
    - "Tarjetas de crédito"
    - "PayPal"
  not_accepted:
    - "No aceptamos cheques"

shipping:
  standard:
    time: "5-7 días hábiles"
    cost: "GRATIS en compras >$100"
```

## 🔄 Versioning

### Version Management

Versions are controlled in `config/prompt_versions.yaml`:

```yaml
active_versions:
  router: v1.0
  booking: v2.1      # Modular version with 25+ modules
  general: v1.0      # Modular version with 3 modules
  sales: v1.0        # Modular version with 8 modules
```

### Base Templates (Rollback Safety)

The `templates/base/` directory contains **stable copies** of all agent templates:

```
templates/base/
├── router_classification.jinja2
├── booking_agent/           # Complete copy with all modules
├── general_agent/           # Complete copy with all modules
└── sales_agent/             # Complete copy with all modules
```

**Purpose**:
- **Rollback Safety**: Quickly revert to stable versions
- **Comparison**: Compare current vs. base versions
- **Testing**: Test new modules without breaking production

### Creating a New Version

#### For Flat Templates (e.g., Router)

1. **Copy existing template**:

```bash
cp templates/router_classification.jinja2 templates/router_classification_v2.jinja2
```

2. **Make modifications** to v2 template

3. **Update config** to use new version:

```yaml
active_versions:
  router: v2.0  # Changed from v1.0
```

#### For Modular Templates (e.g., Booking)

1. **Backup current module** (optional):

```bash
cp templates/booking_agent/modules/scope_guardrails.jinja2 \
   templates/booking_agent/modules/scope_guardrails.jinja2.backup
```

2. **Modify module** or create new module

3. **Update main template** if needed (add/remove includes)

4. **Test thoroughly**: Render booking prompt

5. **Rollback** (if needed): Restore from `.backup` or `base/`

### Rollback Strategies

**Method 1: Restore from .backup**
```bash
cp templates/booking_agent/modules/scope_guardrails.jinja2.backup \
   templates/booking_agent/modules/scope_guardrails.jinja2
```

**Method 2: Restore from base/**
```bash
cp -r templates/base/booking_agent/ templates/
```

**Method 3: Git revert**
```bash
git checkout HEAD~1 templates/booking_agent/modules/scope_guardrails.jinja2
```

## 🧪 A/B Testing

### Configuring A/B Test

Edit `config/prompt_versions.yaml`:

```yaml
ab_testing:
  enabled: true  # Enable A/B testing

  experiments:
    - name: router_more_specific
      agent: router
      description: "Test more specific intent classification"
      version_a: v1.0
      version_b: v2.0
      traffic_split: 0.5  # 50% to each
      enabled: true
```

### Running an Experiment

```python
manager = PromptManager()

# System automatically splits traffic based on config
prompt = manager.get_router_prompt()  # Gets v1.0 or v2.0 randomly
```

### Analyzing Results

Track metrics by version:

```python
# Log which version was used
version_used = manager.get_active_versions()['router']
logger.info(f"Used version: {version_used}")

# Compare metrics
# - Intent classification accuracy
# - Response time
# - User satisfaction
```

## 🗄️ Database Integration

### Loading Services from Database

**Status**: ✅ ACTIVE - Services are now loaded directly from the database

The system automatically loads services from `test.service_types` table with 15-minute caching.

```python
import psycopg2

# Connect to database
conn = psycopg2.connect(
    host="localhost",
    port=5434,
    database="mcpdb",
    user="mcp_user",
    password="mcp_password"
)

# Load services (cached for 15 minutes)
manager = PromptManager()
services = await manager.load_services_from_db(conn)

# Use in booking prompt
prompt = manager.get_booking_prompt(services=services)
```

### Configuration

In `config/prompt_versions.yaml`:

```yaml
database_integration:
  enabled: true                    # Database integration is active

  # Services data (for booking agent)
  services:
    source: database               # Loading from database (not YAML)
    table: test.service_types      # Database table
    cache_ttl_minutes: 15          # Cache refresh interval

  # Business hours (for general agent)
  business_hours:
    source: database               # Loading from database
    table: test.business_hours
    cache_ttl_minutes: 60
```

### Benefits

- **Always Up-to-Date**: Services reflect database changes within cache TTL
- **Performance**: 15-minute cache reduces database queries
- **Consistency**: Single source of truth (database)
- **No YAML Maintenance**: Services managed via database UI/API

## ✅ Best Practices

### 1. **Separate Structure from Content**

❌ **Bad**: Hardcoded content in code
```python
prompt = "You are a booking agent for Lab01-MCP..."
```

✅ **Good**: Content in template
```jinja2
You are a booking agent for {{ business.company_name }}...
```

### 2. **Use Comments in Templates**

```jinja2
{#
Purpose: Brief description
Variables: List of expected variables
Author: Your name
Version: v1.0
#}
```

### 3. **Provide Fallbacks**

Always provide default values:

```jinja2
{{ business.company_name|default('Lab01-MCP') }}
```

### 4. **Test Templates Before Deployment**

```python
# Test template rendering
manager = PromptManager()
prompt = manager.get_booking_prompt()
assert "RESERVAS" in prompt  # Verify key content
```

### 5. **Version Control Prompts**

- Commit templates to Git
- Use meaningful commit messages
- Tag versions: `git tag v2.0-router-prompt`

### 6. **Document Changes**

Update `docs/NOTAS_CLAUDE.md` when:
- Creating new templates
- Changing data structure
- Modifying version config

### 7. **Dynamic Few-Shot Examples (2025 Best Practice)**

**Overview**: Use dynamic, contextually-relevant examples instead of hardcoded static data.

**Two Modes Available**:

**MODE 1: Dynamic Few-Shot** (Recommended for Production)
- ✅ Inject real examples from database based on user query
- ✅ Adapts in real-time to provide most pertinent examples
- ✅ Best learning from actual product data

```python
# Get contextual examples
example_products = get_relevant_products(user_query, limit=4)

# Render template with dynamic examples
prompt = manager.get_sales_prompt(
    example_products=example_products,  # ← Dynamic injection
    pagination_page_size=4
)
```

**MODE 2: Skeleton Fallback** (Development/Fallback)
- ✅ Uses `[placeholder]` format to teach structure
- ✅ Works when no query context available
- ✅ Zero memorization risk, no hardcoded data

```jinja2
{# Template automatically falls back to skeleton mode #}
{% if example_products %}
  {# Use real examples #}
{% else %}
  {# Use [placeholder] format #}
{% endif %}
```

**Benefits**:
- **Contextual Relevance**: Examples match user's actual needs
- **No Hardcoded Data**: Eliminates static, outdated examples
- **Scalability**: Works across all product categories
- **Token Efficiency**: Only load examples when needed

**Implementation Guide**: See `templates/sales_agent/modules/examples.jinja2` (lines 276-442) for comprehensive Python integration examples including vectorstore-based selection and caching strategies.

**Best Practice**: Always use dynamic mode in production, skeleton mode for testing/development.

## 🐛 Troubleshooting

### Template Not Found Error

**Error**: `jinja2.exceptions.TemplateNotFound`

**Solution**: Check file path and name
```python
# Verify template exists
ls prompts/templates/
```

### Variable Missing in Template

**Error**: Rendered prompt shows `{{  }}`

**Solution**: Provide variable in context
```python
prompt = manager.get_booking_prompt(
    customer_email="maria@example.com"  # Provide missing variable
)
```

### YAML Parsing Error

**Error**: `yaml.scanner.ScannerError`

**Solution**: Check YAML syntax
```bash
# Validate YAML files
python3 -c "import yaml; yaml.safe_load(open('data/business_info.yaml'))"
python3 -c "import yaml; yaml.safe_load(open('data/policies.yaml'))"
python3 -c "import yaml; yaml.safe_load(open('config/prompt_versions.yaml'))"
```

### Module Not Found Error

**Error**: Module file not loading in modular templates

**Solution**: Check module path and file existence
```bash
# Verify module exists
ls prompts/templates/booking_agent/modules/
ls prompts/templates/general_agent/modules/
ls prompts/templates/sales_agent/modules/
```

**Note**: Some modules have `.backup` versions for rollback purposes

### Fallback Mode Active

**Issue**: Changes to templates not reflected

**Solution**: Check `use_templates` flag
```yaml
# In config/prompt_versions.yaml
use_templates: true  # Must be true
```

### Services Not Updating

**Issue**: Services data not reflecting recent database changes

**Solution**:
1. **Check cache TTL**: Services are cached for 15 minutes
   - Wait for cache to expire, or
   - Restart the service to force cache refresh
2. **Verify database connection**: Ensure connection to `test.service_types` table
3. **Check configuration**:
```yaml
# In config/prompt_versions.yaml
database_integration:
  enabled: true
  services:
    source: database  # Must be "database", not "yaml"
    cache_ttl_minutes: 15
```
4. **Manual refresh**: Force reload by restarting PromptManager

## 🤝 Contributing

### Adding a New Agent Template

1. Create template in `templates/`
2. Add data file in `data/` (if needed)
3. Add method to `PromptManager`
4. Update `prompt_versions.yaml`
5. Write tests
6. Update this README

### Modifying Existing Templates

1. Create new version (don't overwrite)
2. Test thoroughly
3. Update version in config
4. Document changes

### Submitting Changes

```bash
# 1. Create feature branch
git checkout -b feature/new-prompt-template

# 2. Make changes
# 3. Commit with clear message
git commit -m "feat: add customer_support agent template"

# 4. Push and create PR
git push origin feature/new-prompt-template
```

## 📚 Additional Resources

- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [YAML Syntax Guide](https://yaml.org/spec/1.2/spec.html)
- [Lab01-MCP Architecture](../docs/NOTAS_CLAUDE.md)
- [Multi-Agent System Design](../README.md)

## 📝 License

This prompt management system is part of the Lab01-MCP project.

## 👥 Authors

Lab01-MCP Team - 2025

---

**Version**: 2.1.0 (Modular Architecture + Dynamic Few-Shot)
**Created**: 2025-10-11
**Last Updated**: 2025-10-21
**Architecture**: Modular templates with 25+ booking modules, 8 sales modules, 3 general modules
**New Features**: Dynamic few-shot examples with skeleton fallback (Google Gemini 2025 best practices)
