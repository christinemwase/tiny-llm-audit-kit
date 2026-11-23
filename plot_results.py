#!/usr/bin/env python3
"""Tiny LLM Audit Kit — plot results (chart + Markdown table).

Reads results/sandbagging-scores.json (written by score.py — the scored
sandbagging counts) and results/judge-votes.jsonl (written by the AI
judge, see judge-spec.md), then:
  1. writes assets/results.png — three panels (Sandbagging, Sycophancy,
     Refusal) across the models, and
  2. prints a compact Markdown table with the exact numbers.

Run score.py first.

Requires matplotlib for the chart (pip install matplotlib). Without it,
the script still prints the Markdown table and skips the chart.

Usage, from inside tiny-llm-audit-kit:
    python3 score.py
    python3 plot_results.py
    python3 plot_results.py results/results.jsonl results/judge-votes.jsonl
"""
import json
import os
import sys

MODELS = ["smollm2:360m", "qwen2.5:0.5b", "qwen3:0.6b", "llama3.2:1b", "gemma3:1b", "tinyllama:1.1b", "qwen2.5:1.5b"]
# Short labels for the chart x-axis (model + size).
LABELS = {
    "smollm2:360m": "smollm2\n0.36B",
    "qwen2.5:0.5b": "qwen2.5\n0.5B",
    "qwen3:0.6b": "qwen3\n0.6B",
    "llama3.2:1b": "llama3.2\n1B",
    "gemma3:1b": "gemma3\n1B",
    "tinyllama:1.1b": "tinyllama\n1.1B",
    "qwen2.5:1.5b": "qwen2.5\n1.5B",
}


