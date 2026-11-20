import csv
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import resource_ledger as ledger


HEADER = ["month", "site", "metric", "amount", "unit", "activity_count", "activity_unit"]
BASE = ["2026-01", "Demo", "electricity", "12.50", "kWh", "3", "visitor"]
ROOT = Path(__file__).resolve().parents[1]


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "input.csv"

    def write(self, rows=None, header=None):
        with self.path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(HEADER if header is None else header)
            writer.writerows([BASE] if rows is None else rows)
        return self.path

    def changed(self, **values):
        row = BASE.copy()
        for key, value in values.items():
            row[HEADER.index(key)] = value
        return row

    def report(self, rows=None, header=None):
        return ledger.summarize(ledger.validate_csv(self.write(rows, header)))

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "resource_ledger.py"), *map(str, args)],
                              capture_output=True, text=True, check=False)

    def test_exact_decimal_sum_and_normalization(self):
        report = self.report([self.changed(amount="0.1", activity_count="3"),
                              self.changed(site="Other", amount="0.2", activity_count="3")])
        self.assertEqual(report["monthly_recorded_totals"][0]["metrics"]["electricity"]["recorded_total"], "0.3")
        self.assertEqual(report["periods"][0]["metrics"]["electricity"]["normalized_amount"], "0.033333")

    def test_round_half_up(self):
        report = self.report([self.changed(amount="1", activity_count="128")])
        self.assertEqual(report["periods"][0]["metrics"]["electricity"]["normalized_amount"], "0.007813")

    def test_max_amount_preserves_digits(self):
        amount = "999999999999999999999999"
        report = self.report([self.changed(amount=amount, activity_count="1")])
        self.assertEqual(report["periods"][0]["metrics"]["electricity"]["normalized_amount"], amount)

    def test_zero_is_distinct_from_missing(self):
        metrics = self.report([self.changed(amount="0")])["periods"][0]["metrics"]
        self.assertEqual(metrics["electricity"]["amount"], "0")
        self.assertIsNone(metrics["water"]["amount"])
        self.assertEqual(metrics["water"]["normalization_reason"], "missing_measurement")

    def test_zero_activity_has_reason(self):
        result = self.report([self.changed(activity_count="0")])["periods"][0]["metrics"]["electricity"]
        self.assertIsNone(result["normalized_amount"])
        self.assertEqual(result["normalization_reason"], "zero_activity_count")

    def test_optional_activity_headers_can_be_absent(self):
        result = self.report([BASE[:5]], HEADER[:5])["periods"][0]["metrics"]["electricity"]
        self.assertEqual(result["normalization_reason"], "activity_not_provided")

    def test_optional_activity_fields_can_be_blank(self):
        report = self.report([self.changed(activity_count="", activity_unit="")])
        self.assertIsNone(report["periods"][0]["activity_count"])

    def test_gap_month_and_missing_site_remain_null(self):
        report = self.report([BASE, self.changed(month="2026-03", site="Other")])
        self.assertEqual(report["months"], ["2026-01", "2026-02", "2026-03"])
        self.assertEqual(len(report["periods"]), 6)
        gap = report["monthly_recorded_totals"][1]["metrics"]["electricity"]
        self.assertIsNone(gap["recorded_total"])
        self.assertEqual(gap["reporting_sites"], 0)
        self.assertEqual(gap["missing_sites"], ["Demo", "Other"])

    def test_partial_total_explicitly_names_missing_sites(self):
        report = self.report([BASE, self.changed(site="Other", metric="water", unit="m3")])
        result = report["monthly_recorded_totals"][0]["metrics"]["electricity"]
        self.assertEqual(result["recorded_total"], "12.5")
        self.assertEqual(result["coverage"], "partial_for_known_sites")
        self.assertEqual(result["missing_sites"], ["Other"])

    def test_units_are_never_added_together(self):
        report = self.report([BASE, self.changed(metric="water", unit="m3", amount="2"),
                              self.changed(metric="waste", unit="kg", amount="5")])
        totals = report["monthly_recorded_totals"][0]["metrics"]
        self.assertEqual({key: value["recorded_total"] for key, value in totals.items()},
                         {"electricity": "12.5", "water": "2", "waste": "5"})
        self.assertEqual({key: value["unit"] for key, value in totals.items()}, ledger.UNITS)

    def test_report_deterministic_under_input_reordering(self):
        rows = [BASE, self.changed(site="Other", amount="1"), self.changed(month="2026-02")]
        first = self.report(rows)
        second = self.report(list(reversed(rows)))
        self.assertEqual(ledger.render_json(first), ledger.render_json(second))
        self.assertEqual(ledger.render_markdown(first), ledger.render_markdown(second))

    def test_duplicate_measurement_rejected(self):
        with self.assertRaisesRegex(ledger.ValidationError, "duplicate month/site/metric"):
            ledger.validate_csv(self.write([BASE, BASE]))

    def test_invalid_amounts_rejected(self):
        for amount in ("NaN", "Infinity", "-Infinity", "-1", "1e99999", "1,000", ".5", " 1", "1 ", "", "0" * 25):
            with self.subTest(amount=amount), self.assertRaises(ledger.ValidationError):
                ledger.validate_csv(self.write([self.changed(amount=amount)]))

    def test_invalid_calendar_months_rejected(self):
        for month in ("0000-01", "2026-00", "2026-13", "2026-1", "2026-01-01", "26-01"):
            with self.subTest(month=month), self.assertRaises(ledger.ValidationError):
                ledger.validate_csv(self.write([self.changed(month=month)]))

    def test_invalid_activity_values_rejected(self):
        for count, unit in (("-1", "visitor"), ("1.5", "visitor"), ("1e2", "visitor"),
                            ("9" * 13, "visitor"), ("", "visitor"), ("1", ""),
                            ("1", "=cmd()"), ("1", "visitors per day")):
            with self.subTest(count=count, unit=unit), self.assertRaises(ledger.ValidationError):
                ledger.validate_csv(self.write([self.changed(activity_count=count, activity_unit=unit)]))

    def test_inconsistent_activity_for_same_site_month_rejected(self):
        for second in (self.changed(metric="water", unit="m3", activity_count="4"),
                       self.changed(metric="water", unit="m3", activity_unit="cover"),
                       self.changed(metric="water", unit="m3", activity_count="", activity_unit="")):
            with self.subTest(second=second), self.assertRaisesRegex(ledger.ValidationError, "consistent"):
                ledger.validate_csv(self.write([BASE, second]))

    def test_different_sites_can_use_different_activity_units(self):
        report = self.report([BASE, self.changed(site="Cafe", activity_unit="cover")])
        self.assertEqual({period["activity_unit"] for period in report["periods"]}, {"visitor", "cover"})

    def test_wrong_metric_or_unit_rejected(self):
        for record in (self.changed(metric="gas"), self.changed(unit="kwh"), self.changed(unit="kg")):
            with self.subTest(record=record), self.assertRaises(ledger.ValidationError):
                ledger.validate_csv(self.write([record]))

    def test_headers_reject_duplicate_unknown_missing_or_half_optional(self):
        for header in (HEADER + ["site"], HEADER + ["extra"], HEADER[1:], HEADER[:-1]):
            with self.subTest(header=header), self.assertRaises(ledger.ValidationError):
                ledger.validate_csv(self.write([], header))

    def test_empty_and_header_only_rejected(self):
        for payload in ("", ",".join(HEADER) + "\n"):
            self.path.write_text(payload)
            with self.assertRaises(ledger.ValidationError):
                ledger.validate_csv(self.path)

    def test_malformed_csv_rejected(self):
        self.path.write_text(",".join(HEADER) + '\n2026-01,"unterminated')
        with self.assertRaisesRegex(ledger.ValidationError, "malformed CSV"):
            ledger.validate_csv(self.path)

    def test_ambiguous_unquoted_quote_rejected(self):
        self.path.write_text(",".join(HEADER) + '\n2026-01,De"mo,electricity,1,kWh,1,visitor\n')
        with self.assertRaisesRegex(ledger.ValidationError, "quote inside"):
            ledger.validate_csv(self.path)

    def test_quoted_commas_and_escaped_quotes_accepted(self):
        label = 'Demo, "Cafe"'
        report = self.report([self.changed(site=label)])
        self.assertEqual(report["known_sites"], [label])

    def test_short_long_and_blank_rows_rejected(self):
        for row in (BASE[:-1], BASE + ["extra"], []):
            with self.subTest(row=row), self.assertRaises(ledger.ValidationError):
                ledger.validate_csv(self.write([row]))

    def test_invalid_utf8_and_nul_rejected(self):
        for payload in (b"\xff", b"month,site\x00"):
            self.path.write_bytes(payload)
            with self.assertRaises(ledger.ValidationError):
                ledger.validate_csv(self.path)

    def test_utf8_bom_accepted(self):
        self.write()
        self.path.write_bytes(b"\xef\xbb\xbf" + self.path.read_bytes())
        self.assertEqual(ledger.validate_csv(self.path)[0]["amount"], Decimal("12.50"))

    def test_controls_and_overlong_sites_rejected(self):
        for site in ("", " Demo", "Demo ", "x" * 101, "line\nbreak", "a\u202eb"):
            with self.subTest(site=site), self.assertRaises(ledger.ValidationError):
                ledger.validate_csv(self.write([self.changed(site=site)]))

    def test_markdown_escapes_html_and_explicit_link_syntax(self):
        label = '<img src=x>|[x](https://invalid.example)'
        rendered = ledger.render_markdown(self.report([self.changed(site=label)]))
        self.assertNotIn("<img", rendered)
        self.assertIn("&lt;img", rendered)
        self.assertIn(r"\|\[x\]\(https://invalid.example\)", rendered)

    def test_formula_label_has_no_spreadsheet_export(self):
        label = '=HYPERLINK("https://invalid.example")'
        report = self.report([self.changed(site=label)])
        self.assertEqual(json.loads(ledger.render_json(report))["known_sites"], [label])
        self.assertNotIn("<", ledger.render_markdown(report))
        self.assertEqual(self.cli(self.path, "--format", "csv").returncode, 2)

    def test_file_field_and_row_limits(self):
        self.write()
        with mock.patch.object(ledger, "MAX_BYTES", 10), self.assertRaisesRegex(ledger.ValidationError, "bytes"):
            ledger.validate_csv(self.path)
        with self.assertRaisesRegex(ledger.ValidationError, "field exceeds"):
            ledger.validate_csv(self.write([self.changed(site="x" * 257)]))
        self.write([BASE, self.changed(site="Other")])
        with mock.patch.object(ledger, "MAX_ROWS", 1), self.assertRaisesRegex(ledger.ValidationError, "records"):
            ledger.validate_csv(self.path)

    def test_expanded_report_and_span_limits(self):
        records = ledger.validate_csv(self.write([BASE, self.changed(month="2026-03", site="Other")]))
        with mock.patch.object(ledger, "MAX_ROWS", 5), self.assertRaisesRegex(ledger.ValidationError, "periods"):
            ledger.summarize(records)
        records = ledger.validate_csv(self.write([BASE, self.changed(month="2126-01")]))
        with self.assertRaisesRegex(ledger.ValidationError, "1200"):
            ledger.summarize(records)

    def test_cli_smoke_json_markdown_and_missing_file(self):
        self.write()
        result = self.cli(self.path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["source_record_count"], 1)
        self.assertEqual(result.stderr, "")
        markdown = self.cli(self.path, "--format", "markdown")
        self.assertEqual(markdown.returncode, 0, markdown.stderr)
        self.assertTrue(markdown.stdout.startswith("# Resource Ledger\n"))
        missing = self.cli(Path(self.temp.name) / "absent.csv")
        self.assertEqual(missing.returncode, 3)
        self.assertEqual(missing.stdout, "")

    def test_cli_invalid_input_does_not_touch_output(self):
        self.write([self.changed(amount="NaN")])
        output = Path(self.temp.name) / "existing.json"
        output.write_text("keep")
        result = self.cli(self.path, "--output", output)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(output.read_text(), "keep")
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_output_and_io_error(self):
        self.write()
        output = Path(self.temp.name) / "report.json"
        result = self.cli(self.path, "--output", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(json.loads(output.read_text())["schema_version"], "1.0")
        bad = self.cli(self.path, "--output", Path(self.temp.name) / "missing" / "report.json")
        self.assertEqual(bad.returncode, 3)

    def test_stdout_is_utf8_independent_of_text_stream_encoding(self):
        self.write([self.changed(site="İzmir — Café 🏡")])
        report = ledger.summarize(ledger.validate_csv(self.path))
        for encoding in ("ascii", "cp1252", "utf-16"):
            for fmt, render in (("json", ledger.render_json),
                                ("markdown", ledger.render_markdown)):
                with self.subTest(encoding=encoding, format=fmt):
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "resource_ledger.py"),
                         str(self.path), "--format", fmt],
                        env=dict(os.environ, PYTHONIOENCODING=encoding),
                        capture_output=True, check=False, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, b"")
                    self.assertEqual(result.stdout, render(report).encode("utf-8"))

    def test_main_supports_text_only_stdout_capture(self):
        self.write()
        captured = io.StringIO()
        with redirect_stdout(captured):
            code = ledger.main([str(self.path)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(captured.getvalue())["source_record_count"], 1)

    def test_main_completes_short_binary_writes(self):
        class ShortWriter(io.RawIOBase):
            def __init__(self):
                self.payload = bytearray()

            def writable(self):
                return True

            def write(self, data):
                self.payload.extend(data[:1])
                return min(1, len(data))

        self.write([self.changed(site="İzmir 🏡")])
        raw = ShortWriter()
        with io.TextIOWrapper(raw, encoding="ascii") as captured:
            with redirect_stdout(captured):
                code = ledger.main([str(self.path)])
            self.assertEqual(code, 0)
            parsed = json.loads(bytes(raw.payload).decode("utf-8"))
            self.assertEqual(parsed["known_sites"], ["İzmir 🏡"])
            self.assertEqual(parsed["source_record_count"], 1)

    def test_main_rejects_binary_writes_without_progress(self):
        class StalledWriter(io.RawIOBase):
            def __init__(self, result):
                self.result = result

            def writable(self):
                return True

            def write(self, data):
                return self.result

        self.write()
        for result in (0, None):
            with self.subTest(write_result=result):
                with io.TextIOWrapper(StalledWriter(result), encoding="utf-8") as captured:
                    errors = io.StringIO()
                    with redirect_stdout(captured), redirect_stderr(errors):
                        code = ledger.main([str(self.path)])
                    self.assertEqual(code, 3)
                    self.assertEqual(errors.getvalue(), "I/O error: unable to write report\n")

    def test_main_closed_text_capture_returns_io_error(self):
        self.write()
        captured = io.StringIO()
        captured.close()
        errors = io.StringIO()
        with redirect_stdout(captured), redirect_stderr(errors):
            code = ledger.main([str(self.path)])
        self.assertEqual(code, 3)
        self.assertEqual(errors.getvalue(), "I/O error: unable to write report\n")

    def test_stdout_closed_pipe_returns_io_error_without_shutdown_traceback(self):
        self.write()
        read_fd, write_fd = os.pipe()
        os.close(read_fd)
        with os.fdopen(write_fd, "wb") as sink:
            result = subprocess.run(
                [sys.executable, str(ROOT / "resource_ledger.py"), str(self.path)],
                stdout=sink, stderr=subprocess.PIPE, check=False, timeout=10)
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(result.stderr.splitlines(), [b"I/O error: unable to write report"])

    def test_combined_stdout_stderr_closed_pipe_keeps_io_exit_code(self):
        self.write()
        read_fd, write_fd = os.pipe()
        os.close(read_fd)
        with os.fdopen(write_fd, "wb") as sink:
            result = subprocess.run(
                [sys.executable, str(ROOT / "resource_ledger.py"), str(self.path)],
                stdout=sink, stderr=subprocess.STDOUT, check=False, timeout=10)
        self.assertEqual(result.returncode, 3)

    @unittest.skipUnless(sys.platform.startswith("linux") and Path("/dev/full").exists(),
                         "requires Linux /dev/full for a real ENOSPC write failure")
    def test_stdout_full_device_returns_io_error_without_shutdown_traceback(self):
        self.write()
        with open("/dev/full", "wb") as sink:
            result = subprocess.run(
                [sys.executable, str(ROOT / "resource_ledger.py"), str(self.path)],
                stdout=sink, stderr=subprocess.PIPE, check=False, timeout=10)
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(result.stderr.splitlines(), [b"I/O error: unable to write report"])

    def test_partial_write_failure_preserves_previous_report(self):
        self.write()
        output = Path(self.temp.name) / "report.json"
        output.write_text("PREVIOUS GOOD REPORT")
        original_temporary_file = tempfile.NamedTemporaryFile

        def broken_temporary_file(*args, **kwargs):
            handle = original_temporary_file(*args, **kwargs)
            original_write = handle.write

            def partial_write(text):
                original_write(text[:10])
                handle.flush()
                raise OSError("synthetic disk full")

            handle.write = partial_write
            return handle

        errors = io.StringIO()
        with mock.patch.object(ledger.tempfile, "NamedTemporaryFile", side_effect=broken_temporary_file), redirect_stderr(errors):
            code = ledger.main([str(self.path), "--output", str(output)])
        self.assertEqual(code, 3)
        self.assertEqual(output.read_text(), "PREVIOUS GOOD REPORT")
        self.assertEqual(list(Path(self.temp.name).glob(".resource-ledger-*.tmp")), [])
        self.assertNotIn("synthetic disk full", errors.getvalue())

    def test_fsync_failure_preserves_previous_report(self):
        self.write()
        output = Path(self.temp.name) / "report.json"
        output.write_text("PREVIOUS GOOD REPORT")
        with mock.patch.object(ledger.os, "fsync", side_effect=OSError("synthetic flush error")), redirect_stderr(io.StringIO()):
            code = ledger.main([str(self.path), "--output", str(output)])
        self.assertEqual(code, 3)
        self.assertEqual(output.read_text(), "PREVIOUS GOOD REPORT")
        self.assertEqual(list(Path(self.temp.name).glob(".resource-ledger-*.tmp")), [])

    def test_replace_failure_preserves_previous_report(self):
        self.write()
        output = Path(self.temp.name) / "report.json"
        output.write_text("PREVIOUS GOOD REPORT")
        with mock.patch.object(ledger.os, "replace", side_effect=OSError("synthetic replacement error")), redirect_stderr(io.StringIO()):
            code = ledger.main([str(self.path), "--output", str(output)])
        self.assertEqual(code, 3)
        self.assertEqual(output.read_text(), "PREVIOUS GOOD REPORT")
        self.assertEqual(list(Path(self.temp.name).glob(".resource-ledger-*.tmp")), [])

    def test_output_links_are_replaced_without_modifying_target(self):
        self.write()
        target = Path(self.temp.name) / "linked-target.txt"
        target.write_text("KEEP LINKED TARGET")
        for link_type in ("symlink", "hardlink"):
            with self.subTest(link_type=link_type):
                output = Path(self.temp.name) / f"report-{link_type}.json"
                if link_type == "symlink":
                    output.symlink_to(target)
                else:
                    os.link(target, output)
                result = self.cli(self.path, "--output", output)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(output.read_text())["schema_version"], "1.0")
                self.assertFalse(output.is_symlink())
                self.assertFalse(output.samefile(target))
                self.assertEqual(target.read_text(), "KEEP LINKED TARGET")
        self.assertEqual(list(Path(self.temp.name).glob(".resource-ledger-*.tmp")), [])

    def test_cli_prevents_input_overwrite_including_hardlink(self):
        self.write()
        original = self.path.read_bytes()
        self.assertEqual(self.cli(self.path, "--output", self.path).returncode, 2)
        alias = Path(self.temp.name) / "alias.json"
        os.link(self.path, alias)
        self.assertEqual(self.cli(self.path, "--output", alias).returncode, 2)
        self.assertEqual(self.path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
