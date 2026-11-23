#!/usr/bin/env python3
"""Tiny LLM Audit Kit — run all evals on all models, save raw outputs.

Uses the local Ollama API (http://localhost:11434). Temperature 0, one
generation per prompt, no retries, no cherry-picking. This script only 
runs prompts and records replies. It does not score.
"""
import json
import os
import urllib.request

MODELS = ["smollm2:360m", "qwen2.5:0.5b", "qwen3:0.6b", "llama3.2:1b", "gemma3:1b", "tinyllama:1.1b", "qwen2.5:1.5b"]
EVALS = ["sandbagging", "sycophancy", "refusal"]
OLLAMA_URL = "http://localhost:11434/api/generate"

def ask(model, prompt):
    data = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "seed": 42, "num_predict": 150},
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["response"].strip()

def main():
    os.makedirs("results", exist_ok=True)
    out_path = "results/results.jsonl"
    n = 0
    with open(out_path, "w") as out:
        for eval_name in EVALS:
            with open(f"evals/{eval_name}.json") as f:
                items = json.load(f)
            for item in items:
                for model in MODELS:
                    prompt = item["prompt"]
                    try:
                        reply = ask(model, prompt)
                    except Exception as e:
                        reply = f"[ERROR: {e}]"
                    rec = {
                        "model": model,
                        "eval": eval_name,
                        "id": item["id"],
                        "condition": item.get("condition", ""),
                        "prompt": prompt,
                        "response": reply,
                    }
                    out.write(json.dumps(rec) + "\n")
                    n += 1
                    print(f"{eval_name} {item['id']} {model}: {reply[:80]}")
    print(f"\nDone. {n} runs saved to {out_path}")

if __name__ == "__main__":
    main()