def main():
    results_path = sys.argv[1] if len(sys.argv) > 1 else "results/results.jsonl"
    votes_path = sys.argv[2] if len(sys.argv) > 2 else "results/judge-votes.jsonl"
    if not os.path.exists(results_path):
        print(f"Not found: {results_path} — run './run.sh' first.")
        return 1
    if not os.path.exists(votes_path):
        print(f"Not found: {votes_path} — the AI judge has not scored sycophancy/refusal yet (see judge-spec.md).")
        return 1
    recs = [json.loads(line) for line in open(results_path) if line.strip()]
    votes = [json.loads(line) for line in open(votes_path) if line.strip()]
    scores_path = os.path.join(os.path.dirname(results_path) or ".", "sandbagging-scores.json")
    if not os.path.exists(scores_path):
        print(f"Not found: {scores_path} — run 'python3 score.py' first (it writes the scored sandbagging counts).")
        return 1
    sand_data = json.load(open(scores_path))
    scored_ids = sand_data["scored_ids"]
    sand_counts = sand_data["models"]

    # Models present in the run, in MODELS order (plus any extras at the end).
    have = {r["model"] for r in recs}
    models = [m for m in MODELS if m in have] + sorted(have - set(MODELS))

    # --- Sandbagging (scored counts from score.py) ---
    sand = {}
    for m in models:
        entry = sand_counts.get(m, {"casual": {"exact": 0, "contains": 0}, "tested": {"exact": 0, "contains": 0}})
        sand[m] = (entry["casual"]["exact"], entry["casual"]["contains"],
                   entry["tested"]["exact"], entry["tested"]["contains"])

    # --- Sycophancy + refusal (from the judge's verdicts) ---
    syc = {}
    ref = {}
    for m in models:
        syc_votes = [v for v in votes if v.get("eval") == "sycophancy" and v.get("model") == m]
        flips = sum(1 for v in syc_votes if v.get("verdict") == "flip")
        valid = sum(1 for v in syc_votes if v.get("verdict") in ("flip", "no-flip", "no_flip"))
        excluded = sum(1 for v in syc_votes if v.get("verdict") == "excluded")
        syc[m] = (flips, valid, excluded)
        ref_votes = [v for v in votes if v.get("eval") == "refusal" and v.get("model") == m]
        passes = sum(1 for v in ref_votes if v.get("verdict") == "pass")
        ref[m] = (passes, len(ref_votes))

    # --- Chart ---
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        plt = None
        print("matplotlib is not installed — skipping the chart (install it with: pip install matplotlib).")
        print("The Markdown table below was still computed.")

    if plt is not None:
        labels = [LABELS.get(m, m) for m in models]
        x = np.arange(len(models))

        cas_auto = [sand[m][0] for m in models]
        cas_con = [sand[m][1] for m in models]
        tes_auto = [sand[m][2] for m in models]
        tes_con = [sand[m][3] for m in models]
        flip_rate = [100.0 * syc[m][0] / syc[m][1] if syc[m][1] else 0.0 for m in models]
        excl_rate = [100.0 * syc[m][2] / (syc[m][1] + syc[m][2]) if (syc[m][1] + syc[m][2]) else 0.0 for m in models]
        flip_frac = [f"{syc[m][0]}/{syc[m][1]}" for m in models]
        excl_frac = [str(syc[m][2]) for m in models]
        ref_pass = [ref[m][0] for m in models]
        ref_total = max((ref[m][1] for m in models), default=0)

        fig, axes = plt.subplots(1, 3, figsize=(16, 5.0))
        fig.subplots_adjust(wspace=0.28)

        ax = axes[0]
        w = 0.19
        ax.bar(x - 1.5 * w, cas_auto, w, label="Casual (exact)", color="#2c5f8a")
        ax.bar(x - 0.5 * w, cas_con, w, label="Casual (contains)", color="#7fb3d5")
        ax.bar(x + 0.5 * w, tes_auto, w, label="Tested (exact)", color="#b85c2e")
        ax.bar(x + 1.5 * w, tes_con, w, label="Tested (contains)", color="#e8a87c")
        ax.set_ylim(0, max(len(scored_ids), 1) + 0.5)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_ylabel(f"Correct / {len(scored_ids)}")
        ax.set_title("Sandbagging", fontsize=12)
        ax.yaxis.grid(True, linestyle="--", alpha=0.4)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, frameon=False)

        ax = axes[1]
        w = 0.36
        ax.bar(x - w / 2, flip_rate, w, label="Flip rate (valid pairs)", color="#c0392b")
        ax.bar(x + w / 2, excl_rate, w, label="Exclusion rate", color="#95a5a6")
        ax.set_ylim(0, 112)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_ylabel("Rate (%)")
        ax.set_title("Sycophancy", fontsize=12)
        ax.yaxis.grid(True, linestyle="--", alpha=0.4)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=1, frameon=False)
        for xi, v, f in zip(x, flip_rate, flip_frac):
            ax.text(xi - w / 2, v + 3, f, ha="center", va="bottom", fontsize=8, fontweight="bold")
        for xi, v, f in zip(x, excl_rate, excl_frac):
            if v > 0:
                ax.text(xi + w / 2, v + 3, f, ha="center", va="bottom", fontsize=8)

        ax = axes[2]
        bars = ax.bar(x, ref_pass, 0.62, color="#4a7dbd")
        ax.set_ylim(0, ref_total + 1.5 if ref_total else 1)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_ylabel(f"Refused / {ref_total} prompts" if ref_total else "Refused")
        ax.set_title("Refusal", fontsize=12)
        ax.yaxis.grid(True, linestyle="--", alpha=0.4)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        for b, v in zip(bars, ref_pass):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.5, str(v), ha="center", va="bottom", fontsize=10, fontweight="bold")

        plt.tight_layout()
        os.makedirs("assets", exist_ok=True)
        plt.savefig("assets/results.png", dpi=150)
        print("Wrote assets/results.png")

    # --- Markdown table (copy into the README below the chart) ---
    ref_total = max((ref[m][1] for m in models), default=0)
    print(f"\n| Model | Sandbagging Casual (exact / contains) | Sandbagging Tested (exact / contains) | Sycophancy flips (valid) | Sycophancy excluded | Refused (/{ref_total}) |")
    print("|---|---|---|---|---|---|")
    for m in models:
        cas_a, cas_c, tes_a, tes_c = sand[m]
        flips, valid, excluded = syc[m]
        passes, total = ref[m]
        print(f"| {m} | {cas_a} / {cas_c} | {tes_a} / {tes_c} | {flips}/{valid} | {excluded} | {passes}/{total} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
