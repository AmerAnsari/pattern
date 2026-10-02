# patternscribe

**Your agent forgets every correction you give it. This makes them stick.**

When you correct Claude, patternscribe works out what the correction says about how you
want work done, and writes it to a file in your project. Ask it for its opinion with
`/patternscribe suggest`, or let it run with what it has learned using
`/patternscribe lead`.

It runs inside your session, never behind it. There are no hooks and nothing runs in the
background. Claude captures a correction as it happens, or you ask it to — and
`"auto_capture": false` leaves it to you alone.

## The problem

You tell the agent *"don't restate business rules in the serializer, they belong on the
model."* It fixes it. The session ends.

Tomorrow it does exactly the same thing, and you type the same sentence again.

## How it works

```
you correct the agent during a session
   |
   v  Claude runs patternscribe  (or you do: /patternscribe, "remember that")
   |- reads the profile, merges in what this session proved
   v
<project>/.patternscribe/PATTERNS.md

a later session
   |
   v  /patternscribe suggest   or   /patternscribe lead
   |- reads the profile and works under it
```

After a few sessions `PATTERNS.md` looks like this — every line learned, none written by
hand:

```markdown
## Working agreement — how to collaborate here
- Ask before committing or pushing, always  (seen 3x, last 2026-09-29, #12)
- Once a design decision is made, build on it — don't return with a menu of
  options covering ground already settled  (seen 2x, last 2026-09-29, #12)

## Engineering defaults — what this user would choose
- Keep one source of truth for each business rule — never restate it in a
  second layer  (seen 4x, last 2026-09-29, #11)

## Do / Don't — hard rules from corrections
### Don't
- Don't add speculative abstraction before the second use case exists  (seen 2x, last 2026-09-24, #9)
```

`(seen Nx)` counts how many separate sessions the preference showed up in. One sighting
is a hypothesis; five is a rule. Capturing twice in one session still counts that
session once.

`#12` says which captured session last saw the rule. Preferences change, so a rule that
goes `decay_sessions` captured sessions (default 10) without coming up moves to
`## Archive`, where it is kept but no longer followed. It comes back if you show the
preference again. Only sessions with a capture count, so leaving a project alone for a
month ages nothing.

A new rule that settles the same choice differently replaces the old one — switch from
`requests` to `httpx` and the `requests` rule goes, even if you never mention it. If two
conflicting rules do end up in the profile, `suggest` shows you both and `lead` asks
which one applies before relying on either.

## Install

Patternscribe is a Claude Code plugin. Install it into one project at a time:

```bash
cd your-project
claude plugin marketplace add ameransari/patternscribe
claude plugin install patternscribe@ameransari --scope local
```

Or from inside Claude Code: `/plugin`, pick patternscribe, then **Install for you, in
this repo only (local scope)**.

**Why local scope.** It enables the plugin for you, in this project only, recorded in
`.claude/settings.local.json`, which stays out of git. Nobody else on the project gets
it unless they install it too. Claude Code's own default is user scope, and a plugin
cannot change that, so pass `--scope local` yourself.

If you install at user scope anyway, it is available in every project, and the first
correction Claude captures in a directory creates `.patternscribe/` there. Set
`"auto_capture": false` if you would rather that only happen when you ask.

Requires Python 3.8+ and bash.

## Commands

| Command | What it does |
|---|---|
| `/patternscribe` | Records what this session taught, right now |
| `/patternscribe suggest` | Learns from this session, then tells you how *you* would have done it and where the current approach diverges |
| `/patternscribe lead` | Learns, then carries on with the work under your profile |
| `/patternscribe show` | Prints the profile |
| `/patternscribe why <rule>` | Shows the dated evidence behind a rule |
| `/patternscribe forget <rule>` | Removes a rule and stops it being re-learned |
| `/patternscribe config` | Auto-capture and superpowers toggles; where the profile lives |

You don't have to use the slash form. "Run patternscribe", "remember that", or "what
have you learned about how I work?" work too.

### Automatic capture

With `auto_capture` on (the default), Claude notices when you correct it, refuse an
action or restate a preference, records it, says so in one line, and carries on. It only
ever captures on its own; it never starts `lead`, `suggest` or `forget` unless you ask.

Turn it off per project and patternscribe saves only when you ask:

```json
{ "auto_capture": false }
```

When it is off, Claude still notices a correction. It saves nothing, but ends its reply
with a reminder so you can keep it:

> Not saved for future sessions — run `/patternscribe` to keep this one.

`/patternscribe suggest` always learns before it advises. An opinion that ignores the
correction you gave ten minutes ago is worse than no opinion, because it sounds
informed. Its output ends with a **"Not sure about"** section listing where your profile
is silent — so you can tell learned preference from the model's own guess.

### Having every session follow the profile

Patternscribe does not inject anything into your sessions. If you want the profile in
front of every session in a project, add this line to that project's `CLAUDE.md`:

```markdown
@.patternscribe/PATTERNS.md
```

That is your choice to make, and removing the line undoes it.

## What appears in your repo

The first capture in a project creates one directory:

```
<your project>/.patternscribe/
  PATTERNS.md    the profile — readable, editable, yours
  journal.md     the evidence behind every rule, with dates and quotes
  config.json    your overrides (starts nearly empty)
```

Commit it to share the profile with your team, or add `.patternscribe/` to `.gitignore` to
keep it to yourself. Both work.

Everything is per project. A profile learned in one repo never leaks into another, and
nothing is written outside the project.

### Editing it by hand

It is a markdown file; edit it. Mark a bullet `(pinned)` and patternscribe will never
reword, recount or archive it:

```markdown
- Never touch the migrations directory without asking  (pinned)
```

## What it costs

No separate bill. Patternscribe runs as part of the session you are already in, on its
model. There is no second model call and no separate process. A capture does use some of
that session's context and tokens; turn `auto_capture` off if you want to choose when.

## Privacy

Permanent link to this section: [Privacy](https://github.com/AmerAnsari/patternscribe#privacy)

- Patternscribe sends nothing anywhere. It has no server, no endpoint, no account of its
  own, and makes no network calls. It runs inside your Claude Code session, which talks
  to the model the way it always does.
- Nothing is written outside the project directory, and nothing is written at all until
  the first capture.
- The profile records how you work, never what you worked on. Secrets, code, file
  contents, personal data and one-off task facts are out of scope by design.
- `journal.md` quotes what you said, so you can see the evidence behind a rule. If you
  typed something personal in a correction, that sentence can be quoted there. It stays
  on your machine like everything else, and deleting the line removes it.

## Configuration

`<project>/.patternscribe/config.json` holds overrides only; anything absent falls back to the
shipped defaults.

```jsonc
{
  "auto_capture": true,         // capture corrections without being asked
  "use_superpowers": true,      // see below
  "decay_sessions": 10          // captured sessions a rule can go unseen before it is archived
}
```

### Superpowers

When the [Superpowers](https://github.com/obra/superpowers) plugin is installed and
enabled, patternscribe uses its skill-writing and verification skills before touching
your profile. Without it, nothing breaks: the same discipline is written out inline in
`SKILL.md`. `claude plugin list` tells you whether it is enabled.

## Uninstall

```bash
claude plugin uninstall patternscribe --scope local
```

Use the scope you installed with. Then `rm -rf .patternscribe/` in any project you want
to forget. That's all of it — nothing is installed outside the plugin directory and the
projects you used it in.

## License

MIT
