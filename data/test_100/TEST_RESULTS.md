# Independent 100-event dataset verification

Passed: all 16 tests in the complete suite (five new fixture tests plus eleven existing regression tests).

This fixture has 100 unique platform events, plus two duplicate copies (102 rows), and 20 unique bank batches, plus two duplicate copies (22 rows).

The 12 expected findings are two each of next-month settlement, prior-month inflow, batch rounding, orphan refund, platform duplicate and bank duplicate. Two valid refunds are also included as negative controls. The currencies are INR, USD and EUR, with five merchants and multiple payment methods.

The generator creates its answer key independently and never imports the reconciliation engine. Tests compare every issue by category, reference, batch, currency, signed cash-gap contribution and affected amount. They also compare all currency platform/bank totals and gap amounts. API findings and exported Excel issues undergo the same exact comparison. All settlement delays are checked to be one or two calendar days. No application logic changes were needed.

Files:
- Reconciliation_100.xlsx: upload this workbook.
- Answer_Key_100.xlsx: independent expected cases and totals.
- Actual_Report_100.xlsx: actual report returned by the report endpoint.
- actual_analysis_100.json: actual analysis output.

Run from the onelab directory:

```powershell
python data_tools/generate_test_100.py
python -m unittest discover -s tests -v
```

The rounding fixture deliberately isolates a 0.004 synthetic fee per event to exercise accumulation. It uses the same workbook schema and half-up rounding convention; its fees are test fixtures rather than the larger sample's percentage pricing. Original sample data and answer key remain unchanged.

These checks exercise Python and HTTP endpoints, not browser interactions.
