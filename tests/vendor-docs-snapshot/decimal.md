# Decimal Class
Source: omni-automation.com (live page returned 404 on 2026-05-01; identifiers
captured from probing the running OmniPlan 4.10.2 omniJS surface).

## Class Functions (Constructors)
- Decimal.fromString

## Instance Methods
- add
- subtract
- multiply
- divide
- compare
- equals
- toString

## Notes
- `Decimal.fromString("100.00")` round-trips with trailing zeros collapsed
  (reads back as `"100"`).
- No documented number-extraction accessor; we regex-parse `toString` output.
