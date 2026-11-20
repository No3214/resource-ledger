"""Keep the published first-use examples aligned with the real CLI."""

import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


class ExampleTests(unittest.TestCase):
    def cli(self, *arguments):
        return subprocess.run(
            [sys.executable, str(ROOT / "resource_ledger.py"), *map(str, arguments)],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            check=False, timeout=10,
        )

    def test_worked_example_matches_references_and_documented_values(self):
        for output_format, extension in (("json", "json"), ("markdown", "md")):
            with self.subTest(format=output_format):
                result = self.cli(EXAMPLES / "synthetic.csv", "--format", output_format)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual("", result.stderr)
                # Normalize checkout line endings, as the documented text
                # comparison does; preserve all other content and whitespace.
                expected = (EXAMPLES / f"synthetic.expected.{extension}").read_text(
                    encoding="utf-8")
                self.assertEqual(expected, result.stdout)
                if output_format == "json":
                    document = json.loads(result.stdout)
                    self.assertEqual(8, document["source_record_count"])
                    months = {item["month"]: item["metrics"]
                              for item in document["monthly_recorded_totals"]}
                    self.assertEqual(
                        {"electricity": "1450.5", "water": "53.75", "waste": "145"},
                        {metric: item["recorded_total"]
                         for metric, item in months["2026-01"].items()},
                    )
                    february = months["2026-02"]
                    self.assertEqual("1000", february["electricity"]["recorded_total"])
                    self.assertEqual(["Demo Cafe"], february["electricity"]["missing_sites"])
                    self.assertEqual("partial_for_known_sites",
                                     february["electricity"]["coverage"])
                    self.assertIsNone(february["waste"]["recorded_total"])
                    self.assertEqual(0, february["waste"]["reporting_sites"])
                    periods = {(item["month"], item["site"]): item
                               for item in document["periods"]}
                    guesthouse = periods[("2026-02", "Demo Guesthouse")]
                    self.assertEqual(0, guesthouse["activity_count"])
                    electricity = guesthouse["metrics"]["electricity"]
                    self.assertEqual("1000", electricity["amount"])
                    self.assertIsNone(electricity["normalized_amount"])
                    self.assertEqual("zero_activity_count", electricity["normalization_reason"])

    def test_duplicate_example_is_rejected_and_preserves_existing_report(self):
        with tempfile.TemporaryDirectory(prefix="resource-example-") as temporary:
            output = Path(temporary) / "example.md"
            original = b"Existing synthetic report must remain unchanged.\n"
            output.write_bytes(original)
            result = self.cli(EXAMPLES / "invalid-duplicate.csv", "--format", "markdown",
                              "--output", output)
            self.assertEqual(2, result.returncode, result.stderr)
            self.assertEqual("", result.stdout)
            self.assertIn("duplicate month/site/metric measurement", result.stderr)
            self.assertEqual(original, output.read_bytes())

    def test_template_has_five_required_headers_and_no_measurements(self):
        template = EXAMPLES / "template.csv"
        with template.open(encoding="utf-8-sig", newline="") as source:
            records = list(csv.reader(source))
        self.assertEqual(1, len(records), "The published template must remain header-only")
        self.assertEqual(5, len(records[0]))
        self.assertEqual({"month", "site", "metric", "amount", "unit"}, set(records[0]))
        result = self.cli(template)
        self.assertEqual(2, result.returncode, result.stderr)
        self.assertEqual("", result.stdout)
        self.assertIn("input has no data records", result.stderr)


if __name__ == "__main__":
    unittest.main()
