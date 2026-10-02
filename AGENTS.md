# Working on `patternscribe`

Notes for anyone — human or agent — changing this repo.

## What this is

A plugin that reads finished agent sessions and maintains a per-project profile of how
its owner wants work done. Claude Code only.

## Layout

```
.claude-plugin/              plugin and marketplace manifests
skills/patternscribe/        the skill the live agent follows
commands/patternscribe.md    the /patternscribe slash command
hooks/                       session-start / session-end, + hooks.json
lib/                         extraction, config, the distiller
prompts/distill.md           what the background model is told
config.default.json          shipped defaults
```

## Rules that are not negotiable

**Nothing leaves the project.** No telemetry, no network calls beyond the runner the
user configured. Data is per project; there is no user-global store and adding one is
not an enhancement.

**No third-party dependencies.** `lib/` is Python standard library only and the hooks
are bash. This installs into other people's repos; it does not get to bring a
dependency tree with it.

**Digests never carry payload.** The extractor emits tool *names and summarised
arguments*, never tool output or file contents. `lib/hosts/base.py::SAFE_ARG_KEYS` is an
allowlist for exactly this reason — a new tool's arguments are dropped by default rather
than leaked by default. If you widen it, say why in the commit.

**Hooks never break a session.** Every path in `hooks/session-end` and
`hooks/session-start` exits 0. A hook that fails loudly on someone's exit is worse than
one that silently does nothing.

**Sessions are counted once.** `state/analyzed` is the ledger and the session-end hook
checks it. Confidence counts are the only signal the profile has; re-analysing a session
to "double-check" corrupts them.

**Never spend without a gate.** `extract.py --score` runs locally and decides whether a
session is worth a model call. Any new capture path needs the same gate.

## Things that will bite you

- **`--add-dir` is variadic.** Passing the prompt as a trailing argument gets it eaten as
  a directory. The default runner uses stdin; leave it that way.
- **A distill run is itself a session.** Everything it spawns sets `PATTERNSCRIBE_DISTILL=1`
  and both hooks return immediately when they see it. Without that it analyses its own
  exit for ever.
- **`--max-budget-usd` too low reads as failure.** A budget-exceeded error means the
  model *answered*; `config.py` treats it as a successful probe. Don't "fix" that.
- **`setsid` is Linux-only.** macOS and BSD take the `nohup` branch.
- **Hook scripts are extensionless on purpose.** Claude Code's Windows detection
  prepends `bash` to any command containing `.sh`, which would double-invoke them.
- **`privacyPolicyUrl` warns in `claude plugin validate`.** The directory portal asks
  for it in `plugin.json`; Claude Code does not know the field and reports it as an
  unknown top-level key that it strips at load time. Both are right, and the field is
  harmless — it exists for the directory. Do not "fix" the warning by removing it, and
  do not run `claude plugin validate --strict` in CI expecting a clean pass.
- **Host-injected text arrives in the user role.** Task notifications, interruption
  notices and canned rejection blurbs are filtered by `SYNTHETIC` and
  `SYNTHETIC_FEEDBACK` in `extract.py`. Without those you learn rules about the harness
  talking to itself.

## Versioning

Two manifests carry the version. Never edit them by hand:

```bash
scripts/bump-version.sh 0.2.0
```

It writes every file listed in `.version-bump.json` and fails if anything is left stale.

## Testing a change

No test framework — this is shell and stdlib Python against real transcripts.

```bash
# extraction, free
python3 lib/extract.py <a real transcript>.jsonl --score
python3 lib/extract.py <a real transcript>.jsonl --cwd <project>

# the hooks, free
echo '{"cwd":"<project>","session_id":"x","transcript_path":"..."}' | bash hooks/session-end
echo '{"cwd":"<project>"}' | bash hooks/session-start

# the distiller without spending: a runner that only prints
# see skills/patternscribe/references/runners.md, writes_files:false
```

Before shipping a change to the prompt or the merge rules, run the distiller twice
against two *different* real transcripts that share a preference, and check the shared
rule reaches `(seen 2x)` without a near-duplicate appearing. That is the behaviour the
whole thing rests on.

## Claude Code only

Support for Cursor, Codex and Gemini CLI was removed before the first release. Don't add
another host's manifest back: every host is another place the privacy rules above have
to hold, and only Claude Code gives the plugin both a session-end hook and a transcript
it can read.

## Credits

The polyglot `hooks/run-hook.cmd` wrapper technique is from
[Superpowers](https://github.com/obra/superpowers) (MIT).
