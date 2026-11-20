# Security

## Scope

Version 0.1.x is an early local CLI. Reports are not encrypted. Input and output
files remain under the operator's filesystem permissions. The program makes no
network calls and does not run content from CSV files as commands or configuration.

CSV and labels are untrusted. Report parsing, resource exhaustion, incorrect
unit/amount handling, and unsafe rendering are relevant security issues. The
JSON and Markdown outputs are not a promise that another application's import
or spreadsheet export is safe. CSV export is deliberately not implemented.

## Reporting

Do not publish exploit details, business data, or credentials in a public issue.
If this repository's **Security → Report a vulnerability** control is available,
use that private channel. This file does **not** claim that GitHub private
vulnerability reporting is enabled.

If the control is absent, open a minimal public issue requesting a private
security contact, without the vulnerability details. A maintainer must establish
a private contact before you share the reproduction. No response-time or
remediation SLA is promised for this volunteer project.

Use a minimal synthetic reproduction and include the application/Python version,
expected behavior, and observed behavior. Never include token values, private
keys, customer information, or raw real-world source files.
