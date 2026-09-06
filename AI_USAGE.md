# AI Usage

## Overview

AI was used as a development assistant during the implementation of the
**Bridgeline Ledger Assistant**.

The main goal was to use AI for **development support and reasoning**,
while keeping the actual financial calculations deterministic and local.

### AI tools used

-   **ChatGPT** --- used for development guidance, debugging help, code
    review, documentation, test ideas, and explaining technical
    concepts.
-   **Ollama** --- used inside the application for local
    natural-language intent classification.
-   **Llama 3 / Llama 3.2 3B** --- tested as local Ollama models.

No paid cloud AI API is required by the application.

------------------------------------------------------------------------

## How ChatGPT Was Used

ChatGPT was mainly used for:

1.  **Project planning**
    -   Breaking the assignment into smaller tasks.
    -   Planning the CLI architecture.
    -   Choosing a simple hybrid AI + deterministic design.
2.  **Python development**
    -   Getting help with Python implementation ideas.
    -   Reviewing code structure.
    -   Finding and fixing bugs.
    -   Improving error handling and CLI behavior.
3.  **Data handling**
    -   Reasoning about messy ledger values.
    -   Designing cleaning and normalization rules.
    -   Checking duplicate-invoice handling.
    -   Designing GST and data-quality checks.
4.  **Testing and debugging**
    -   Creating test cases.
    -   Interpreting test failures.
    -   Checking CLI outputs.
    -   Improving unsupported-question handling.
5.  **Documentation**
    -   Structuring the README.
    -   Explaining design decisions.
    -   Preparing model evaluation notes.
    -   Improving the clarity of project documentation.
6.  **Model research**
    -   Understanding Ollama models.
    -   Understanding parameter size and quantisation.
    -   Comparing the local models used in the project.

ChatGPT did **not** act as the source of financial truth. The ledger and
the provided payment policy remained the source of truth.

------------------------------------------------------------------------

## How Ollama Was Used

Ollama is used locally by the application.

The LLM has a limited responsibility:

``` text
User's plain-English question
            ↓
      Local Ollama model
            ↓
       Intent / query type
            ↓
     Python analytics
```

For example:

``` text
"Which vendor has the highest spend?"
```

is classified as:

``` text
highest_spend_vendor
```

Python then performs the actual vendor aggregation.

------------------------------------------------------------------------

## What the LLM Does NOT Do

The LLM is not trusted to:

-   Calculate financial totals.
-   Calculate GST.
-   Decide overdue status.
-   Calculate payment delays.
-   Convert USD to INR.
-   Determine duplicate rows.
-   Produce financial facts independently.

These operations are performed by deterministic Python code.

This was an intentional design choice because financial calculations
should be reproducible and easy to verify.

------------------------------------------------------------------------

## Data Privacy

The project was designed around the assignment requirement that ledger
data should remain on the local machine.

The application uses:

-   Local CSV files.
-   Local Python processing.
-   Local Pandas calculations.
-   Local Ollama inference.

No paid cloud AI service is required to process the ledger.

------------------------------------------------------------------------

## Important Principle

The project follows this principle:

> **Use AI to understand language, but use deterministic code to
> calculate financial answers.**

This gives the project the convenience of natural-language questions
without giving the LLM control over financial arithmetic.

------------------------------------------------------------------------

## AI Assistance Disclosure

AI assistance was used throughout development, but the final
implementation, testing, debugging, evaluation, and project decisions
were reviewed against the assignment requirements.

The final application was tested locally using the actual ledger and
policy files.
