# Writing the upstream sync report

The preparation task runs this non-interactively. Its prompt names an input file and an output file. Nobody answers questions during the run, so make reasonable choices and finish.

## Public-content boundary

The overview and explanations are posted as comments on the public ticket PR. Use only public upstream material: commits and diffs on the `upstream` branch, the prepared commit messages on `upstream-sync`, `.github/upstream-sync/rules`, existing briefs, and upstream PRs on liby/dotfiles. Do not run chezmoi or `upstream-sync affected`, and do not read files under `$HOME`, the user's chezmoi config, or encrypted files; machine impact is computed by the script and stays in the local report. Do not name the user's employer or link internal hosts, tools, or people to it.

## Input

A JSON object with `commits`, a list in ticket order. Each item has `upstream` (full hash on `upstream`) and `prepared` (full hash on `upstream-sync`). Read the full original with `git show <upstream>` and what lands locally from the prepared commit's message and `git show <prepared>`.

## What to write

For each commit, an explanation in Chinese, keeping tool names, file names, and technical terms in their original form:

- What changes and why, using the upstream message and, when the subject carries `(#N)`, `gh pr view N -R liby/dotfiles`.
- The background knowledge needed, extended briefly to related concepts, with further topics named in one line each.
- Behavior changes the user will notice, especially ones that would not produce an error.
- Whether it fails silently, changes machine state (apply-time scripts, package installs or removals, macOS settings, background services), or touches daily tools such as Claude Code or Git, and anything that cannot be undone.
- Depth follows the handling in the prepared message: followed and watched files in full; owned, skipped, or unclassified files in one line. A commit with nothing applied still gets one line saying what upstream did.

Do not repeat the file lists that the prepared message already shows.

The overview, in Chinese: pending commits grouped by risk and topic, the commits that need a decision first (failed to apply, new upstream files, renames into unclassified paths, an owned file renamed onto a followed path), commits that touch local overlays (followed files mapped to `upstream.*` copies), and runs of commits on the same files that are candidates for combining.

A brief for each tool or concept that first appears in a followed or watched file and has no file in `.github/docs/briefs/`, following the Briefs section of the skill.

## Output

Write one JSON object to the output file:

```json
{
  "overview": "中文 Markdown",
  "commits": [{"upstream": "<full hash>", "explanation": "中文 Markdown"}],
  "briefs": [{"tool": "<file name without .md>", "content": "中文 Markdown"}]
}
```

`commits` has one entry per input commit, in input order. `briefs` may be empty. Do not edit the repository; the script posts the comment and commits the briefs.
