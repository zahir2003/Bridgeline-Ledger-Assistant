"""Benchmark local Ollama models for the Bridgeline assignment."""

import time
import subprocess

import ollama

OLLAMA_HOST = "http://127.0.0.1:11434"

MODELS = [
    "llama3:latest",
    "llama3.2:3b",
]

PROMPT = """
You are a concise financial assistant.

Explain in 3 short sentences why deterministic Python calculations
are safer than asking an LLM to calculate financial ledger totals.
"""


def get_ollama_memory_usage_mb():
    """
    Read memory usage of running Ollama-related processes on Windows.

    This is an approximate process-memory measurement.
    """

    command = [
        "powershell",
        "-Command",
        (
            "Get-Process ollama* -ErrorAction SilentlyContinue | "
            "Measure-Object WorkingSet64 -Sum | "
            "Select-Object -ExpandProperty Sum"
        ),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    output = result.stdout.strip()

    if not output:
        return None

    try:
        memory_bytes = int(output)
        return memory_bytes / (1024 * 1024)
    except ValueError:
        return None


def benchmark_model(client, model_name):
    """Run one benchmark for a model."""

    print()
    print("=" * 60)
    print(f"Benchmarking: {model_name}")
    print("=" * 60)

    # -----------------------------------------------------
    # STEP 1:
    # Load the model with a very small request.
    #
    # This reduces the effect of model-loading time on the
    # actual generation benchmark.
    # -----------------------------------------------------
    client.chat(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": "Reply with only: ready",
            }
        ],
        keep_alive="5m",
    )

    # -----------------------------------------------------
    # STEP 2:
    # Measure Ollama process memory after the model is loaded.
    # -----------------------------------------------------
    memory_mb = get_ollama_memory_usage_mb()

    # -----------------------------------------------------
    # STEP 3:
    # Run the real benchmark and record wall-clock time.
    # -----------------------------------------------------
    start_time = time.perf_counter()

    response = client.chat(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": PROMPT,
            }
        ],
        keep_alive="5m",
    )

    elapsed_seconds = time.perf_counter() - start_time

    # -----------------------------------------------------
    # STEP 4:
    # Ollama returns eval_count and eval_duration.
    #
    # eval_count:
    #     number of generated tokens
    #
    # eval_duration:
    #     model generation time in nanoseconds
    #
    # These values let us calculate tokens per second.
    # -----------------------------------------------------
    eval_count = getattr(response, "eval_count", None)
    eval_duration = getattr(response, "eval_duration", None)

    tokens_per_second = None

    if eval_count and eval_duration:
        eval_seconds = eval_duration / 1_000_000_000

        if eval_seconds > 0:
            tokens_per_second = eval_count / eval_seconds

    # -----------------------------------------------------
    # STEP 5:
    # Print benchmark results.
    # -----------------------------------------------------
    print(f"Model: {model_name}")

    if memory_mb is not None:
        print(f"Approx. Ollama RAM usage: {memory_mb:.2f} MB")
    else:
        print("Approx. Ollama RAM usage: unavailable")

    print(f"Wall-clock response time: {elapsed_seconds:.2f} seconds")

    if eval_count is not None:
        print(f"Generated tokens: {eval_count}")

    if tokens_per_second is not None:
        print(f"Generation speed: {tokens_per_second:.2f} tokens/sec")
    else:
        print("Generation speed: unavailable")

    print()
    print("Response:")
    print(response["message"]["content"])

    return {
        "model": model_name,
        "memory_mb": memory_mb,
        "response_time_seconds": elapsed_seconds,
        "generated_tokens": eval_count,
        "tokens_per_second": tokens_per_second,
    }


def main():
    """Benchmark all configured models."""

    client = ollama.Client(host=OLLAMA_HOST)

    results = []

    for model_name in MODELS:
        result = benchmark_model(
            client,
            model_name,
        )

        results.append(result)

    # -----------------------------------------------------
    # STEP 6:
    # Print a compact comparison summary.
    # -----------------------------------------------------
    print()
    print("=" * 60)
    print("MODEL COMPARISON")
    print("=" * 60)

    for result in results:
        print()
        print(f"Model: {result['model']}")

        if result["memory_mb"] is not None:
            print(f"RAM: " f"{result['memory_mb']:.2f} MB")

        print(f"Response time: " f"{result['response_time_seconds']:.2f} sec")

        if result["tokens_per_second"] is not None:
            print(f"Speed: " f"{result['tokens_per_second']:.2f} tok/s")


if __name__ == "__main__":
    main()
