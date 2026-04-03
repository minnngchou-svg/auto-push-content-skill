# AI Opportunity Watcher

This project monitors AI-related opportunities across multiple communities and sends digest emails with reply commands for saving, scoring, and annotating items.

## Sources

- `linux.do`
- `NodeSeek`
- `V2EX`

## What It Does

- fetches recent posts from all configured sources
- filters for AI freebies, trials, credits, invitation codes, and similar opportunities
- deduplicates across sources before sending
- groups each email by source
- supports email reply commands such as `1 3 5`, `2+`, `3-`, and `4 note: ...`
- saves structured articles into `saved_articles/`

## Main Files

- `linux_do_watcher.py`: main watcher and reply processor
- `config.example.json`: shareable config template
- `config.json`: local config created from the template
- `run_linux_do_watcher.ps1`: launcher used by the watcher scheduled task
- `run_linux_do_reply_processor.ps1`: launcher used by the reply-processing task
- `install_tasks.ps1`: creates the Windows scheduled tasks
- `doctor.ps1`: basic health check for Python, files, and tasks

## Common Commands

Preview matched items without sending mail:

```powershell
python .\linux_do_watcher.py --config .\config.json --dry-run
```

Run a normal watcher cycle:

```powershell
python .\linux_do_watcher.py --config .\config.json
```

Run the watcher and send current matches on the first run:

```powershell
python .\linux_do_watcher.py --config .\config.json --first-run-send
```

Only process reply emails:

```powershell
python .\linux_do_watcher.py --config .\config.json --process-replies-only
```

Save selected items from the latest sent batch:

```powershell
python .\linux_do_watcher.py --config .\config.json --save-numbers "1 3 5"
```

## Reply Commands

Reply directly to a watcher email and put one or more commands at the top of the reply body:

- `1 3 5`: save selected entries
- `2+`: prefer similar entries in future emails
- `3-`: reduce similar entries in future emails
- `4 note: this looks legit`: save a note on the selected entry

## Scheduler Behavior

Run the bundled installer on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_tasks.ps1
```

The installer creates:

- `LinuxDoWatcher3H`: every 3 hours from `14:10`
- `LinuxDoReplyProcessor10M`: every 10 minutes from `00:00`

The created tasks are configured to:

- not start while the machine is on battery
- stop if the machine switches to battery

## Proxy Safety

The bundled launcher scripts clear common proxy environment variables before running Python. This avoids a common failure mode where requests are silently routed into a dead local proxy such as `127.0.0.1:9`.

## Health And Logs

Useful local files:

- `state.json`
- `watcher_runs.jsonl`
- `last_sent_batch.json`
- `reply_state.json`
- `reply_actions.jsonl`
- `watcher_task.log`
- `reply_task.log`

Common statuses:

- `no_match`
- `no_new`
- `sent`
- `bootstrapped`
- `error`
