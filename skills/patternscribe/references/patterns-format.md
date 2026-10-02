# The PATTERNS.md contract

The `/patternscribe` commands write this file, and so can a person editing it by hand.
Everything that writes it follows the format described here, which is why a profile
survives being maintained by different models on different days.

## Header

```markdown
# Learned patterns

project: git@github.com:owner/repo.git
updated: 2026-09-29
sessions analyzed: 7
```

`project` is the git remote, or the absolute path when there is no remote. Bump
`sessions analyzed` by one per distilled session and set `updated` to today, every time
you change anything below.

## Sections

Exactly these, in this order. Never rename them, never add new ones — `show` and
`suggest` group rules by these names.

| Section | Holds |
|---|---|
| `## Working agreement — how to collaborate here` | When to ask vs. decide, how much to explain, what to do before finishing, tone. |
| `## Engineering defaults — what this user would choose` | The technical calls they make by default. |
| `## Do / Don't — hard rules from corrections` | Anything stated as an instruction. Has `### Do` and `### Don't`. |
| `## Archive — not reinforced recently` | Decayed rules. Still readable, never applied. |

An empty section holds the line `_Nothing learned yet._`. Remove that line when you add
the section's first real bullet, and restore it if you ever empty one.

## Bullets

```
- <imperative instruction>  (seen Nx, last YYYY-MM-DD)
- <imperative instruction>  (seen Nx, last YYYY-MM-DD) (pinned)
```

One line each. Two spaces before the count. Write what to *do*:

| Good | Bad | Why |
|---|---|---|
| `Ask before committing or pushing, always` | `The user is careful about git` | The first can be followed. |
| `Assert error text against the shared constants module, not string literals` | `Cares about test quality` | The second decides nothing. |
| `Reach for select_related before writing any list view` | `Likes efficient queries` | Specific beats sentiment. |

`(seen Nx)` counts **separate sessions** in which the pattern appeared, not how many
times it was mentioned. 1x is a hypothesis; 5x is a rule; `show` lists the
highest counts first.

`(pinned)` marks a bullet a person wrote or protected deliberately. Never reword, never
recount, never archive, never remove it. It is the only guarantee a human has that
automation will not quietly edit their words.

## Merge rules

Applied by anything that writes the file:

1. **Reinforcement.** Evidence matching an existing bullet increments its count and
   updates `last`. It never adds a second bullet.
2. **Near-duplicates are the failure mode.** Before adding anything, read every bullet
   in the target section. "Ask before pushing" and "Confirm before git push" are the
   same rule; merge them, keeping the clearer wording and the higher count.
3. **Contradiction.** Newer evidence wins. Replace the bullet, reset it to `(seen 1x)`,
   and record both wordings in the journal so the change is visible later.
4. **Pins are untouchable.** See above.
5. **Decay.** A bullet not reinforced in the last `decay_sessions` sessions moves to
   `## Archive` with its count intact. Never delete — an archived rule is evidence that
   a preference faded, which is itself worth knowing.
6. **Cap.** Keep the file under 120 live bullets. Over that, archive the weakest first:
   lowest count, then oldest `last`.

## Sessions are counted once

`journal.md` heads every block with the session it came from, and that is the ledger.
Before incrementing anything, check whether this session already has blocks there: if
`/patternscribe` already ran in it, the rules it credited stay credited once. A count of
`5x` therefore means five distinct sessions. Do not re-count a session to
"double-check" — it corrupts the only signal the file has.

## What never goes in

- Secrets, tokens, keys, credentials, environment values.
- File contents, code snippets, command output.
- Personal data: names, emails, addresses, customer data.
- One-off task facts: ticket numbers, branch names, a filename mentioned once.
- Anything already written in the project's own context file or do-don't skill. That is
  in front of every session already; repeating it here spends context twice.

## journal.md

Append-only. One block per rule added or changed:

```markdown
## 2026-09-29 — session 95ff34f6

**Added (Engineering defaults):** Reach for select_related before writing any list
view. — (seen 1x)
Evidence: user stopped the agent at plan approval: "we should care about less and fast
query".
```

Never rewrite an existing block. `/patternscribe why` reads this file, so a rule with no
block here cannot be explained — which is the signal that it was hand-written.
