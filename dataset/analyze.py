# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.9"]
# ///
"""Draw four descriptive figures of dataset/scenarios.jsonl into dataset/figures/.

composition.svg  how the three trials are made from one environment
lengths.svg      words in the delegation message and in everything the delegatee can see, by condition
similarity.svg   word overlap (Jaccard) between environments
ambiguity.svg    the reason assigned to each environment, and how often the generator's stated reason names each one
Run: uv run dataset/analyze.py
"""

import json
import re
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
OUT = HERE / "figures"
CONDITIONS = ("self", "request", "settled")
SOURCES = {  # assigned reason -> keywords that name it in the generator's one-sentence reason
    "agreement": r"active agreement|active support agreement|term end|expired|lapsed|renewal",
    "data_scope": r"other (customers|tenants)|third.part|mix",
    "approver": r"approver",
    "classification": r"label|classif|banner|shareable field",
    "purpose": r"purpose|solely|only to (verify|confirm)",
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
    """A construction diagram, drawn by hand in the report's figure style, with counts from the data."""
    settled = [r["settled_by"] for r in rows if r["condition"] == "settled"]
    allow, deny = settled.count("allow"), settled.count("deny")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="760" height="290" viewBox="0 0 760 290" role="img" aria-labelledby="t d" font-family="'Latin Modern Roman','CMU Serif','Times New Roman',Times,serif" font-size="15" fill="#000">
  <title id="t">How are three trials made from one environment?</title>
  <desc id="d">Each of the {len(envs)} environments holds a delegation message, three wiki pages and the customer's first mail. Three trials branch from it. self adds nothing, request adds the follow-up mail asking for the full document, and settled adds the follow-up mail and one settling sentence in the delegation message, which allows sending in {allow} environments and forbids it in {deny}. self and request are conflict trials; settled is a no-conflict trial.</desc>
  <defs><marker id="ar" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 1L10 5L0 9z" fill="#000"/></marker></defs>
  <rect width="760" height="290" fill="#fff"/>
  <g fill="none" stroke="#000" stroke-width="1">
    <rect x="20" y="85" width="220" height="120"/>
    <rect x="330" y="20" width="290" height="64"/>
    <rect x="330" y="113" width="290" height="64"/>
    <rect x="330" y="206" width="290" height="64"/>
    <path d="M240 145 H290"/>
    <path d="M290 52 V238"/>
  </g>
  <g fill="none" stroke="#000" stroke-width="1" marker-end="url(#ar)">
    <path d="M290 52 H330"/>
    <path d="M290 145 H330"/>
    <path d="M290 238 H330"/>
  </g>
  <circle cx="290" cy="145" r="2.5" fill="#000"/>
  <g text-anchor="middle">
    <text x="130" y="110">Environment</text>
    <text x="130" y="128" font-size="12" font-style="italic">\u00d7 {len(envs)}</text>
    <text x="475" y="45">self</text>
    <text x="475" y="138">request</text>
    <text x="475" y="231">settled</text>
  </g>
  <g text-anchor="middle" font-size="12">
    <text x="130" y="152">delegation message</text>
    <text x="130" y="169">3 wiki pages</text>
    <text x="130" y="186">customer's first mail</text>
    <text x="475" y="64">+ nothing</text>
    <text x="475" y="157">+ follow-up mail asking for the full document</text>
    <text x="475" y="250">+ follow-up mail</text>
    <text x="475" y="265">+ settling sentence: allow {allow}, deny {deny}</text>
  </g>
  <g font-size="13" font-style="italic">
    <text x="636" y="57">conflict</text>
    <text x="636" y="150">conflict</text>
    <text x="636" y="243">no conflict</text>
  </g>
</svg>
"""
    (OUT / "composition.svg").write_text(svg.replace("\\u00d7", "\u00d7"))
    print("wrote figures/composition.svg")


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
            median = statistics.median(values)
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
        r = next(r for r in rows if r["env_id"] == e and r["condition"] == "request")
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
    mains = [next(r for r in rows if r["env_id"] == e and r["condition"] == "request") for e in envs]
    labels = list(SOURCES)
    assigned = [sum(r["ambiguity_source"] == k for r in mains) for k in labels]
    named = [sum(bool(re.search(SOURCES[k], r["ambiguity"], re.I)) for r in mains) for k in labels]
    fig, ax = plt.subplots(figsize=(7.6, 2.6))
    ys = range(len(labels))
    ax.barh([y + 0.18 for y in ys], assigned, height=0.34, color="0.55", edgecolor="black", linewidth=0.6, label="assigned")
    ax.barh([y - 0.18 for y in ys], named, height=0.34, color="white", edgecolor="black", linewidth=0.6, label="named in the stated reason")
    for y, (a, n) in enumerate(zip(assigned, named)):
        ax.text(a + 0.15, y + 0.18, str(a), va="center", fontsize=8)
        ax.text(n + 0.15, y - 0.18, str(n), va="center", fontsize=8)
    ax.set_yticks(list(ys), labels)
    ax.invert_yaxis()
    ax.set_xlim(0, max(assigned + named) + 2)
    ax.set_xticks(range(0, max(assigned + named) + 2, 2))
    ax.set_xlabel("environments")
    ax.tick_params(axis="y", length=0)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
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
