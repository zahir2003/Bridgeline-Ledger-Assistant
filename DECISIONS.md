# Design Decisions

## 1. Hybrid AI + Deterministic Architecture

### Decision

Use Ollama for natural-language understanding and Python/Pandas for
financial calculations.

### Why

Financial values should not depend on an LLM's ability to perform
arithmetic correctly.

The architecture is:

``` text
User Question
      ↓
Ollama
      ↓
Intent Classification
      ↓
Python Query Router
      ↓
Deterministic Analytics
      ↓
Answer + Source Rows + Policy
```

This provides both natural-language interaction and reliable
calculations.

------------------------------------------------------------------------

## 2. Local Ollama Instead of Cloud AI

### Decision

Use Ollama and local models.

### Why

The assignment requires an on-prem/local AI approach and does not
require paid cloud AI.

Running Ollama locally also keeps ledger processing on the local
machine.

------------------------------------------------------------------------

## 3. Python for Financial Calculations

### Decision

Use Python/Pandas for all calculations.

### Why

Python gives:

-   Exact arithmetic.
-   Repeatable results.
-   Easy filtering and aggregation.
-   Easy testing.
-   Clear business rules.

The LLM only identifies what the user is asking.

------------------------------------------------------------------------

## 4. GSTIN-First Vendor Identity

### Decision

Use GSTIN as the primary vendor identity when available.

### Why

The same supplier can appear with different spellings.

For example, the ledger contains variations such as:

``` text
Konark Fabrication Pvt. Ltd.
KONARK FABRICATION
Konark Fabrication
Konark Fab
```

Using GSTIN prevents these spelling differences from being treated as
different vendors.

A normalized vendor-name fallback is used when GSTIN is unavailable.

------------------------------------------------------------------------

## 5. Duplicate Invoice Handling

### Decision

When the same invoice number appears more than once, the later/revised
row supersedes the earlier row.

### Why

This follows the provided payment policy and prevents duplicate amounts
from being counted twice.

------------------------------------------------------------------------

## 6. Credit Notes

### Decision

Credit notes are preserved as negative amounts.

### Why

A credit note reduces the vendor payable and should remain visible in
the ledger calculations.

Credit notes do not have a due date and are never treated as overdue.

------------------------------------------------------------------------

## 7. Currency Conversion

### Decision

Convert USD values to INR using the fixed rate:

``` text
1 USD = ₹83.50
```

### Why

USD values cannot be directly added to INR totals.

The fixed conversion rate is explicitly provided by the assignment
policy.

------------------------------------------------------------------------

## 8. Overdue Calculation

### Decision

Calculate overdue status using invoice date, payment status/payment
date, reporting date, and category-specific payment terms.

### Why

The payment policy defines overdue status using elapsed days against the
standard payment term.

The default reporting date is:

``` text
31 March 2025
```

------------------------------------------------------------------------

## 9. Payment Delay

### Decision

Use:

``` text
payment date - invoice date - standard payment term
```

### Why

The assignment explicitly defines payment delay this way.

Negative values are preserved.

For example:

``` text
-8.16 days
```

means payment happened 8.16 days earlier than the contractual due date
on average.

------------------------------------------------------------------------

## 10. Source-Row Traceability

### Decision

Include original source rows in answers.

### Why

A financial assistant should allow the user to trace an answer back to
the ledger.

This makes the system easier to audit and debug.

------------------------------------------------------------------------

## 11. Unsupported Questions

### Decision

Reject unsupported questions instead of guessing.

Example:

``` text
question
```

returns:

``` text
Sorry, I could not understand the question or it is not currently supported.
```

### Why

For financial data, a safe failure is better than an invented answer.

------------------------------------------------------------------------

## 12. Keep the Project Simple

### Decision

Use a CLI instead of adding a web frontend, API server, database, or
unnecessary infrastructure.

### Why

The assignment specifically asks for a simple local CLI application.

A smaller architecture is easier to understand, test, run, and audit.
