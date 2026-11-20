# Resource Ledger

Only input sites and the inclusive first-to-last input month. Completeness outside this scope is unknown.

Amounts are separate by metric and unit. An em dash means missing data, not zero.
Normalized values are rounded to 6 decimal places (ROUND_HALF_UP).

## Site / month measurements

| Month | Site | Metric | Amount | Unit | Activity | Per activity | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-01 | Demo Cafe | electricity | 250 | kWh | 500 cover | 0.5 kWh/cover | — |
| 2026-01 | Demo Cafe | water | 8.5 | m3 | 500 cover | 0.017 m3/cover | — |
| 2026-01 | Demo Cafe | waste | 35 | kg | 500 cover | 0.07 kg/cover | — |
| 2026-01 | Demo Guesthouse | electricity | 1200.5 | kWh | 80 occupied\_room\_night | 15.00625 kWh/occupied\_room\_night | — |
| 2026-01 | Demo Guesthouse | water | 45.25 | m3 | 80 occupied\_room\_night | 0.565625 m3/occupied\_room\_night | — |
| 2026-01 | Demo Guesthouse | waste | 110 | kg | 80 occupied\_room\_night | 1.375 kg/occupied\_room\_night | — |
| 2026-02 | Demo Cafe | electricity | — | kWh | — | — | missing\_measurement |
| 2026-02 | Demo Cafe | water | — | m3 | — | — | missing\_measurement |
| 2026-02 | Demo Cafe | waste | — | kg | — | — | missing\_measurement |
| 2026-02 | Demo Guesthouse | electricity | 1000 | kWh | 0 occupied\_room\_night | — | zero\_activity\_count |
| 2026-02 | Demo Guesthouse | water | 42 | m3 | 0 occupied\_room\_night | — | zero\_activity\_count |
| 2026-02 | Demo Guesthouse | waste | — | kg | 0 occupied\_room\_night | — | missing\_measurement |

## Recorded monthly totals

Partial totals include only reported measurements. No mixed-unit or cross-metric total is calculated.

| Month | Metric | Recorded total | Unit | Reporting sites | Missing known sites |
| --- | --- | --- | --- | --- | --- |
| 2026-01 | electricity | 1450.5 | kWh | 2 | — |
| 2026-01 | water | 53.75 | m3 | 2 | — |
| 2026-01 | waste | 145 | kg | 2 | — |
| 2026-02 | electricity | 1000 | kWh | 1 | Demo Cafe |
| 2026-02 | water | 42 | m3 | 1 | Demo Cafe |
| 2026-02 | waste | — | kg | 0 | Demo Cafe, Demo Guesthouse |
