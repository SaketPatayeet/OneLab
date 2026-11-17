# Dataset decisions and assumptions

Scope: data generation only; application logic is deferred. Earlier application drafts do not define this dataset.

## Accepted design

- October 2026 close. Platform dates: September 28-November 4 inclusive. Bank dates extend through November 6 to cover all trailing settlements.
- 1,000 unique platform events: 984 payments and 16 refunds. Six duplicate rows are additional, giving 1,006 platform rows.
- Assumption: multiple currencies, INR, USD and EUR; settlement in original currency with no conversion. Totals remain separate by currency.
- Assumption: five synthetic merchants and multiple payment methods. Cards and bank transfers support all currencies; UPI supports INR only.
- Assumption: one daily settlement batch per merchant per currency with activity, combining payment methods. Both sources share a batch reference.
- Assumption: settlement cash is net of processing fees.
- Settlement timing: one or two calendar days after activity, including weekends. No holidays, intraday cutoffs or timezone conversion; all events in a batch settle together.
- Delivery: Excel dataset plus a separate Excel answer key. Anomaly labels appear only in the answer key.

## Synthetic amounts and fees

These are test assumptions, not actual provider pricing.

- Most purchases: USD/EUR 5-200 or INR 400-16,000. Occasional large purchases: USD/EUR 1,000-5,000 or INR 80,000-400,000. Selection uses a seeded 92%/8% mixture.
- Cards: 2.9% plus INR 2.00, USD 0.30 or EUR 0.25.
- Bank transfer: 0.8% plus INR 1.00, USD 0.10 or EUR 0.10.
- UPI: synthetic 0.3% with no fixed fee.
- Decimal arithmetic; half-up rounding to two decimals. Platform net equals signed gross minus rounded fee. Unrounded fee is retained as an audit field.
- Normally the bank sums rounded transaction nets. Eight planted batches instead sum unrounded nets and round once, creating aggregate differences.
- Refunds reverse full gross amounts, carry negative amounts and incur zero additional fee; original payment fees are retained. Eight have supplied earlier originals; eight refer to originals absent from all supplied history.
- A settled orphan refund is an integrity exception with no additional cash-gap impact.
- All events are completed. Failed payments, chargebacks, reserves, tax and split settlements are outside scope.

## Cases and boundary context

- 19 October batches settle in November within the normal delay: a close-period timing difference.
- Eight batch rounding differences.
- Six exact repeated platform rows and six exact repeated bank rows. IDs and contents are unchanged on duplicate rows.
- Eight orphan refunds.
- 17 September batches arrive in October, documented as prior-month inflow context.
- Cases can share a batch. Answer-key impacts are signed contributions to October platform net minus October bank cash, separately by currency.

## Files and validation

- data/Onelab_Reconciliation_Data.xlsx: transactions, bank settlements, merchants, fee rules and data dictionary.
- data/Onelab_Answer_Key.xlsx: case list, October currency gap bridge, canonical batch truth and case counts.
- data/validation_report.json: decimal totals and validation outcome.
- data_tools/generate_excel.py: reproducible generator, seed 92026; requires Python and openpyxl.
- Financial calculations use Decimal before writing numeric Excel cells; dates are Excel dates.
- Validation passed: unique and imported counts, workbook reload, merchant/currency batch isolation, all settlement delays, orphan count, rounding count, and zero unexplained October gap per currency.
