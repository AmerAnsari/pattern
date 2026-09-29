# patternscribe

**Your agent forgets every correction you give it. This makes them stick.**

`patternscribe` reads each finished session, works out what your corrections say about how you
want work done, and writes those conclusions to a file that every later session reads
before it starts. Ask it for its opinion with `/patternscribe suggest`, or let it run with what
it has learned using `/patternscribe lead`.

## The problem

You tell the agent *"don't restate business rules in the serializer, they belong on the
model."* It fixes it. The session ends.

Tomorrow it does exactly the same thing, and you type the same sentence again.

Session transcripts already record these moments precisely — when you stopped the agent,
and what you typed to explain why. Nothing reads them. `patternscribe` does.

## How it works

```
session exits
   |
   v  session-end hook  (shell, ~30ms, never delays your exit)
   |- nothing worth analysing?  -> stop, costs nothing
   |- already analysed?         -> stop
   v
   detached background run, cost-capped
   |- reads the profile, merges in what this session proved
   v
<project>/.patternscribe/PATTERNS.md

next session starts
   |
   v  injected into its context automatically
   "[patternscribe] 14 rules active. Added after the last session: + …"
```

After a few sessions `PATTERNS.md` looks like this — every line learned, none written by
hand:

```markdown
## Working agreement — how to collaborate here
- Ask before committing or pushing, always  (seen 3x, last 2026-09-29)
- Once a design decision is made, build on it — don't return with a menu of
  options covering ground already settled  (seen 2x, last 2026-09-29)

## Engineering defaults — what this user would choose
- Keep one source of truth for each business rule — never restate it in a
  second layer  (seen 4x, last 2026-09-29)

## Do / Don't — hard rules from corrections
### Don't
- Don't add speculative abstraction before the second use case exists  (seen 2x)
```

`(seen Nx)` counts how many separate sessions the preference showed up in. One sighting
is a hypothesis; five is a rule. The highest counts are injected first.

## Install

```bash
claude plugin marketplace add ameransari/patternscribe
claude plugin install patternscribe@ameransari
```

Restart your session. That is the entire setup — the hooks ship with the plugin, so
there is no config file to edit and nothing to add to your settings.

<details>
<summary>Other hosts</summary>

**Cursor** — add the repo as a plugin source; it loads `.cursor-plugin/plugin.json`.

**Codex** — add the repo as a plugin source; it loads `.codex-plugin/plugin.json`.

**Gemini CLI** — `gemini extensions install https://github.com/ameransari/patternscribe`.

</details>

### What works where

| Host | `/patternscribe` commands | Profile injected at start | Automatic capture at exit |
|---|---|---|---|
| Claude Code | yes | yes | **yes** |
| Cursor | yes | yes | no — run `/patternscribe` |
| Codex | yes | no | no — run `/patternscribe` |
| Gemini CLI | yes | no | no — run `/patternscribe` |

Automatic capture needs a session-end hook *and* a readable transcript. Only Claude Code
provides both today. Everywhere else the same learning happens when you run `/patternscribe`,
because the agent can reflect on the conversation it is already in — it just isn't
unattended. `/patternscribe doctor` tells you which case you are in.

Requires Python 3.8+ and bash. Both are already there on macOS and Linux; on Windows the
hooks use Git Bash if it is installed and skip quietly if not.

## Commands

| Command | What it does |
|---|---|
| `/patternscribe suggest` | Learns from this session, then tells you how *you* would have done it and where the current approach diverges |
| `/patternscribe` | Records what this session taught, right now — use it the moment you correct something |
| `/patternscribe lead` | Learns, then carries on with the work under your profile |
| `/patternscribe show` | Prints the profile |
| `/patternscribe why <rule>` | Shows the dated evidence behind a rule |
| `/patternscribe forget <rule>` | Removes a rule and stops it being re-learned |
| `/patternscribe config` | Model, runner, data location, superpowers toggle |
| `/patternscribe doctor` | Diagnoses hooks, host support, model, queue |

`/patternscribe suggest` always learns before it advises. An opinion that ignores the
correction you gave ten minutes ago is worse than no opinion, because it sounds
informed. Its output ends with a **"Not sure about"** section listing where your profile
is silent — so you can tell learned preference from the model's own guess.

## What appears in your repo

On first run, one directory:

```
<your project>/.patternscribe/
  PATTERNS.md    the profile — readable, editable, yours
  journal.md     the evidence behind every rule, with dates and quotes
  config.json    your overrides (starts nearly empty)
  state/         locks, queues, logs — self-gitignored, never shows in git status
```

