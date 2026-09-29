# Runners

The background distiller shells out to a CLI. Which one is configuration, so this plugin
is not tied to any particular model or vendor.

Everything here goes in the `runner` block of `<project>/.patternscribe/config.json`. Only the
keys you change need to be present.

## The contract

A runner is handed the distillation prompt and is expected to update the profile. There
are two ways it can do that:

| `writes_files` | The runner… | Used when |
|---|---|---|
| `true` (default) | has file tools, reads and edits `PATTERNS.md` itself | Claude Code, Codex, any agentic CLI |
| `false` | only talks: it prints the complete new profile on stdout and the plugin writes it | a plain completion CLI with no file access |

In `false` mode the plugin appends the current profile and the session digest to the
prompt, and asks for the whole file back. It refuses output that does not start with
`#`, leaving the existing profile untouched — so a runner that answers with an apology
cannot destroy the file.

## Placeholders

Substituted into every string in `args`:

| Token | Becomes |
|---|---|
| `{model}` | the resolved model name |
| `{budget}` | `budget_usd` |
| `{data_dir}` | absolute path to the data directory |
| `{digest_file}` | absolute path to this session's digest |
| `{patterns_file}` | absolute path to `PATTERNS.md` |
| `{prompt_file}` | a temp file holding the prompt — only when `"prompt": "file"` |

## Credentials

The runner is started with an allowlist of environment variables that authenticate
nothing: `PATH`, `HOME`, locale, proxy and certificate settings, plus this plugin's own
`PATTERNSCRIBE_*`. It is expected to find its credentials the way it normally does — its
own config file or the system keychain, both reachable through `HOME`. That is how the
default `claude` runner works, and it needs no configuration.

A runner that authenticates from an environment variable instead needs you to name it:

```jsonc
{ "runner": { "pass_env": ["YOUR_RUNNERS_KEY_VARIABLE"] } }
```

`pass_env` is empty by default and nothing is inferred. This plugin does not decide which
of your secrets to hand to a program that talks to the network.

If a runner fails to start, `state/needs-config` and the next session start will say so,
and `pass_env` is the second thing to check after `model`.

## How the prompt is delivered

`"prompt"` picks one:

- `"stdin"` (default) — piped in. Safest: it cannot be mistaken for a flag's value.
- `"file"` — written to a temp file, path available as `{prompt_file}`, deleted after.
- `"arg"` — appended as the last argument. **Avoid this if any flag is variadic.**
  Claude's `--add-dir` takes a list and will swallow a trailing prompt argument, which
  is exactly why the default is `stdin`.

## Default (Claude Code)

```jsonc
{
  "runner": {
    "command": "claude",
    "model": null,              // null -> probe for Opus
    "model_probe": ["opus"],
    "prompt": "stdin",
    "writes_files": true,
    "timeout_seconds": 300,
    "args": [
      "-p",
      "--model", "{model}",
      "--permission-mode", "acceptEdits",
      "--permission-prompts", "none",
      "--allowedTools", "Read,Write,Edit,Glob,Grep",
      "--max-budget-usd", "{budget}",
      "--no-session-persistence",
      "--add-dir", "{data_dir}"
    ]
  }
}
```

`--allowedTools` is deliberately narrow: the distiller has no reason to run commands or
reach the network. `--permission-prompts none` means anything outside that list is
denied rather than hanging forever on a prompt nobody can answer — the session that
triggered this is already gone.

## A different model

```jsonc
{ "runner": { "model": "sonnet" } }
```

Setting `model` explicitly skips the availability probe entirely.

## Another agentic CLI

Any CLI that takes a prompt and can edit files works. Match its own flags:

```jsonc
{
  "runner": {
    "command": "/usr/local/bin/some-agent",
    "model": "its-model-name",
    "prompt": "file",
    "writes_files": true,
    "args": ["run", "--model", "{model}", "--allow-write", "{data_dir}",
             "--prompt-file", "{prompt_file}"]
  }
}
```

## A completion-only CLI

```jsonc
{
  "runner": {
    "command": "llm",
    "model": "gpt-4o",
    "prompt": "stdin",
    "writes_files": false,
    "args": ["-m", "{model}"]
  }
}
```

The plugin writes whatever it prints, after checking it looks like a profile.

## Turning the background runner off

```jsonc
{ "enabled": false }
```

Hooks become no-ops. `/patternscribe` and `/patternscribe suggest` still work — they run in the live
session and never invoke a runner at all.

## Checking your configuration

```bash
python3 <plugin>/lib/config.py show           # merged settings, resolved model
python3 <plugin>/lib/config.py resolve-model  # probe now
tail -20 <data_dir>/state/distill.log         # what the last run actually did
```

The log records the command's shape and argument count, never the prompt or the
profile — it is safe to paste into a bug report.
