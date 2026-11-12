---
name: upstream-sync
description: Process this repository's upstream sync ticket, the `upstream-sync` pull request that carries liby/dotfiles changes prepared by `.github/upstream-sync/bin/upstream-sync`. Explains each pending upstream commit in Chinese, records the user's decisions (accept, adjust, combine, skip, defer, change a file's handling) in commit history, merges the processed part into main, and applies it with chezmoi. Also writes the Chinese report when the preparation task runs it non-interactively. Use when the user wants to sync, review, or process upstream changes, or asks about the ticket, the `upstream` mirror branch, or `.github/upstream-sync/rules`. Not for ordinary edits to local dotfiles that do not involve upstream changes.
---

# Upstream sync

When the prompt asks for the upstream sync report (a non-interactive run started by the preparation task), follow [the report instructions](references/report.md) and skip everything below.

The workflow implements `.github/upstream-sync/design.md`; requirement numbers such as R17 come from `.github/upstream-sync/requirements.md`. Read the matching design section when a case below does not cover the situation.

## Safety rules

- Never decrypt, view, or apply encrypted files. Every `chezmoi diff` and `chezmoi apply` names its targets and carries `--exclude=encrypted`; never run either without targets.
- `~/.local/share/chezmoi` is the chezmoi source directory and stays on `main`, because `chezmoi apply` deploys whatever is checked out there. Edit the ticket only in the worktree `~/Code/worktrees/chezmoi-upstream-sync`.
- A followed file (`follow` rule, including its `upstream.*` copy) only takes upstream changes whole (R17). Local adjustments go into files the user owns, usually the local template that includes the `upstream.*` copy; never hand-edit a followed file.
- Ask before every push and before applying. When the runtime refuses a push, give the user the exact command to run with `!` instead of retrying another way.

## Where things are

- `upstream`: read-only mirror of liby/dotfiles `main`, fast-forward only. `git show <sha>` there gives the full original commit, including files this repo does not use.
- `upstream-sync`: the ticket branch, based on `main`. Each pending commit maps one upstream commit to local paths. Its message is the upstream message followed by `Applied`, `Not applied` (each path with its handling), `New upstream files`, and the trailers `Upstream-Commit`, `Upstream-Author`, `Upstream-Decision: pending`. Path notes `added`, `deleted`, and `renamed to/from` mark file-level changes; `Failed to apply` means the commit is empty because a local file did not match upstream.
- `.github/upstream-sync/bin/upstream-sync`: `check` validates the rules file in the current checkout and lists rules that match nothing, overridden rules, upstream files that land on registered local paths (a `local` rule, or the `X.tmpl` template implied by `follow X > copy`), unclassified upstream files, and unregistered local-only files; `pending` lists upstream commits not yet in `main`; `affected OLD NEW` renders both source versions and lists the deployed files and scripts whose rendered content differs, failing when either version does not render; `prepare` belongs to the preparation task.
- Briefs live in `.github/docs/briefs/<tool>.md`.

## Start a session

1. In the worktree, confirm that `upstream-sync` is checked out with no uncommitted changes, then `git fetch origin` and compare `origin/upstream-sync` with the local branch; if they differ, stop and ask, because another machine may have processed part of the ticket.
2. Run `upstream-sync check` and report its warnings. A rule that matches nothing usually means upstream renamed or deleted a file, an unclassified file usually needs a new rule, and an upstream file on a registered local path means upstream now uses a path the user owns, so the user chooses between renaming the local file and changing its registration: replace a `local` entry with an `own` rule, or update the `follow X > copy` rule that implies `X.tmpl`; all become decisions in this session. For a rename, add the rule for the new path but keep the old path's rule until the renaming commit is processed, because earlier pending commits still change the old path.
3. Find the open PR with `gh pr list --head upstream-sync --state open` and add the `in-progress` label (`gh label create in-progress` once if it does not exist). While the label is on, the preparation task only updates the mirror.
4. Give an overview in Chinese: the pending commits grouped as in the PR body, the commits that need a decision before anything else (failed, new files, renames into unclassified paths, render failures), and commits that change the same files in sequence and are candidates for combining. Agree with the user on this session's scope, for example one date range.
5. Record the starting point: `git update-ref refs/upstream-sync/session-start HEAD`, then `git switch --detach $(git merge-base main HEAD)`. Processed commits are built on this detached HEAD; the `upstream-sync` branch stays untouched until wrap-up, so abandoning the session is `git switch upstream-sync`.

## Explain each commit

For each commit in the agreed order, explain in Chinese before asking for a decision:

- What it changes and why, from the upstream message, the diff on `upstream`, and the upstream PR when the subject carries `(#N)` (`gh pr view N -R liby/dotfiles`). Name the background knowledge it needs (R11).
- Depth follows the handling: followed and watched files get a full explanation; files that are `own`, `skip`, or unclassified get one line, except that a change to an owned file mentions what upstream did that the user may want to copy.
- What happens to this machine: run `upstream-sync affected <previous> <prepared>` for the prepared commit alone. Mark changes that fail silently, change machine state, or touch daily tools (R24), and separately anything that cannot be undone, such as uninstalls or system settings (R25). A render failure means the commit breaks chezmoi as prepared; explain the cause and propose a fix.
- Learning follows the change: extend briefly to related concepts and mention further topics in one line each (R14). When a tool in a followed or watched file already has a brief, cite it and verify any command you take from it against the current repo or docs (R44). When it has none, offer to write one (see Briefs).

## Record decisions

Build processed commits on the detached HEAD. Keep the user as author and let the user's Git configuration sign the commits. The message of a processed commit is a Chinese summary line, a Chinese explanation, then the prepared message with `Upstream-Decision` changed. When the decision differs from upstream (adjusted, skipped), the Chinese part states the reason (R36).

- Accept: `git cherry-pick --no-commit <prepared>`, then `git commit --allow-empty -F <message file>` with `accepted`.
- Adjust: accept with `adjusted`, then make the local change in an owned file and commit it separately with the reason.
- Combine: `git cherry-pick --no-commit` each commit in order, then one commit with `combined`, one Chinese explanation for all, every upstream message, and one `Upstream-Commit` trailer per upstream commit.
- Skip: `git commit --allow-empty` with the Chinese reason and `skipped`. A commit that changes followed files cannot simply be skipped (R17): the user chooses between changing those files to `own` first and accepting with a local overlay.
- Defer: do nothing now; deferred commits return to the ticket at wrap-up.
- Process out of order: pick that commit now; the rest return later in their original order.
- Change a file's handling: edit `.github/upstream-sync/rules` and commit it on its own, before the commit it affects, with the reason in Chinese (R8), then run `upstream-sync check`. Switching to `follow` copies the current version from `upstream` (`git show upstream:<path>`), not the history. Switching away from `follow` deletes the local copy and adds deleting the deployed file to the manual steps. Declining a new upstream file is a `skip` rule plus `git rm` of that file before committing the accepted change.

When a cherry-pick conflicts, stop and show the conflict; do not resolve a followed file by hand. After each decision, show the processed commits so far with `git log --oneline main..HEAD`.

## Wrap up

Let `X` be the processed tip (the detached HEAD) and keep the list of pending commits not processed in this session, in their original order.

1. In `~/.local/share/chezmoi`, check `git status`; stop if uncommitted changes touch files the merge changes. Run `git merge --no-ff X` with a message listing each processed upstream commit (short hash, subject, decision). Do not push yet.
2. Run `upstream-sync affected ORIG_HEAD main` there. If it fails, undo the merge with `git reset --keep ORIG_HEAD` and return to the worktree. Otherwise preview with `chezmoi diff --exclude=encrypted <targets>`, list R24 and R25 items, and list scripts that would run; mark scripts unrelated to this merge and let the user decide whether they run now. Do not run a full `chezmoi apply`, because it would also overwrite unrelated local drift.
3. After the user agrees, run `chezmoi apply --exclude=encrypted <targets>`. When a script that would run reads a file this merge changes, such as a helper that a reloaded launchd job runs, apply the files first with `--exclude=encrypted,scripts` and the scripts in a second apply: one apply with explicit targets has run scripts before writing the files, and the job then ran the old helper without any error.
4. Verify: `chezmoi diff --exclude=encrypted <targets>` is now empty, and for each changed `upstream.*` copy the consuming target still contains its local overrides. List manual steps: `chezmoi init` when `affected` warned that the config template changed, Maskey entries, service restarts, and deployed files of `removed` targets, which chezmoi does not delete.
5. After the user agrees, push `main`. Rebuild the ticket in the worktree: `git switch -C upstream-sync main`, remove the `in-progress` label, then run `upstream-sync prepare --no-mirror`. It prepares the remaining commits again under the current rules, which this session may have changed, pushes the branch with `--force-with-lease`, and updates the PR. With no remaining commits the branch equals `main` and GitHub marks the PR merged.

## Briefs

A brief introduces a tool or concept that first appears in a followed or watched file (R38). Write it in Chinese at `.github/docs/briefs/<tool>.md` with: what it is and which problem it solves, how upstream uses it (in outline, not per file), key points and pitfalls, links for further study, and the upstream commit and tool version it was checked against (R40). Leave out details that change often (R41) and anything that ties it to the user's employer (R45). Commit a brief separately with no `Upstream-*` trailers. When a later commit changes, upgrades, or replaces the tool, update the brief in the same session (R42); when upstream retires it, mark the brief as retired with the replacing commit and reason instead of deleting it (R43).