Commit it to share the profile with your team, or add `.patternscribe/` to `.gitignore` to
keep it to yourself. Both work.

Everything is per project. A profile learned in one repo never leaks into another, and
nothing is written outside the project.

### Editing it by hand

It is a markdown file; edit it. Mark a bullet `(pinned)` and automation will never
reword, recount or archive it:

```markdown
- Never touch the migrations directory without asking  (pinned)
```

## What it costs

One background model call per session that has something in it, capped by
`budget_usd` (default `$0.50`) and usually well under that.

Sessions with no corrections, no refusals and no edits are skipped before anything is
spent — the check is a local script, not a model. In practice most sessions cost
nothing.

Set `"enabled": false` in `.patternscribe/config.json` to stop background runs entirely;
`/patternscribe` and `/patternscribe suggest` keep working, since they run inside your live session.

## What it runs and what it sends

Stated plainly, because it runs unattended:

**It runs one program: the CLI named in `runner.command`** — by default `claude`, the agent
you already have installed. It is launched detached after a session ends, with the prompt on
stdin and a spending cap. Nothing is downloaded and no code arrives from anywhere at run
time; everything that executes is in this repository.

**That CLI sends the digest to whichever model provider it is configured for**, under your
own account and credentials. This plugin has no server, no endpoint and no account of its
own, and nothing is ever sent to its author.

**The runner receives no credentials from this plugin.** It gets a fixed allowlist of
variables that authenticate nothing — `PATH`, `HOME`, locale, proxy and certificate
settings — and finds its own credentials the way it normally does, from its own config or
keychain. On a typical machine that is 10 variables out of 60.

If your runner authenticates from an environment variable instead, name it yourself:

```jsonc
{ "runner": { "pass_env": ["YOUR_RUNNERS_KEY_VARIABLE"] } }
```

Name the variable your runner actually reads. `pass_env` is empty by default, and this
plugin never decides on its own which of your secrets to hand to a program that talks to
the network — you do.

## Privacy

Permanent link to this section: [Privacy](https://github.com/AmerAnsari/patternscribe#privacy)

- Nothing leaves your machine except that one model call, which your agent already makes.
- Nothing is written outside the project directory.
- Transcripts are reduced locally to a small digest first. **Tool output and file
  contents are never included** — only which tools ran, with which paths, and what you
  said.
- Credential-shaped strings are stripped before anything is sent, and `redact` in the
  config excludes paths (`.env*`, `*.pem`, `*.key`, `secrets/**` by default).
- The profile records how you work, never what you worked on. Secrets, code, personal
  data and one-off task facts are out of scope by design.
- `state/distill.log` records the command's shape, never the prompt or the profile — it
  is safe to paste into a bug report.

## Configuration

`<project>/.patternscribe/config.json` holds overrides only; anything absent falls back to the
shipped defaults.

```jsonc
{
  "enabled": true,
  "use_superpowers": true,      // use the superpowers skills when they're installed
  "data_dir": ".patternscribe",       // move the profile elsewhere if you'd rather
  "budget_usd": 0.50,           // hard cap per background run
  "min_signal": 1,              // raise to only analyse eventful sessions
  "decay_sessions": 10,         // rules unreinforced this long move to Archive
  "redact": [".env*", "*.pem", "*.key", "secrets/**"],

  "runner": {
    "command": "claude",
    "model": null,              // null -> probe for Opus
    "pass_env": []              // env vars to forward; none by default
  }
}
```

### The model

The default is Opus, checked once and cached for 30 days. **If Opus isn't available on
your plan, nothing is silently downgraded** — a profile built by a weaker model is worse
than no profile, and you would never have been told. Instead background capture pauses
and every session start says:

```
[patternscribe] Opus unavailable. Set runner.model in .patternscribe/config.json
          or run /patternscribe config. Auto-capture is paused until then.
```

Set it and capture resumes:

```jsonc
{ "runner": { "model": "sonnet" } }
```

### A different CLI entirely

The background runner is just a command. Any CLI that takes a prompt works, including
ones that can't edit files — they print the new profile and the plugin writes it.
See [`skills/patternscribe/references/runners.md`](skills/patternscribe/references/runners.md) for
worked examples.

## Uninstall

```bash
claude plugin uninstall patternscribe
```

Then `rm -rf .patternscribe/` in any project you want to forget. That's all of it — nothing is
installed outside the plugin directory and the projects you used it in.

## Credits

The polyglot hook wrapper technique comes from
[Superpowers](https://github.com/obra/superpowers) (MIT).

## License

MIT
