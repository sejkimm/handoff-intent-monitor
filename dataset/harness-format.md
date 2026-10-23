# Harness format: Claude Code subagent transcripts

The dataset and every run follow the transcript format that Claude Code writes for a subagent. This file describes only the subset the detector reads. It was taken from real subagent transcripts on 2026-10-23; harness-internal record types are listed at the end and are not used.

## 1. Where a handoff starts and ends

| Side | Record | What it holds |
|---|---|---|
| Delegator (parent session) | assistant `tool_use` with `name: "Agent"` | `input: {description, subagent_type, model, prompt}`. `prompt` is the delegation message. |
| Delegatee (subagent file) | first `user` record, `parentUuid: null` | `message.content` is the same `prompt` as a string. |
| Delegatee | last assistant `text` | The return to the delegator. It is the only channel back. |
| Delegator | user `tool_result` for that `tool_use_id` | Carries the return text into the parent. |

A Claude Code subagent has no tool for asking the delegator while it runs. Asking means ending with a return that contains the question. Report section 4.3 lists this as a limitation.

## 2. Records in a subagent file

One JSON object per line. Every record carries `uuid`, `parentUuid`, `isSidechain: true`, `agentId`, `sessionId`, `timestamp`, `type`, and `message`.

| `type` | `message.role` | `message.content` |
|---|---|---|
| `user` (first line) | `user` | string: the delegation message |
| `assistant` | `assistant` | list of blocks: `text`, `tool_use {id, name, input}`, `thinking` |
| `user` | `user` | list of `tool_result {tool_use_id, content}` blocks |

```json
{"type": "user", "uuid": "u1", "parentUuid": null, "isSidechain": true, "agentId": "a1", "sessionId": "s1", "timestamp": "2026-10-23T12:00:00Z", "message": {"role": "user", "content": "Answer the customer's inquiry..."}}
{"type": "assistant", "uuid": "u2", "parentUuid": "u1", "isSidechain": true, "agentId": "a1", "sessionId": "s1", "timestamp": "2026-10-23T12:00:02Z", "message": {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "mcp__mail__read_inbox", "input": {}}]}}
{"type": "user", "uuid": "u3", "parentUuid": "u2", "isSidechain": true, "agentId": "a1", "sessionId": "s1", "timestamp": "2026-10-23T12:00:03Z", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": [{"type": "text", "text": "..."}]}]}}
```

## 3. What the detector reads

| Report term | Record |
|---|---|
| delegation message | first `user` record |
| tool call | assistant `tool_use` block |
| tool result, incoming message | user `tool_result` block. A new customer mail arrives here, as a result of `mcp__mail__read_inbox`. |
| message to the delegator | final assistant `text` (the return) |
| reasoning | assistant `thinking` block. The detector drops it. |
| commit | `tool_use` of a tool with an outside effect (`mcp__mail__send`), or the return |

Tools in this dataset are MCP tools, named the way Claude Code names them: `mcp__<server>__<tool>`. Their definitions are in `tools.json`.

## 4. Not used

`attachment`, `api-request`, `api-request-shape`, `api-request-blob`, and the side files `agent-*.meta.json` and `agent-*.prefix.json` are harness internals. The detector does not read them, because another harness would not write them.
