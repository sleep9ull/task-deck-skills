# TaskDeck Skills

[![English](https://img.shields.io/badge/English-selected-2563eb?style=for-the-badge)](README.md) [![简体中文](https://img.shields.io/badge/简体中文-切换语言-64748b?style=for-the-badge)](README.zh-CN.md)

An agent skill for running long tasks in the background with a live HTML progress dashboard. Invoke `$task-deck-skills` to plan batches, save checkpoints, track results, and keep progress visible from the start.

Use it for batch processing, data collection, migrations, generation, and analysis. The repository includes the [skill instructions](SKILL.md), an offline HTML template, and a renderer built with the Python standard library. Your agent creates or reuses the worker needed for each task.

## Installing TaskDeck

Clone this repository into a supported skills directory, or link an existing checkout. For local Codex, run the following from the repository root, provided the destination does not already exist:

```bash
mkdir -p "$HOME/.codex/skills"
ln -s "$PWD" "$HOME/.codex/skills/task-deck-skills"
```

Keep the checkout in place while using this symbolic link. Rendering the dashboard requires Python 3; no third-party Python packages or web server are needed.

## Using TaskDeck

Explicitly invoke the skill in Codex with `$task-deck-skills` and describe the task, constraints, and expected output:

```text
Use $task-deck-skills to convert files in batches by directory,
with concurrency 3, preserving the originals. Run in the background
and give me an HTML progress dashboard when the task starts.
```

The skill is configured for explicit invocation. It does not automatically take over a request just because the work may take a long time.

## What TaskDeck Does

- Plans batches with stable IDs, a defined scope, and acceptance criteria.
- Creates the dashboard before work begins, then updates it from saved state.
- Guides resumable background execution with checkpoints, logs, and process verification.
- Tracks successful, failed, and review-needed items, with searchable batches and result links.
- Verifies outputs and preserves a final snapshot with results and unresolved issues.

The dashboard is a view of recorded state. Its renderer does not run workers or collect their status; those processes must run independently in the background.

## Previewing the Dashboard

From the repository root, generate a standalone HTML preview:

```bash
python3 scripts/render_dashboard.py --demo --output /tmp/task-deck-demo/index.html
```

Open `/tmp/task-deck-demo/index.html` in your browser. The page is marked as demo data and does not start a task.

For a real run, render an existing status file and refresh the HTML every five seconds:

```bash
python3 scripts/render_dashboard.py \
  --state /path/to/run/status.json --output /path/to/run/index.html --watch 5
```

Replace the example paths with your run directory. Open the generated HTML directly in a browser; it works offline without a development server or CDN.

## Reference

- [Skill instructions](SKILL.md): planning, execution, supervision, and delivery.
- [Status contract](references/status-contract.md): state format, progress counts, and optional AI token and cost estimates.
- [Background execution and recovery](references/execution.md): workers, checkpoints, and resuming runs.
- [Interface guidelines](references/interface.md): dashboard layout and truthful status presentation.

The skill and reference documents are currently written in Chinese.
