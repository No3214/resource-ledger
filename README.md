# Resource Ledger

A small, offline electricity, water, and waste ledger for small businesses.

[Türkçe kullanım](README.tr.md)

Validate a monthly CSV and produce a deterministic JSON or Markdown report. Each
metric keeps its own unit. Missing measurements remain missing. No accounts,
network calls, telemetry, API keys, or runtime dependencies are needed.

**Status:** early working MVP. This is a measurement bookkeeping tool, not a
carbon calculator, cost estimator, savings claim, or sustainability certification.
The project has not been validated against a real business's bills.

## Quick start

Python **3.11 or newer** and Git are required for the commands below. Clone the
repository and run the tool directly; no Python package installation is needed:

```sh
git clone https://github.com/No3214/resource-ledger.git
cd resource-ledger
python3 resource_ledger.py examples/synthetic.csv --format markdown
```

If your Python command is `python` (common on Windows), use it in place of `python3`.

**Next: [your first report with your own data](examples/README.md).** The walkthrough
includes a blank CSV template, expected example reports, an intentionally invalid
file, and a private pilot record. Start with the synthetic example before adding
business records.

All data in `examples/synthetic.csv` is invented. It deliberately includes a zero
activity count and missing measurements to demonstrate those states. `--output`
stages the complete report in the destination directory, then atomically replaces
the selected report path. A write, flush, or replacement failure preserves an
existing report. Existing output symlinks/hard links are replaced at that path;
their other linked targets are not edited. Keep reports in a private directory.
The tool refuses to overwrite the input CSV through `--output`, including through
hard links. Shell redirection (`>`) opens or truncates its target before the tool
starts; never redirect output onto the input CSV.

Reports sent to stdout or `--output` use UTF-8. Configure a downstream viewer to
read UTF-8. Stdout is flushed before success is returned; a failed write or flush
returns exit code 3. Pipes and shell redirection can still leave partial output
on failure. Use `--output` for the atomic file replacement described above.

## CSV contract

```csv
month,site,metric,amount,unit,activity_count,activity_unit
2026-01,Demo Cafe,electricity,250,kWh,500,cover
2026-01,Demo Cafe,water,8.5,m3,500,cover
```

| Field | Contract |
| --- | --- |
| `month` | A real calendar month in `YYYY-MM`, years `0001`–`9999`. |
| `site` | A case-sensitive site label, 1–100 characters, with no surrounding whitespace, control characters, or invisible formatting characters. Use exactly the same label for the same site. |
| `metric` | Exactly `electricity`, `water`, or `waste`. |
| `amount` | A nonnegative finite plain decimal, at most 24 characters, such as `0`, `12`, or `12.50`. No exponent, sign, comma, `NaN`, or `Infinity`. |
| `unit` | Exactly `kWh` for electricity, `m3` for water, or `kg` for waste. No automatic conversion. |
| `activity_count` | Optional nonnegative integer of at most 12 digits. |
| `activity_unit` | Optional user-defined ASCII label: a letter followed by letters, digits, `_`, or `-`, at most 40 characters. Examples: `occupied_room_night`, `cover`, `visitor`. |

`amount` must be the **total consumption or waste generated during that month**
for that site, not a cumulative meter reading. Convert cumulative readings into
period consumption before importing. The tool cannot distinguish these meanings
from a numeric value and does not perform that conversion.

The optional activity columns must either both exist or both be omitted. When
present, both cells must be supplied or both blank. Every metric for the same
month/site must carry the same count and activity unit, including blank values.
Counts describe that entire month/site; they are **never added once per metric**.

There must be at most one measurement per month/site/metric. Duplicate records are
errors, even if the amounts match. A site label's spelling is not automatically
corrected or merged. Quoted UTF-8 CSV and a UTF-8 byte-order mark are supported.
Unknown, missing or repeated headers, unequal record widths, blank records,
invalid UTF-8, and malformed quoting fail validation.

## What the report means

- Reports include all known sites for every month between the first and last
  input month. A missing site, metric, or intervening month has `amount: null`.
- `monthly_recorded_totals` add only reported amounts for the **same metric/unit**.
  Each total includes reporting-site count, missing known sites, and coverage.
  A partial recorded total is not an estimate for the entire business. No reported
  measurements means a null total; a real recorded zero remains `"0"`.
- The tool cannot identify sites absent from the entire input or months outside
  its date range. Complete coverage means complete **for known sites only**.
- Normalization is `amount / activity_count`. A positive denominator is required.
  Missing activity returns null with `activity_not_provided`; a zero denominator
  returns null with `zero_activity_count`. Missing measures carry
  `missing_measurement`. Ratios round to six decimal places using `ROUND_HALF_UP`.
- Amounts are JSON strings, calculated with `Decimal`, to preserve decimal values.
  Different activity labels are never combined into a normalized portfolio total.
  No comparisons, improvement percentages, or causal explanations are inferred.

JSON keys and rows are deterministic. Reordering equivalent valid CSV records
produces identical reports. Markdown escapes HTML and explicit Markdown syntax
in labels. Some renderers may automatically make plain URLs or email addresses
clickable; the tool does not disable that renderer behavior.
**There is no CSV/spreadsheet export.** Downstream applications that export these
labels to spreadsheets must handle formula injection themselves.

## Limits and exit codes

Input is capped at 5 MiB, 20,000 data records, and 256 characters per field, with
tighter field-specific limits above. Expanded reports are capped at 20,000
site/month periods and 1,200 calendar months. These bounds prevent accidentally
expanding sparse data into huge reports. Exact duplicate amounts are not summed.

| Exit code | Meaning |
| --- | --- |
| `0` | Valid input, report written. |
| `2` | Invalid CSV/semantics/CLI arguments, or unsafe input-output path overlap. |
| `3` | Input or output I/O failure. |

Validation failures emit a short message to stderr, without a partial report or
raw input rows. `--output` does not create missing parent directories. The tool
does not encrypt reports; store business records using your own access controls.

## Development

```sh
python3 -m unittest discover -s tests -v
```

Tests use Python's standard library. Runtime has no third-party dependencies.
The committed example outputs are checked against the CLI, along with the empty
template and duplicate-record walkthrough. Reference files are read by tests,
never regenerated by CI. Maintainers can also run the
[optional repository contract](contracts/README.md) with Repo Contract Check.
CI runs the tests on Linux with Python 3.11–3.15 and on Windows/macOS with Python
3.12. A separate Python 3.11 job builds and installs a wheel into a clean virtual
environment, runs both installed commands outside the source directory, and
compares their reports with the source commands. The required `test` check passes
only when all platform tests and the installed-wheel job succeed.

`pyproject.toml` also supports optional packaging with setuptools, which is a
build dependency, not required for the direct commands above. No package has been
published to PyPI. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

License: [MIT](LICENSE). Maintained under the No3214 name.
