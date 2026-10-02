# Working on `patternscribe`

Notes for anyone — human or agent — changing this repo.

## What this is

A Claude Code plugin that distils a session's corrections into a per-project profile of
how its owner wants work done — when Claude notices a correction, or when asked.

## Layout

```
.claude-plugin/              plugin and marketplace manifests
skills/patternscribe/        the /patternscribe skill, and the profile format it follows
scripts/                     config resolution and bootstrap, plus the version tooling
config.default.json          shipped defaults
```

## Rules that are not negotiable

**It runs inside a live session, never behind one.** No hooks, no background process,
no scheduled run. Claude may invoke the skill when it sees a correction; that path checks
`auto_capture` and stops when it is `false`, and it only ever captures. An explicit ask
always runs.

**Nothing leaves the project.** No telemetry, no network calls, no second model call.
Data is per project; there is no user-global store and adding one is not an enhancement.

**No third-party dependencies.** `scripts/` is Python standard library only, plus bash. This
installs into other people's repos; it does not get to bring a dependency tree with it.

**Sessions are counted once.** `journal.md` heads every block with the session id, which
the skill gets from `${CLAUDE_SESSION_ID}`, and that is the ledger. Auto-capture can run
several times in one session; confidence counts are the only signal the profile has, and
counting that session more than once corrupts them.

## Things that will bite you

- **`privacyPolicyUrl` warns in `claude plugin validate`.** The directory portal asks
  for it in `plugin.json`; Claude Code does not know the field and reports it as an
  unknown top-level key that it strips at load time. Both are right, and the field is
  harmless — it exists for the directory. Do not "fix" the warning by removing it, and
  do not run `claude plugin validate --strict` in CI expecting a clean pass.
- **Install scope is the user's choice, not the plugin's.** Claude Code defaults to user
  scope and has no manifest field to change that. The README's install command passes
  `--scope local`; keep it that way.

## Branches and releases

- **`main`** is the default branch. Every PR targets it and is squash-merged.
- **`release`** is what users get. The plugin directory tracks it, and the README's
  install command pins it (`ameransari/patternscribe#release`), so directory and manual
  installs are always on the same version. Nothing reaches users until it is released.

To release:

1. On a branch off `main`, run `scripts/bump-version.sh 0.3.0`, open a PR into `main`
   titled exactly `Release 0.3.0`, and merge it.
2. Open a PR from `main` into `release`, titled `Release 0.3.0` too, and merge it with
   **Create a merge commit** — never squash or rebase. Squashing rewrites the commits, so
   `release` stops sharing history with `main` and the next release PR conflicts.

CI enforces the rest: a PR into `release` must come from `main`, and only a PR titled
`Release <version>` may change the version. There are no tags; the merge commits on
`release` are the release history.

## Versioning

Two manifests carry the version. Never edit them by hand:

```bash
scripts/bump-version.sh 0.3.0
```

It writes every file listed in `.version-bump.json` and fails if anything is left stale.

## Testing a change

No test framework — this is shell and stdlib Python.

```bash
claude plugin validate .
python3 scripts/config.py show
claude --plugin-dir . # correct it in a session; check it captures, and doesn't with
                      # "auto_capture": false unless you ask
```

Before shipping a change to the skill or the merge rules, capture in two
*different* sessions that share a preference, and check the shared rule reaches
`(seen 2x)` without a near-duplicate appearing. Then capture a second time in the second
session and check the count stays at 2. That is the behaviour the whole thing rests on.
