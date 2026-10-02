# Working on `patternscribe`

Notes for anyone — human or agent — changing this repo.

## What this is

A Claude Code plugin that, when its owner runs `/patternscribe`, distils the current
session into a per-project profile of how they want work done.

## Layout

```
.claude-plugin/              plugin and marketplace manifests
skills/patternscribe/        the /patternscribe skill, and the profile format it follows
lib/                         config resolution and bootstrap
config.default.json          shipped defaults
```

## Rules that are not negotiable

**It runs only when the user types `/patternscribe`.** No hooks, no background process,
no scheduled run. The skill sets `disable-model-invocation: true`, so Claude cannot
trigger it on its own either. Don't add an automatic path back: running unasked in every
session is what installing at user scope used to mean, and that is exactly what this
removed.

**Nothing leaves the project.** No telemetry, no network calls, no second model call.
Data is per project; there is no user-global store and adding one is not an enhancement.

**No third-party dependencies.** `lib/` is Python standard library only, plus bash. This
installs into other people's repos; it does not get to bring a dependency tree with it.

**Sessions are counted once.** `journal.md` heads every block with the session id, which
the skill gets from `${CLAUDE_SESSION_ID}`, and that is the ledger. Confidence counts are
the only signal the profile has; counting a session twice because `/patternscribe` ran
twice in it corrupts them.

## Things that will bite you

- **`privacyPolicyUrl` warns in `claude plugin validate`.** The directory portal asks
  for it in `plugin.json`; Claude Code does not know the field and reports it as an
  unknown top-level key that it strips at load time. Both are right, and the field is
  harmless — it exists for the directory. Do not "fix" the warning by removing it, and
  do not run `claude plugin validate --strict` in CI expecting a clean pass.
- **Install scope is the user's choice, not the plugin's.** Claude Code defaults to user
  scope and has no manifest field to change that. The README's install command passes
  `--scope local`; keep it that way.

## Versioning

Two manifests carry the version. Never edit them by hand:

```bash
scripts/bump-version.sh 0.2.0
```

It writes every file listed in `.version-bump.json` and fails if anything is left stale.

## Testing a change

No test framework — this is shell and stdlib Python.

```bash
claude plugin validate .
python3 lib/config.py show
bash lib/bootstrap.sh <a scratch project>
claude --plugin-dir . # then /patternscribe in a session with a correction in it
```

Before shipping a change to the skill or the merge rules, run `/patternscribe` in two
*different* sessions that share a preference, and check the shared rule reaches
`(seen 2x)` without a near-duplicate appearing. Then run it a second time in the second
session and check the count stays at 2. That is the behaviour the whole thing rests on.

## Claude Code only

Support for Cursor, Codex and Gemini CLI was removed before the first release. Don't add
another host's manifest back.
