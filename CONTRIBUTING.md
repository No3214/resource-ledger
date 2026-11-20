# Contributing

Start with a reproducible problem and a small synthetic CSV. Never attach a real
business bill, customer record, credential, or private report to an issue or PR.

1. Use Python 3.11+ and work on a branch.
2. Keep the runtime standard-library-only and offline.
3. Add a regression test for changes to validation or arithmetic.
4. Run `python3 -m unittest discover -s tests -v` and both example output formats.
5. Describe behavior, limitations, and test evidence in the PR.

Preserve distinct units, missing-data semantics, bounded inputs, deterministic
output, and private data handling. Do not add telemetry, automatic uploads,
carbon factors, or claimed savings without a separately discussed scope.

Useful first contributions include clearer Turkish/English errors and reviewed
synthetic examples. Please keep translation changes consistent with the data
contract. Small readable changes are easier to maintain than framework migrations.
