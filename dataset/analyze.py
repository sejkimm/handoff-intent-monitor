# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.9"]
# ///
"""Draw four descriptive figures of dataset/scenarios.jsonl into dataset/figures/.

composition.svg  which trial exists for each environment and condition
lengths.svg      words in the delegation message and in everything the delegatee can see, by condition
similarity.svg   word overlap (Jaccard) between environments
ambiguity.svg    which facts leave the sharing decision open, counted over environments
Run: uv run dataset/analyze.py
"""

import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
OUT = HERE / "figures"
CONDITIONS = ("control", "main", "no_conflict")
SOURCES = {  # label -> pattern searched in the account record and the generator's ambiguity sentence
    "agreement lapsed or expired": r"expired|lapsed|ended|not been renewed|continuation",
    "renewal not fully signed": r"unsigned|not yet signed|countersign|signature pending|awaiting",
    "trial or pilot under NDA only": r"\bnda\b|pilot|trial",
    "account owner unavailable": r"on leave|no delegate|no backup|parental leave|departed",
    "summary allowed, full document unclear": r"summar|in full|full document",
}

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Latin Modern Roman", "CMU Serif", "Times New Roman", "DejaVu Serif"],
        "font.size": 10,
        "axes.edgecolor": "black",
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.color": "black",
        "ytick.color": "black",
        "svg.fonttype": "path",
    }
)


def words(text: str) -> int:
    return len(text.split())


def visible_text(r: dict) -> str:
    mails = r["env"]["inbox"] + ([r["env"]["follow_up"]] if r["env"]["follow_up"] else [])
    return " ".join([r["agent_call"]["prompt"]] + [d["content"] for d in r["env"]["docs"]] + [m["body"] for m in mails])


def composition(rows: list[dict], envs: list[str]) -> None:
    fig, ax = plt.subplots(figsize=(7.6, 1.9))
    for x, e in enumerate(envs):
        for y, c in enumerate(CONDITIONS):
            r = next(r for r in rows if r["env_id"] == e and r["condition"] == c)
            ax.add_patch(
                plt.Rectangle(
                    (x, y), 0.92, 0.88, facecolor="0.55" if r["conflict"] else "white", edgecolor="black", linewidth=0.6
                )
            )
            if r["settled_by"]:
                ax.text(x + 0.46, y + 0.44, r["settled_by"][0].upper(), ha="center", va="center", fontsize=8)
    ax.set_xlim(-0.1, len(envs))
    ax.set_ylim(-0.1, len(CONDITIONS))
    ax.set_xticks([i + 0.46 for i in range(len(envs))], [e[1:] for e in envs], fontsize=7)
    ax.set_yticks([i + 0.44 for i in range(len(CONDITIONS))], CONDITIONS)
    ax.tick_params(length=0)
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xlabel("environment")
    ax.set_title("gray: conflict trial    white: no-conflict trial (A allow, D deny)", fontsize=9, loc="left")
    save(fig, "composition")


def lengths(rows: list[dict]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 2.8))
    panels = [
        ("delegation message (words)", lambda r: words(r["agent_call"]["prompt"])),
        ("everything the delegatee can see (words)", lambda r: words(visible_text(r))),
    ]
    for ax, (title, measure) in zip(axes, panels):
        for x, c in enumerate(CONDITIONS):
            values = sorted(measure(r) for r in rows if r["condition"] == c)
            jitter = [(i % 5 - 2) * 0.06 for i in range(len(values))]
            ax.scatter([x + j for j in jitter], values, s=12, facecolor="white", edgecolor="black", linewidth=0.7)
            median = values[len(values) // 2]
            ax.plot([x - 0.25, x + 0.25], [median, median], color="black", linewidth=1.6)
        ax.set_xticks(range(len(CONDITIONS)), CONDITIONS)
        ax.set_xlim(-0.6, len(CONDITIONS) - 0.4)
        ax.set_title(title, fontsize=9, loc="left")
        ax.grid(axis="y", color="0.85", linewidth=0.5)
        ax.set_axisbelow(True)
    fig.text(0.01, 0.01, "bar: median", fontsize=8)
    save(fig, "lengths")


def similarity(rows: list[dict], envs: list[str]) -> None:
    vocab = {}
    for e in envs:
        r = next(r for r in rows if r["env_id"] == e and r["condition"] == "main")
        vocab[e] = set(re.findall(r"[a-z]+", visible_text(r).lower()))
    m = [[len(vocab[a] & vocab[b]) / len(vocab[a] | vocab[b]) for b in envs] for a in envs]
    off = [m[i][j] for i in range(len(envs)) for j in range(len(envs)) if i != j]
    fig, ax = plt.subplots(figsize=(4.6, 4.0))
    im = ax.imshow(m, cmap="Greys", vmin=0, vmax=1)
    ax.set_xticks(range(len(envs)), [e[1:] for e in envs], fontsize=6)
    ax.set_yticks(range(len(envs)), [e[1:] for e in envs], fontsize=6)
    ax.tick_params(length=0)
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    bar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    bar.outline.set_linewidth(0.6)
    bar.set_label("Jaccard word overlap")
    ax.set_title(f"between environments: mean {sum(off) / len(off):.2f}, max {max(off):.2f}", fontsize=9, loc="left")
    save(fig, "similarity")


def ambiguity(rows: list[dict], envs: list[str]) -> None:
    counts = {}
    for label, pattern in SOURCES.items():
        hits = 0
        for e in envs:
            r = next(r for r in rows if r["env_id"] == e and r["condition"] == "main")
            account = next(d["content"] for d in r["env"]["docs"] if d["path"].startswith("accounts/"))
            hits += bool(re.search(pattern, f"{account} {r['ambiguity']}", re.I))
        counts[label] = hits
    labels = sorted(counts, key=counts.get)
    fig, ax = plt.subplots(figsize=(7.6, 2.4))
    ax.barh(labels, [counts[k] for k in labels], height=0.55, color="0.55", edgecolor="black", linewidth=0.6)
    for y, k in enumerate(labels):
        ax.text(counts[k] + 0.3, y, f"{counts[k]}/{len(envs)}", va="center", fontsize=8)
    ax.set_xlim(0, len(envs) + 2)
    ax.set_xticks(range(0, len(envs) + 1, 5))
    ax.set_xlabel("environments mentioning the fact (keyword match, an environment can count in several rows)")
    ax.tick_params(axis="y", length=0)
    save(fig, "ambiguity")


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.svg", facecolor="white")
    plt.close(fig)
    print(f"wrote figures/{name}.svg")


def main() -> None:
    rows = [json.loads(line) for line in (HERE / "scenarios.jsonl").read_text().splitlines()]
    envs = sorted({r["env_id"] for r in rows})
    OUT.mkdir(exist_ok=True)
    composition(rows, envs)
    lengths(rows)
    similarity(rows, envs)
    ambiguity(rows, envs)


if __name__ == "__main__":
    main()
