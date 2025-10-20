# Agent Tools - Utility Scripts

This directory contains utility scripts and analytics tools for the agent system.

## Available Tools

### `metrics_collector.py`

Analytics tool for collecting and analyzing A/B testing metrics from logs.

**Purpose:** Parse A/B testing decisions, calculate statistics, and export results.

**Features:**
- ✅ Parse logs for A/B test decisions
- ✅ Calculate variant distribution (A/B split)
- ✅ User-level breakdown and consistency tracking
- ✅ Timeline analysis of decisions over time
- ✅ Export results to CSV
- ✅ Visual summary statistics

**Usage:**

```bash
# Parse logs and show summary
python metrics_collector.py --log-file logs/app.log

# Export to CSV for further analysis
python metrics_collector.py --log-file logs/app.log --export metrics.csv

# Real-time monitoring (future feature)
python metrics_collector.py --log-file logs/app.log --watch
```

**Example Output:**

```
================================================================================
  📊 A/B TEST METRICS SUMMARY
================================================================================

Total Decisions: 1042
Unique Users: 156

Variant Distribution:
  Variant A: 521 (50.0%)
  Variant B: 521 (50.0%)

✅ Variance from expected 50/50 split:
  Variant A: 0.0% ✅ OK
  Variant B: 0.0% ✅ OK
```

**Requirements:**

The tool uses only standard Python libraries:
- `re` (regex)
- `collections` (defaultdict)
- `pathlib` (Path)
- `csv` (export)

**Log Format Expected:**

The tool expects log lines in the format:
```
[INFO] A/B test 'sales_pagination_6_products': user=maria@example.com, variant=B, version=v1.1, pagination=6
```

**Integration with Project:**

This tool is designed to work with the A/B testing infrastructure in:
- `src/multi_agent/prompt_manager.py` (A/B variant selection)
- `demos/demo_ab_testing_e2e.py` (demo script)
- `tests/test_ab_testing.py` (A/B testing tests)

**Next Steps:**

1. Enable A/B testing in `prompts/config/prompt_versions.yaml`
2. Run demo: `python demos/demo_ab_testing_e2e.py`
3. Check logs are written to correct location
4. Run this tool: `python tools/metrics_collector.py`
5. Export results for analysis
6. Calculate statistical significance
7. Declare winner and rollout to 100%

**Documentation:**

See `docs/AGENT_AB_TESTING_GUIDE.md` for more information on A/B testing framework.

---

**Last Updated:** 2025-10-20
**Status:** ✅ Production Ready
