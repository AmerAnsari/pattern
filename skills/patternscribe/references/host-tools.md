# Hosts

This plugin runs under several agent CLIs. They differ in two ways that matter.

## What each host supports

| Host | Skill | `/patternscribe` command | Injects profile at start | Automatic capture at exit |
|---|---|---|---|---|
| Claude Code | yes | yes | yes | **yes** |
| Cursor | yes | yes | yes | no — use `/patternscribe` |
| Codex | yes | yes | no | no — use `/patternscribe` |
| Gemini CLI | yes | via `GEMINI.md` | no | no — use `/patternscribe` |

Automatic capture needs two things from the host: a hook that fires when a session ends,
and a transcript on disk in a format this plugin can read. Only Claude Code currently
provides both.

**Everything else works everywhere.** The live commands reflect on the conversation the
agent is already in, so they need no transcript file and no hook. On a host without
automatic capture, run `/patternscribe` when you finish something — the result is identical,
it just isn't unattended.

`/patternscribe doctor` reports which of these applies here rather than leaving you to guess.

## Tool names

The skill is written with Claude Code's tool names. Translate as needed:

| Claude Code | Cursor | Codex | Gemini CLI |
|---|---|---|---|
| `Read` | `read_file` | `read_file` | `read_file` |
| `Write` | `write` | `write_file` | `write_file` |
| `Edit` | `search_replace` | `apply_patch` | `replace` |
| `Bash` | `run_terminal_cmd` | `shell` | `run_shell_command` |
| `Grep` | `grep` | `grep` | `search_file_content` |
| `Glob` | `file_search` | `glob` | `glob` |

The tool names never appear in `PATTERNS.md` — rules are about how the user wants work
done, which does not change with the harness.

## Adding a host

To give a new host automatic capture, add a module beside `lib/hosts/claude.py`
implementing the four functions documented in `lib/hosts/base.py`
(`detect`, `find_transcript`, `recent_transcripts`, `iter_events`), then add its name to
`registry` in that file. The adapter's job is to normalise that host's transcript into
the event shape described there — in particular to surface, if the host records them:

- the text a user typed when they stopped an action
- the fact that an action was refused at all
- whether a tool call came back as an error

Those three are most of the signal. A host that records none of them can still be
supported; capture just falls back to the live `/patternscribe` command.

Adapters must never emit tool output or file contents. Everything they yield ends up in
a digest that is handed to a model.
