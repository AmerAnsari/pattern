# patternscribe

**Your agent forgets every correction you give it. This makes them stick.**

Run `/patternscribe` at the end of a session and it works out what your corrections say
about how you want work done, then writes those conclusions to a file in your project.
Ask it for its opinion with `/patternscribe suggest`, or let it run with what it has
learned using `/patternscribe lead`.

It only ever runs when you type it. There are no hooks, nothing runs in the background,
and Claude cannot invoke it on its own.

## The problem

You tell the agent *"don't restate business rules in the serializer, they belong on the
model."* It fixes it. The session ends.

Tomorrow it does exactly the same thing, and you type the same sentence again.

## How it works

```
you correct the agent during a session
   |
   v  /patternscribe
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
is a hypothesis; five is a rule. Running `/patternscribe` twice in one session still
counts that session once.

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

If you install at user scope anyway, nothing happens in other directories until you
type `/patternscribe` there. The plugin has no hooks, so it never writes anything you
did not ask for.

Requires Python 3.8+ and bash.

## Commands

| Command | What it does |
|---|---|
| `/patternscribe` | Records what this session taught, right now — use it after you correct something |
| `/patternscribe suggest` | Learns from this session, then tells you how *you* would have done it and where the current approach diverges |
| `/patternscribe lead` | Learns, then carries on with the work under your profile |
| `/patternscribe show` | Prints the profile |
| `/patternscribe why <rule>` | Shows the dated evidence behind a rule |
| `/patternscribe forget <rule>` | Removes a rule and stops it being re-learned |
| `/patternscribe config` | Data location, superpowers toggle |

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

The first `/patternscribe` in a project creates one directory:

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

It is a markdown file; edit it. Mark a bullet `(pinned)` and `/patternscribe` will never
reword, recount or archive it:

```markdown
- Never touch the migrations directory without asking  (pinned)
```

## What it costs

Nothing beyond the session you are already in. `/patternscribe` runs as part of that
session, on its model, the moment you type it. There is no second model call and no
separate process.

## Privacy

Permanent link to this section: [Privacy](https://github.com/AmerAnsari/patternscribe#privacy)

- Patternscribe sends nothing anywhere. It has no server, no endpoint, no account of its
  own, and makes no network calls. It runs inside your Claude Code session, which talks
  to the model the way it always does.
- Nothing is written outside the project directory, and nothing is written at all until
  you type `/patternscribe`.
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
  "use_superpowers": true,      // see below
  "data_dir": ".patternscribe", // move the profile elsewhere if you'd rather
  "decay_sessions": 10          // rules unreinforced this long move to Archive
}
```

### Superpowers

When the [Superpowers](https://github.com/obra/superpowers) plugin is installed and
enabled, `/patternscribe` uses its skill-writing and verification skills before touching
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
