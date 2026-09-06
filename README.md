# Bridgeline Ledger Assistant

A simple local AI-powered assistant for answering questions about a financial ledger.

The project uses **Ollama for natural-language question understanding** and **Python/Pandas for all financial calculations**. This keeps the financial results deterministic and prevents the LLM from performing arithmetic.

## Features

- Natural-language ledger questions
- Local AI using Ollama
- Deterministic Python/Pandas calculations
- FY 2024-25 filtering
- Vendor payable and spend analysis
- Overdue invoice detection
- Taxable amount filtering
- GST calculation
- ITC exception detection
- Fabrication payment-delay analysis
- Duplicate and data-quality detection
- USD → INR conversion at ₹83.50
- Credit-note handling
- Source-row traceability
- Policy-aware answers

## Architecture

```text
User Question
      ↓
Ollama
(Intent Classification)
      ↓
Python Query Router
      ↓
Python/Pandas Analytics
      ↓
Deterministic Result
      ↓
Answer + Source Rows + Policy