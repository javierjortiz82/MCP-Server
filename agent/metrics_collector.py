#!/usr/bin/env python3
"""Metrics Collector for A/B Testing Results.

This script parses logs to extract A/B testing decisions and calculate metrics.
Use this as a starting point for building an analytics dashboard.

Usage:
    # Parse logs and show summary
    python metrics_collector.py --log-file logs/app.log

    # Export to CSV
    python metrics_collector.py --log-file logs/app.log --export metrics.csv

    # Real-time monitoring
    python metrics_collector.py --log-file logs/app.log --watch
"""

import re
from collections import defaultdict
from pathlib import Path


class ABTestMetricsCollector:
    """Collector for A/B test metrics from logs."""

    def __init__(self, log_file: str):
        self.log_file = Path(log_file)
        self.decisions = []  # List of (timestamp, user_id, variant, version, pagination)

    def parse_logs(self):
        """Parse log file for A/B test decisions."""
        if not self.log_file.exists():
            print(f"❌ Log file not found: {self.log_file}")
            print("   Create it or specify correct path with --log-file")
            return

        # Regex pattern for A/B test log lines
        # Example: [INFO] A/B test 'sales_pagination_6_products': user=maria@..., variant=B, version=v1.1, pagination=6
        pattern = r"\[INFO\] A/B test '([^']+)': user=([^,]+), variant=([AB]), version=([^,]+), pagination=(\d+)"

        with open(self.log_file) as f:
            for line in f:
                match = re.search(pattern, line)
                if match:
                    experiment = match.group(1)
                    user_id = match.group(2)
                    variant = match.group(3)
                    version = match.group(4)
                    pagination = int(match.group(5))

                    # Extract timestamp (assuming format: YYYY-MM-DD HH:MM:SS)
                    timestamp_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
                    timestamp = timestamp_match.group(1) if timestamp_match else None

                    self.decisions.append(
                        {
                            "timestamp": timestamp,
                            "experiment": experiment,
                            "user_id": user_id,
                            "variant": variant,
                            "version": version,
                            "pagination": pagination,
                        }
                    )

        print(f"✅ Parsed {len(self.decisions)} A/B test decisions from {self.log_file}")

    def calculate_summary(self) -> dict:
        """Calculate summary statistics."""
        if not self.decisions:
            return {}

        summary = {
            "total_decisions": len(self.decisions),
            "unique_users": len({d["user_id"] for d in self.decisions}),
            "variant_a_count": sum(1 for d in self.decisions if d["variant"] == "A"),
            "variant_b_count": sum(1 for d in self.decisions if d["variant"] == "B"),
        }

        summary["variant_a_pct"] = (summary["variant_a_count"] / summary["total_decisions"]) * 100
        summary["variant_b_pct"] = (summary["variant_b_count"] / summary["total_decisions"]) * 100

        return summary

    def show_summary(self):
        """Display summary statistics."""
        print("\n" + "=" * 80)
        print("  📊 A/B TEST METRICS SUMMARY")
        print("=" * 80 + "\n")

        summary = self.calculate_summary()

        if not summary:
            print("❌ No A/B test decisions found in logs")
            print("   Make sure A/B testing is enabled and users are making requests")
            return

        print(f"Total Decisions: {summary['total_decisions']}")
        print(f"Unique Users: {summary['unique_users']}")
        print("\nVariant Distribution:")
        print(f"  Variant A: {summary['variant_a_count']} ({summary['variant_a_pct']:.1f}%)")
        print(f"  Variant B: {summary['variant_b_count']} ({summary['variant_b_pct']:.1f}%)")

        # Expected: ~50/50 split
        expected_split = 50.0
        variance_a = abs(summary["variant_a_pct"] - expected_split)
        variance_b = abs(summary["variant_b_pct"] - expected_split)

        print("\n✅ Variance from expected 50/50 split:")
        print(f"  Variant A: {variance_a:.1f}% {'✅ OK' if variance_a < 10 else '⚠️ HIGH'}")
        print(f"  Variant B: {variance_b:.1f}% {'✅ OK' if variance_b < 10 else '⚠️ HIGH'}")

    def show_user_breakdown(self, limit: int = 10):
        """Show breakdown by user."""
        print("\n" + "-" * 80)
        print(f"  👥 USER BREAKDOWN (Top {limit} users)")
        print("-" * 80 + "\n")

        user_variants = defaultdict(list)
        for decision in self.decisions:
            user_variants[decision["user_id"]].append(decision["variant"])

        # Sort by number of decisions
        sorted_users = sorted(user_variants.items(), key=lambda x: len(x[1]), reverse=True)

        print(f"{'User ID':<30} {'Decisions':<12} {'Variant':<10} {'Consistency':<12}")
        print("-" * 70)

        for user_id, variants in sorted_users[:limit]:
            decisions_count = len(variants)
            primary_variant = max(set(variants), key=variants.count)
            consistency = (variants.count(primary_variant) / decisions_count) * 100

            print(f"{user_id:<30} {decisions_count:<12} {primary_variant:<10} {consistency:.0f}%")

    def show_timeline(self):
        """Show decisions over time."""
        print("\n" + "-" * 80)
        print("  📅 TIMELINE BREAKDOWN")
        print("-" * 80 + "\n")

        if not self.decisions:
            print("No data available")
            return

        # Group by timestamp (date only)
        timeline = defaultdict(lambda: {"A": 0, "B": 0})

        for decision in self.decisions:
            if decision["timestamp"]:
                date = decision["timestamp"].split()[0]  # Extract date part
                timeline[date][decision["variant"]] += 1

        # Sort by date
        sorted_dates = sorted(timeline.items())

        print(f"{'Date':<15} {'Variant A':<12} {'Variant B':<12} {'Total':<10}")
        print("-" * 55)

        for date, variants in sorted_dates:
            total = variants["A"] + variants["B"]
            print(f"{date:<15} {variants['A']:<12} {variants['B']:<12} {total:<10}")

    def export_to_csv(self, output_file: str):
        """Export decisions to CSV."""
        import csv

        if not self.decisions:
            print("❌ No data to export")
            return

        with open(output_file, "w", newline="") as f:
            fieldnames = ["timestamp", "experiment", "user_id", "variant", "version", "pagination"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            for decision in self.decisions:
                writer.writerow(decision)

        print(f"\n✅ Exported {len(self.decisions)} decisions to {output_file}")

    def run_analysis(self):
        """Run complete analysis."""
        self.parse_logs()

        if not self.decisions:
            print("\n💡 Tips to generate A/B test data:")
            print("   1. Enable A/B testing in prompts/config/prompt_versions.yaml")
            print("   2. Run demo: python demo_ab_testing_e2e.py")
            print("   3. Check logs are being written to correct location")
            return

        self.show_summary()
        self.show_user_breakdown()
        self.show_timeline()

        print("\n" + "=" * 80)
        print("  📝 NEXT STEPS")
        print("=" * 80 + "\n")
        print("1. Add conversion tracking to your application")
        print("2. Log conversion events alongside A/B decisions")
        print("3. Calculate conversion_rate per variant")
        print("4. Run statistical significance test")
        print("5. Declare winner and rollout to 100%")
        print("\nFor more info, see: agent/README_AB_TESTING.md")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Collect A/B test metrics from logs")
    parser.add_argument(
        "--log-file", default="logs/app.log", help="Path to log file (default: logs/app.log)"
    )
    parser.add_argument("--export", help="Export to CSV file")
    parser.add_argument(
        "--watch", action="store_true", help="Real-time monitoring (not implemented yet)"
    )

    args = parser.parse_args()

    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  A/B TESTING METRICS COLLECTOR".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    collector = ABTestMetricsCollector(args.log_file)
    collector.run_analysis()

    if args.export:
        collector.export_to_csv(args.export)

    if args.watch:
        print("\n⚠️  Real-time monitoring not implemented yet")
        print("    Run this script periodically or implement --watch mode")


if __name__ == "__main__":
    main()
