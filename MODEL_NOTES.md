# Model Notes

## Local AI Models Tested

Two Ollama models were tested for this project:

1.  `llama3:latest`
2.  `llama3.2:3b`

The application uses:

``` text
llama3.2:3b
```

by default.

------------------------------------------------------------------------

## Machine Used

The tests were performed on:

``` text
Device: ASUSTeK Vivobook M6500QF
CPU: AMD Ryzen 5 5600H
CPU: 6 cores / 12 threads
RAM: 15.40 GB
GPU: NVIDIA RTX 2050, approximately 4 GB
Integrated GPU: AMD Radeon
```

The exact available memory can vary slightly depending on
operating-system usage.

------------------------------------------------------------------------

## Model Comparison

  ------------------------------------------------------------------------------
  Model              Approx. Size      Parameters Quantisation    Observed Speed
  --------------- --------------- --------------- -------------- ---------------
  llama3:latest            4.7 GB    Larger model Local Ollama     \~10.71 tok/s
                                                  build          

  llama3.2:3b              2.0 GB            3.2B Q4_K_M           \~41.11 tok/s
  ------------------------------------------------------------------------------

The benchmark was performed locally with a small test prompt.

Observed results:

``` text
llama3
- Approx. wall-clock time: 7.27 seconds
- Approx. generation speed: 10.71 tokens/sec

llama3.2:3b
- Approx. wall-clock time: 1.66 seconds
- Approx. generation speed: 41.11 tokens/sec
```

These are local observations, not universal performance numbers.

------------------------------------------------------------------------

## Quantisation

Quantisation reduces the number of bits used to represent model weights.

A quantised model is generally:

-   Smaller.
-   Faster to load.
-   Less demanding on memory.
-   Suitable for running on consumer hardware.

The selected `llama3.2:3b` model uses:

``` text
Q4_K_M
```

which is a 4-bit-style quantised representation.

------------------------------------------------------------------------

## Why a 3B Model Can Run Locally

A 3B model has approximately 3 billion parameters.

Using quantisation reduces the memory required to store those parameters
compared with a full-precision model.

The machine used for this project has around 15.40 GB system RAM, so a
small quantised 3B model is practical for local inference.

The application also gives the model a small task: intent classification
and language understanding.

It does not send the whole ledger to the model.

------------------------------------------------------------------------

## Why `llama3.2:3b` Was Selected

The main reason is the architecture of this project.

The LLM is not responsible for:

-   Financial arithmetic.
-   GST calculations.
-   Vendor aggregation.
-   Overdue calculations.
-   Payment-delay calculations.

Python handles those operations.

Therefore, a smaller and faster model is sufficient for the
natural-language understanding part.

### Selected model

``` text
llama3.2:3b
```

### Main trade-off

**Advantages**

-   Smaller.
-   Faster on the test machine.
-   Lower local resource requirements.
-   Good fit for simple intent classification.

**Trade-off**

A larger model may handle more complex or ambiguous natural-language
questions better, but it is slower and requires more resources.

For this assignment, the faster 3B model provides a better practical
trade-off.

------------------------------------------------------------------------

## Memory Measurement Note

The benchmark also recorded the Ollama process working-set memory.

Approximate observations:

``` text
llama3:latest       ~119 MB
llama3.2:3b         ~125 MB
```

These values represent the observed Ollama process working set during
the benchmark, **not the complete model-only memory requirement**.

Model memory can vary depending on:

-   Operating system state.
-   GPU/CPU offloading.
-   Context size.
-   Loaded model state.
-   Ollama runtime behavior.

Therefore, these measurements are reported as observations rather than
exact model-memory specifications.

------------------------------------------------------------------------

## Recommendation

For this project:

> **Use `llama3.2:3b`.**

The financial logic is deterministic, so the main requirement for the
LLM is reliable question understanding. The 3B model is substantially
faster in the local benchmark while being smaller than the larger Llama
3 model.

If the project later needs more complex natural-language reasoning, a
larger model could be evaluated again.
