# Your first report

[Türkçe rehber](README.tr.md) · [CSV contract](../README.md#csv-contract)

Run these commands from the repository directory after the main README's clone
step. Python 3.11 or newer is required. Replace `python3` with `python` if that is
your installed command, including on Windows. Everything in this folder is
synthetic or an unfilled template; none is evidence of a real business pilot.

## 1. Run the worked example

Create the output and private input directories, then generate a readable report:

```sh
python3 -c "from pathlib import Path; Path('reports').mkdir(exist_ok=True); Path('private-data').mkdir(exist_ok=True)"
python3 resource_ledger.py examples/synthetic.csv --format markdown --output reports/example.md
```

Expected exit code: **0**. Compare `reports/example.md` with
[synthetic.expected.md](synthetic.expected.md). For JSON consumers, run:

```sh
python3 resource_ledger.py examples/synthetic.csv --output reports/example.json
```

The reference is [synthetic.expected.json](synthetic.expected.json). The eight
input records cover two sites and two months. Check these values yourself:

| Check | Expected result |
| --- | --- |
| January electricity | `1200.50 + 250 = 1450.5 kWh` |
| January water | `45.25 + 8.5 = 53.75 m3` |
| January waste | `110 + 35 = 145 kg` |
| February electricity | `1000 kWh`, partial coverage: Demo Cafe is missing |
| February waste | `null` in JSON, an em dash in Markdown; no measurement, not zero |
| February Demo Guesthouse electricity per activity | `null`, reason `zero_activity_count` |

The sample demonstrates a zero **activity count**, not a recorded zero consumption.
Coverage describes sites present somewhere in the input; it cannot discover an
entirely omitted site. A partial total does not estimate the missing consumption.

## 2. See a rejected file without losing the example report

Use the same **synthetic** output path as above:

```sh
python3 resource_ledger.py examples/invalid-duplicate.csv --format markdown --output reports/example.md
```

Expected exit code: **2**, with a duplicate measurement error on stderr.
Immediately run `echo $?` in Bash/zsh or `$LASTEXITCODE` in PowerShell to see the
code. The previous `reports/example.md` must remain unchanged. Check its text:

```sh
python3 -c "from pathlib import Path; assert Path('reports/example.md').read_text(encoding='utf-8') == Path('examples/synthetic.expected.md').read_text(encoding='utf-8'); print('PASS: example report preserved')"
```

Fix a duplicate by checking the source records and retaining the one intended
monthly measurement. The tool does not add duplicates, even when values match.

## 3. Prepare your own CSV

Copy the five-column [template.csv](template.csv) into your private directory:

```sh
python3 -c "from pathlib import Path; data=Path('examples/template.csv').read_bytes(); f=Path('private-data/my-ledger.csv').open('xb'); f.write(data); f.close()"
```

This command refuses to overwrite an existing file. On a later run, edit your
existing copy or choose another filename. **The template has no measurements and
intentionally fails validation with exit 2 until you add at least one data row.**

Start with one site, one calendar month, and source records you can check. Enter
that month's consumption, not a cumulative meter reading. Use `electricity/kWh`,
`water/m3`, and `waste/kg`; the tool does not convert units. Use a consistent site
label. A label containing a comma must be quoted, for example `"İzmir, Merkez"`.

For an unknown measurement, **omit that month/site/metric row**. Do not leave an
empty amount or substitute `0`. Enter `0` only for a real measured zero. Optional
activity columns can be added together later; the main README explains their
consistency rules. Without them, quantities remain valid and per-activity ratios
remain unavailable.

Preview the saved file as text: **UTF-8, comma-separated fields, decimal point**.
UTF-8 with or without a BOM is accepted. A `.csv` extension does not guarantee
these settings: Excel's delimiter can depend on regional and application settings.
See Microsoft's [CSV export guidance][csv-export] and [UTF-8 import guidance][csv-utf8].

| Symptom | Correction |
| --- | --- |
| Header is `month;site;metric;amount;unit` | Export with a comma field separator. |
| Amount is `"8,5"` or `8,5` | Verify the source quantity, then use `8.5`; do not replace every comma in the file. |
| Turkish text is corrupted | Save as UTF-8 and use your spreadsheet's text/CSV import preview. |
| Output fails with exit 3 | Check that the input exists and the destination directory exists and is writable. |

## 4. Run and reconcile your report

After filling your private CSV:

```sh
python3 resource_ledger.py private-data/my-ledger.csv --format markdown --output reports/my-report.md
```

Expect exit **0** only for a valid file and successful output. Check the period,
site spelling, units, at least one amount against the source record, and each
reported total against the corresponding source amounts. Missing metrics stay
missing. JSON is optional: use `--output reports/my-report.json` without the
`--format markdown` option.

`private-data/` and `reports/` are ignored by Git, but this is not encryption or
access control. Keep bills, business inputs, and reports private. Use `--output`
as shown; never redirect output onto your input CSV.

Copy [pilot-record.md](pilot-record.md) into `reports/` for your own acceptance
notes. Record any help needed, reconciliation result, and a later repeat run.
Its initial status is **NOT_RUN**. Publishing this kit or passing synthetic tests
does not mean that a real business pilot passed.

[csv-export]: https://support.microsoft.com/en-us/excel/get-started/import-or-export-text-txt-or-csv-files
[csv-utf8]: https://support.microsoft.com/en-us/excel/opening-csv-utf-8-files-correctly-in-excel
