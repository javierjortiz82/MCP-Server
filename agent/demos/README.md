# Agent Demo Scripts

This directory contains demonstration and example scripts for the agent system. These are **not automated tests** but interactive demonstrations of the system in action.

## Available Demos

### 1. `demo_interactive.py` (235 lines)
Interactive chatbot demo with multi-turn conversation support.

**Usage:**
```bash
python demos/demo_interactive.py
```

**Features:**
- Live conversation with the agent system
- Multi-agent routing (booking, sales, general)
- Real-time response generation

---

### 2. `demo_ab_testing_e2e.py` (383 lines)
End-to-end A/B testing demonstration comparing different prompt variants.

**Usage:**
```bash
python demos/demo_ab_testing_e2e.py
```

**Features:**
- Compares variant A vs variant B of prompts
- Measures response quality metrics
- Tracks performance differences

---

### 3. `demo_booking_ab_testing.py` (304 lines)
Booking-specific A/B testing with different conversation strategies.

**Usage:**
```bash
python demos/demo_booking_ab_testing.py
```

**Features:**
- Tests booking agent prompt variants
- Evaluates reservation handling quality
- Compares conversation flows

---

### 4. `demo_general_ab_testing.py` (314 lines)
General agent A/B testing for FAQ and information delivery.

**Usage:**
```bash
python demos/demo_general_ab_testing.py
```

**Features:**
- Tests general agent prompt variants
- Evaluates FAQ response quality
- Compares information accuracy

---

## Running Demos

### Prerequisites

Make sure you have the required dependencies installed:

```bash
cd /home/javort/Lab01-MCP/agent
pip install -r requirements.txt
```

Set up your environment variables:

```bash
# Copy template and configure
cp .env.example .env
# Edit .env with your API keys
```

### All Demos

Run all interactive demos sequentially:

```bash
for demo in demos/demo_*.py; do
    echo "Running: $demo"
    python "$demo"
    echo "---"
done
```

---

## Differences: Demos vs Tests

| Aspect | Demos | Tests |
|--------|-------|-------|
| **Location** | `demos/` | `tests/` |
| **Purpose** | Showcase functionality | Verify correctness |
| **Interactivity** | Often interactive | Automated |
| **Output** | User-friendly output | Pass/Fail result |
| **Run with** | `python demo_*.py` | `pytest tests/` |
| **Dependencies** | May need manual setup | Minimal setup (fixtures) |

---

## Documentation

- **Tests:** See `tests/` directory
- **Architecture:** See `src/gemini_agent/` and `src/multi_agent/`
- **Configuration:** See `src/gemini_agent/config/settings.py`

---

**Last Updated:** 2025-10-20
