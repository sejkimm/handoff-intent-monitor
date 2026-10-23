# Detecting Subagents That Silently Resolve Conflicts with Delegator Intent at Handoff

- Created: 2026.10.23
- Author: SeungJong Kim

## Abstract

A subagent often settles a conflict between a new criterion and the delegator's intent on its own and reports only that the work is done. We propose a monitor that reads the handoff transcript at every commit and asks the delegator only when a choice the delegation message left open was made without being put to the delegator, and we evaluate it on a dataset with a seeded conflict in every trial.

## dataset

### Contents

60 trials from 20 customer-support environments, each seeded with one conflict: whether an internal document may be sent to an external customer. The folder holds the generation prompt and script, the trials (`scenarios.jsonl`), the Claude Code transcript format, a validation script, and figures; see [`dataset/README.md`](dataset/README.md).

### Limitations

One LLM wrote every environment in one domain, and whether each environment is truly undecidable was checked only by keyword match, not by a reader. The `settled` delegation messages are longer by one sentence, which a detector could use as a cue.

## detector

TBD - a minimal monitor (commit detection, gate, judgment) over Claude Code transcripts, and a runner that executes a delegatee on the 60 trials.

## result

TBD - replay of the monitor over the run transcripts, the scores of report section 4.1 (`F`, `h`, `R`, `ΔL`, `W`), and their figures.
