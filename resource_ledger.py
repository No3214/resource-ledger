"""Offline validation and monthly resource summaries. Python 3.11+, stdlib only."""

from __future__ import annotations

import argparse
import csv
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unicodedata

__version__ = "0.1.0"
UNITS = {"electricity": "kWh", "water": "m3", "waste": "kg"}
REQUIRED = {"month", "site", "metric", "amount", "unit"}
OPTIONAL = {"activity_count", "activity_unit"}
MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 20_000
MAX_FIELD = 256
MAX_SITE = 100
MAX_AMOUNT_CHARS = 24
MAX_ACTIVITY_DIGITS = 12


class ValidationError(ValueError):
    """Input is syntactically or semantically invalid."""


def _fail(row: int, message: str) -> None:
    raise ValidationError(f"record {row}: {message}")


def _amount(value: str, row: int) -> Decimal:
    # Fixed decimal notation bounds parsing, arithmetic, and serialized output.
    if not (1 <= len(value) <= MAX_AMOUNT_CHARS):
        _fail(row, f"amount must contain 1–{MAX_AMOUNT_CHARS} characters")
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value) is None:
        _fail(row, "amount must be a nonnegative finite plain decimal (example: 12.50)")
    return Decimal(value)


def _activity(record: dict[str, str], row: int) -> tuple[int | None, str | None]:
    count, unit = record.get("activity_count", ""), record.get("activity_unit", "")
    if count == "" and unit == "":
        return None, None
    if count == "" or unit == "":
        _fail(row, "activity_count and activity_unit must both be supplied or both be blank")
    if re.fullmatch(r"[0-9]{1,12}", count) is None:
        _fail(row, f"activity_count must be a nonnegative integer of at most {MAX_ACTIVITY_DIGITS} digits")
    if re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,39}", unit) is None:
        _fail(row, "activity_unit must be an ASCII label, 1–40 characters, starting with a letter")
    return int(count), unit


def _validate_quoting(text: str) -> None:
    """Reject ambiguous quotes that csv.reader(strict=True) otherwise tolerates."""
    state = "start"
    for char in text:
        if state == "quoted":
            if char == '"':
                state = "closed"
        elif state == "closed":
            if char == '"':
                state = "quoted"  # Escaped double quote.
            elif char in ",\r\n":
                state = "start"
            else:
                raise ValidationError("malformed CSV: unexpected character after closing quote")
        elif char in ",\r\n":
            state = "start"
        elif char == '"':
            if state != "start":
                raise ValidationError("malformed CSV: quote inside an unquoted field")
            state = "quoted"
        else:
            state = "unquoted"
    if state == "quoted":
        raise ValidationError("malformed CSV: unterminated quoted field")


def validate_csv(path: Path) -> list[dict]:
    """Read a bounded UTF-8 CSV. No network, subprocesses, or configuration execution."""
    with path.open("rb") as handle:
        payload = handle.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValidationError(f"input exceeds {MAX_BYTES} bytes")
    try:
        decoded = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError("input must be UTF-8") from exc
    if "\x00" in decoded:
        raise ValidationError("NUL bytes are not allowed")
    _validate_quoting(decoded)
    reader = csv.reader(io.StringIO(decoded, newline=""), strict=True)
    records: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    activities: dict[tuple[str, str], tuple[int | None, str | None]] = {}
    try:
        header = next(reader, None)
        if header is None:
            raise ValidationError("input is empty")
        if len(header) != len(set(header)):
            raise ValidationError("duplicate CSV header")
        if not REQUIRED.issubset(header) or set(header) - REQUIRED - OPTIONAL:
            raise ValidationError("headers must include month,site,metric,amount,unit; only activity_count,activity_unit are optional")
        if len(set(header) & OPTIONAL) == 1:
            raise ValidationError("optional activity headers must be supplied together")
        for row_number, values in enumerate(reader, start=2):
            if len(records) >= MAX_ROWS:
                raise ValidationError(f"input exceeds {MAX_ROWS} data records")
            if len(values) != len(header):
                _fail(row_number, "CSV field count does not match header (blank records are not allowed)")
            if any(len(value) > MAX_FIELD for value in values):
                _fail(row_number, f"field exceeds {MAX_FIELD} characters")
            record = dict(zip(header, values))
            month = record["month"]
            if re.fullmatch(r"[0-9]{4}-[0-9]{2}", month) is None:
                _fail(row_number, "month must be YYYY-MM")
            try:
                date(int(month[:4]), int(month[5:]), 1)
            except ValueError as exc:
                raise ValidationError(f"record {row_number}: invalid calendar month") from exc
            site = record["site"]
            if not 1 <= len(site) <= MAX_SITE or site != site.strip():
                _fail(row_number, f"site must be 1–{MAX_SITE} characters without surrounding whitespace")
            if any(unicodedata.category(char).startswith("C") for char in site):
                _fail(row_number, "site must not contain control or invisible formatting characters")
            metric, unit = record["metric"], record["unit"]
            if metric not in UNITS:
                _fail(row_number, "metric must be electricity, water, or waste")
            if unit != UNITS[metric]:
                _fail(row_number, f"unit for {metric} must be exactly {UNITS[metric]}")
            quantity = _amount(record["amount"], row_number)
            activity = _activity(record, row_number)
            key = (month, site, metric)
            if key in seen:
                _fail(row_number, "duplicate month/site/metric measurement")
            period = (month, site)
            if period in activities and activities[period] != activity:
                _fail(row_number, "activity_count/unit must be consistent for every metric in the same month/site")
            seen.add(key)
            activities[period] = activity
            records.append({"month": month, "site": site, "metric": metric,
                            "amount": quantity, "activity_count": activity[0], "activity_unit": activity[1]})
    except csv.Error as exc:
        raise ValidationError(f"malformed CSV near physical line {reader.line_num}") from exc
    if not records:
        raise ValidationError("input has no data records")
    return records


def decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _month_range(first: str, last: str) -> list[str]:
    start = int(first[:4]) * 12 + int(first[5:]) - 1
    end = int(last[:4]) * 12 + int(last[5:]) - 1
    # CSV can contain valid but distant years; refuse an enormous expanded report.
    if end - start >= 1200:
        raise ValidationError("report span exceeds 1200 calendar months")
    return [f"{index // 12:04d}-{index % 12 + 1:02d}" for index in range(start, end + 1)]


def summarize(records: list[dict]) -> dict:
    """Group every known site/month; missing measurements remain null, never zero."""
    months_observed = sorted({record["month"] for record in records})
    months = _month_range(months_observed[0], months_observed[-1])
    sites = sorted({record["site"] for record in records})
    if len(months) * len(sites) > MAX_ROWS:
        raise ValidationError(f"expanded site/month report exceeds {MAX_ROWS} periods")
    lookup = {(r["month"], r["site"], r["metric"]): r for r in records}
    activities = {(r["month"], r["site"]): (r["activity_count"], r["activity_unit"]) for r in records}
    periods = []
    totals = []
    with localcontext() as context:
        context.prec = 64
        for month in months:
            for site in sites:
                count, activity_unit = activities.get((month, site), (None, None))
                metrics = {}
                for metric, unit in UNITS.items():
                    record = lookup.get((month, site, metric))
                    normalized = None
                    if record is None:
                        reason = "missing_measurement"
                    elif count is None:
                        reason = "activity_not_provided"
                    elif count == 0:
                        reason = "zero_activity_count"
                    else:
                        ratio = record["amount"] / Decimal(count)
                        normalized = decimal_text(ratio.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
                        reason = None
                    metrics[metric] = {
                        "amount": decimal_text(record["amount"]) if record else None,
                        "unit": unit,
                        "normalized_amount": normalized,
                        "normalized_unit": f"{unit}/{activity_unit}" if activity_unit else None,
                        "normalization_reason": reason,
                    }
                periods.append({"month": month, "site": site,
                                "activity_count": count, "activity_unit": activity_unit,
                                "metrics": metrics})
            by_metric = {}
            for metric, unit in UNITS.items():
                observed = [lookup[(month, site, metric)] for site in sites if (month, site, metric) in lookup]
                missing_sites = [site for site in sites if (month, site, metric) not in lookup]
                by_metric[metric] = {
                    "recorded_total": decimal_text(sum((r["amount"] for r in observed), Decimal(0))) if observed else None,
                    "unit": unit,
                    "reporting_sites": len(observed),
                    "missing_sites": missing_sites,
                    "coverage": "complete_for_known_sites" if not missing_sites else "partial_for_known_sites",
                }
            totals.append({"month": month, "metrics": by_metric})
    return {
        "schema_version": "1.0",
        "source_record_count": len(records),
        "known_sites": sites,
        "months": months,
        "normalization": {"decimal_places": 6, "rounding": "ROUND_HALF_UP"},
        "scope": "Only input sites and the inclusive first-to-last input month. Completeness outside this scope is unknown.",
        "periods": periods,
        "monthly_recorded_totals": totals,
    }


def render_json(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"


def _markdown(value: object) -> str:
    # Escape HTML and explicit Markdown delimiters; renderer autolinks may remain.
    text = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for char in ("\\", "`", "*", "_", "[", "]", "(", ")", "#", "!", "|"):
        text = text.replace(char, "\\" + char)
    return text


def render_markdown(report: dict) -> str:
    lines = ["# Resource Ledger", "", report["scope"], "",
             "Amounts are separate by metric and unit. An em dash means missing data, not zero.",
             "Normalized values are rounded to 6 decimal places (ROUND_HALF_UP).", "",
             "## Site / month measurements", "",
             "| Month | Site | Metric | Amount | Unit | Activity | Per activity | Reason |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for period in report["periods"]:
        count, activity_unit = period["activity_count"], period["activity_unit"]
        activity = f"{count} {activity_unit}" if count is not None else "—"
        for metric, result in period["metrics"].items():
            normalized = f"{result['normalized_amount']} {result['normalized_unit']}" if result["normalized_amount"] is not None else "—"
            cells = (period["month"], period["site"], metric,
                     result["amount"] if result["amount"] is not None else "—", result["unit"],
                     activity, normalized, result["normalization_reason"] or "—")
            lines.append("| " + " | ".join(_markdown(cell) for cell in cells) + " |")
    lines += ["", "## Recorded monthly totals", "",
              "Partial totals include only reported measurements. No mixed-unit or cross-metric total is calculated.", "",
              "| Month | Metric | Recorded total | Unit | Reporting sites | Missing known sites |",
              "| --- | --- | --- | --- | --- | --- |"]
    for total in report["monthly_recorded_totals"]:
        for metric, result in total["metrics"].items():
            cells = (total["month"], metric,
                     result["recorded_total"] if result["recorded_total"] is not None else "—",
                     result["unit"], result["reporting_sites"], ", ".join(result["missing_sites"]) or "—")
            lines.append("| " + " | ".join(_markdown(cell) for cell in cells) + " |")
    return "\n".join(lines) + "\n"


def _discard_failed_stream(stream) -> None:
    """Prevent a failed descriptor from being flushed again at shutdown."""
    try:
        fd = stream.fileno()
        with open(os.devnull, "wb") as sink:
            os.dup2(sink.fileno(), fd)
    except (OSError, AttributeError, ValueError):
        # Closed or text-only captures may have no descriptor to redirect.
        pass


def _write_stream_utf8(stream, output: str) -> None:
    """Complete short writes, then flush; zero progress is an I/O failure."""
    binary = getattr(stream, "buffer", None)
    target = stream if binary is None else binary
    # Text-only capture (for example StringIO) remains supported. Memoryview
    # slices avoid copying the remaining byte payload after each short write.
    payload = output if binary is None else memoryview(output.encode("utf-8"))
    offset = 0
    while offset < len(payload):
        chunk = payload[offset:offset + 65536]
        written = target.write(chunk)
        if type(written) is not int or not 0 < written <= len(chunk):
            raise OSError("output stream did not make valid progress")
        offset += written
    stream.flush()


def _write_stdout_utf8(output: str) -> None:
    """Emit UTF-8 and detect buffered I/O errors before reporting success."""
    try:
        _write_stream_utf8(sys.stdout, output)
    except (OSError, ValueError):
        _discard_failed_stream(sys.stdout)
        raise


def _diagnostic(message: str) -> None:
    """A failed stderr must not replace the documented process exit code."""
    try:
        _write_stream_utf8(sys.stderr, message + "\n")
    except (OSError, ValueError):
        _discard_failed_stream(sys.stderr)


def _write_report_atomic(path: Path, output: str) -> None:
    """Replace the chosen pathname only after the complete report is written."""
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, prefix=".resource-ledger-",
                                         suffix=".tmp", delete=False) as handle:
            temporary_path = Path(handle.name)
            handle.write(output)
            handle.flush()
            os.fsync(handle.fileno())
        # Same-directory staging keeps replacement on the destination filesystem.
        # Existing output symlinks/hard links are replaced, not followed/modified.
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                # Preserve the original failure if filesystem cleanup also fails.
                pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UTF-8 input CSV")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path, help="write to a file instead of standard output")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    try:
        if args.output:
            same_path = args.input.resolve() == args.output.resolve()
            same_file = args.output.exists() and args.input.exists() and args.input.samefile(args.output)
            if same_path or same_file:
                raise ValidationError("output must not overwrite the input CSV")
        report = summarize(validate_csv(args.input))
        output = render_json(report) if args.format == "json" else render_markdown(report)
    except ValidationError as exc:
        _diagnostic(f"validation error: {exc}")
        return 2
    except OSError:
        _diagnostic("I/O error: unable to read input file")
        return 3
    try:
        if args.output:
            _write_report_atomic(args.output, output)
        else:
            _write_stdout_utf8(output)
    except (OSError, ValueError):
        _diagnostic("I/O error: unable to write report")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
