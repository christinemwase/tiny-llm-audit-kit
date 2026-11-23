#!/bin/bash
# Tiny LLM Audit Kit - run all evals, save all replies.
# Requires Ollama running locally with the models already pulled.
# See README.md.
# WARNING: run_evals.py overwrites results/results.jsonl. 
set -e
cd "$(dirname "$0")"
python3 run_evals.py
