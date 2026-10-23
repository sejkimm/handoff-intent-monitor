from pathlib import Path

from monitor import checked, events, is_commit, monitor

FIXTURE = Path(__file__).parent / "fixtures" / "e00-request.jsonl"


def test_commits_are_effectful_tool_calls_and_the_return():
    kinds = [(r["kind"], r["name"]) for r in monitor(FIXTURE, dry_run=True)]
    assert kinds == [("tool_call", "mcp__mail__send"), ("tool_call", "mcp__mail__send"), ("to_delegator", None)]


def test_unknown_tool_counts_as_a_commit():
    assert is_commit({"kind": "tool_call", "name": "mcp__crm__update"})
    assert not is_commit({"kind": "tool_call", "name": "mcp__wiki__read"})


def test_segment_of_the_target_commit_holds_the_follow_up_and_the_attachment():
    segment = monitor(FIXTURE, dry_run=True)[1]["judgment_prompt"].split("[Commit segment]")[1]
    assert segment.startswith(" [tool_result] sent\n[tool_call mcp__mail__read_inbox]")
    assert '"attachments"' in segment


def test_quote_not_in_the_delegation_message_turns_conflict_off():
    record = {"conflict": "yes", "quote": "Never share anything.", "told": "no"}
    assert checked(record, "Follow the sharing policy.", ["x"])["conflict"] == "no"


def test_nothing_sent_means_not_told():
    record = {"conflict": "yes", "quote": "Follow the sharing policy.", "told": "yes"}
    assert checked(record, "Follow the sharing policy.", [])["told"] == "no"


def test_transcript_must_start_with_the_delegation_message(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}}\n')
    try:
        events(bad)
    except ValueError:
        return
    raise AssertionError("expected ValueError")
