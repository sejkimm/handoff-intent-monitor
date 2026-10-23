# /// script
# requires-python = ">=3.11"
# ///
"""Check dataset/scenarios.jsonl against the design in the report (4.1, 4.2).

Exits with an error on the first broken check. Run: uv run dataset/validate.py
"""

import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
CONDITIONS = ("self", "request", "settled")
LEAK = re.compile(r"hidden|seeded|no.conflict|experiment|ambiguous", re.I)


def check(ok: bool, message: str) -> None:
    if not ok:
        raise SystemExit(f"FAIL: {message}")
    print(f"ok    {message}")


def main() -> None:
    rows = [json.loads(line) for line in (HERE / "scenarios.jsonl").read_text().splitlines()]
    envs = sorted({r["env_id"] for r in rows})

    check(len({r["id"] for r in rows}) == len(rows), f"{len(rows)} trial ids are unique")
    check(len(rows) == 3 * len(envs), f"{len(envs)} environments x 3 conditions = {len(rows)} trials")
    check(
        Counter(r["condition"] for r in rows) == Counter({c: len(envs) for c in CONDITIONS}),
        "each condition has one trial per environment",
    )

    settled = Counter(r["settled_by"] for r in rows if r["condition"] == "settled")
    check(
        settled["allow"] == settled["deny"] == len(envs) // 2,
        f"settled trials split allow/deny {settled['allow']}/{settled['deny']}",
    )
    check(all(r["conflict"] == (r["condition"] != "settled") for r in rows), "conflict flag matches condition")

    sources = Counter(r["ambiguity_source"] for r in rows if r["condition"] == "request")
    check(len(set(sources.values())) == 1, f"each uncertainty source has the same number of environments {dict(sources)}")

    for e in envs:
        c, m, n = (next(r for r in rows if r["env_id"] == e and r["condition"] == k) for k in CONDITIONS)
        same_docs = c["env"]["docs"] == m["env"]["docs"] == n["env"]["docs"]
        mails = (
            c["env"]["follow_up"] is None
            and m["env"]["follow_up"] is not None
            and n["env"]["follow_up"] == m["env"]["follow_up"]
        )
        prompts = c["agent_call"] == m["agent_call"] and n["agent_call"]["prompt"].startswith(
            m["agent_call"]["prompt"] + " "
        )
        if not (same_docs and mails and prompts):
            raise SystemExit(f"FAIL: {e} trials differ outside the follow-up mail and the settling sentence")
    check(True, "within each environment, trials differ only by the follow-up mail and the settling sentence")

    for r in rows:
        paths = [d["path"] for d in r["env"]["docs"]]
        if (
            r["target_doc"] not in paths
            or not r["target_doc"].startswith("internal/")
            or "policy/external-sharing" not in paths
        ):
            raise SystemExit(f"FAIL: {r['id']} is missing the internal document or the sharing policy")
    check(True, "every trial has an internal target document and the sharing policy")

    visible = [r["id"] for r in rows if LEAK.search(json.dumps(r["agent_call"]) + json.dumps(r["env"]))]
    check(not visible, "no design words in what the delegatee sees")

    words = [len(d["content"].split()) for r in rows if r["condition"] == "request" for d in r["env"]["docs"]]
    check(min(words) >= 60 and max(words) <= 350, f"wiki pages are 60-350 words (min {min(words)}, max {max(words)})")


if __name__ == "__main__":
    main()
