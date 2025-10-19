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

The Prompt Management System provides a centralized, modular approach to managing AI agent prompts for Lab01-MCP's multi-agent system. It replaces hardcoded prompts with external Jinja2 templates and YAML configuration files, enabling:

- **Separation of Concerns**: Code vs content separation
- **Version Control**: Multiple prompt versions coexist
- **A/B Testing**: Compare different prompt strategies
- **Database Integration**: Load dynamic data (services, hours)
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
├── templates/           # Jinja2 prompt templates
│   ├── router_classification.jinja2
│   ├── booking_agent.jinja2
│   ├── general_agent.jinja2
│   └── sales_agent.jinja2
├── data/               # YAML configuration data
│   ├── services.yaml
│   ├── business_info.yaml
│   └── policies.yaml
├── config/             # Version management
│   └── prompt_versions.yaml
└── README.md           # This file
```

### Components

1. **PromptManager** (`agent/src/multi_agent/prompt_manager.py`)
   - Loads and renders Jinja2 templates
   - Manages versions and A/B testing
   - Integrates with database for dynamic data

2. **Templates** (`templates/`)
   - Jinja2 templates for each agent
   - Support variables, loops, conditionals
   - Clean separation of structure and content

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

### Templates Directory

```
templates/
├── router_classification.jinja2    # Intent classification (40 lines)
├── booking_agent.jinja2             # Booking/appointments (60 lines)
├── general_agent.jinja2             # FAQ/general info (90 lines)
└── sales_agent.jinja2               # Sales/products (600+ lines)
```

### Data Directory

```
data/
├── services.yaml        # Booking services (temporary, will load from DB)
├── business_info.yaml   # Company info, hours, contact
└── policies.yaml        # Payment, shipping, returns, warranty
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

## 📄 Data Files

### services.yaml

Defines booking services. **Note**: Will be replaced by database loading in Fase 3.

```yaml
services:
  - name: consultation
    display_name: Consulta General
    description: Consulta general de servicios disponibles
    duration_minutes: 30
    price: 50.00
    color: "#4A90E2"
    icon: chat
```

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
  booking: v1.0
  general: v1.0
  sales: v1.0
```

### Creating a New Version

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

4. **Test**: System automatically loads v2.0

5. **Rollback** (if needed): Change back to v1.0 in config

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

**Current State (Fase 2)**: Services loaded from `data/services.yaml`

**Future State (Fase 3)**: Services loaded directly from database

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

# Load services
manager = PromptManager()
services = await manager.load_services_from_db(conn)

# Use in prompt
prompt = manager.get_booking_prompt(services=services)
```

### Configuration

In `config/prompt_versions.yaml`:

```yaml
database_integration:
  enabled: true
  services:
    source: database  # "database" or "yaml"
    table: test.service_types
    cache_ttl_minutes: 15
```

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
# Validate YAML
python3 -c "import yaml; yaml.safe_load(open('data/services.yaml'))"
```

### Fallback Mode Active

**Issue**: Changes to templates not reflected

**Solution**: Check `use_templates` flag
```yaml
# In config/prompt_versions.yaml
use_templates: true  # Must be true
```

### Services Not Updating

**Issue**: Services data not current

**Solution**:
1. Check `data/services.yaml` is up-to-date
2. Or enable database integration:
```yaml
database_integration:
  enabled: true
  services:
    source: database
```

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

**Version**: 1.0.0
**Created**: 2025-10-11
**Last Updated**: 2025-10-11
