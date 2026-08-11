#!/usr/bin/env python3
"""Discriminate a legitimate repo-ahead window from real drift between synced copies.

`sdd-global` keeps two copies of several files: the repository copy, which is the source of
truth, and the installed copy under `~/.claude/`, which the operator refreshes by running
`./install.sh`. Between a merge and that install step the repository copy is legitimately **ahead**.

A strict byte-identity assertion cannot tell that window apart from real divergence, so it fails
during every normal change and pressures whoever sees it into one of two bad moves: sync the live
fleet early just to get the suite green, or delete the assertion. Syncing early is the worse of the
two here — it loads unreviewed contracts into the agents that must review them.

This helper names the three states instead:

- ``identical`` — the copies match byte for byte. Nothing to do.
- ``pending``   — the repository copy is strictly ahead: every line of the installed copy still
                  appears in the repository copy, and no invariant has been lost. The operator
                  owes an `./install.sh`. This is a normal, expected state, not a defect.
- ``drift``     — anything else. The installed copy contains a line the repository copy does not
                  (divergence, or a hand-edit of the installed copy), or the repository copy has
                  lost a stated invariant.

The invariants argument is what stops ``pending`` from becoming a blanket excuse: a repository copy
that dropped a load-bearing sentence is ``drift`` even though it is otherwise "ahead".

EXPECTED ON ANY RE-RUN of the callers: ``identical`` or ``pending``. ``drift`` is a real failure.
A caller must never treat an unreadable installed copy as a blanket skip of everything it was
going to assert — report it, and assert what can still be asserted.
"""

import subprocess

__all__ = ["classify_sync_state", "merged_revisions"]


def classify_sync_state(repo_text, global_text, invariants=(), merged_texts=()):
    """Classify the relationship between a repository copy and its installed copy.

    Args:
        repo_text:    contents of the repository copy (the source of truth).
        global_text:  contents of the installed copy under ``~/.claude/``.
        invariants:   strings that must be present in the repository copy. A missing one is
                      ``drift`` regardless of how the two copies otherwise relate.
        merged_texts: contents of the file at revisions reachable from the merged branch — most
                      recent first. Any of these is something ``install.sh`` could legitimately
                      have installed at some point. A single string is accepted for convenience.
                      With none supplied, any difference can only be reported as ``drift``,
                      because content alone cannot prove the installed copy is merely older.

    Returns:
        One of ``"identical"``, ``"pending"``, or ``"drift"``.

    Why historical revisions and not a content heuristic: an earlier version defined ``pending``
    as "the repository copy only added lines". That is wrong, because a real edit *modifies*
    lines, so the previous wording survives only in the installed copy and looks exactly like
    divergence. Comparing the two texts cannot distinguish "the repo edited this line" from
    "someone hand-edited the installed copy". Only the history settles it.

    Why a *set* of revisions and not just the tip: an earlier version compared against the tip of
    the merged branch alone. That is correct right up until a merge lands — at which point the tip
    moves, and an installed copy that is simply one revision behind and awaiting ``./install.sh``
    is reported as ``drift``. That fired for real, on the merge of the feature this helper was
    written for, and a false ``drift`` is corrosive: it trains the reader to sync the live fleet
    reflexively, which is the exact hazard the helper exists to prevent.
    """
    if merged_texts is None:
        merged_texts = ()
    elif isinstance(merged_texts, str):
        merged_texts = (merged_texts,)

    if any(inv not in repo_text for inv in invariants):
        # Both copies agreeing on a lost invariant is not agreement worth having.
        return "drift"

    if repo_text == global_text:
        return "identical"

    if any(global_text == m for m in merged_texts):
        # The installed copy matches a revision that was merged at some point. The repository copy
        # is ahead of it, and the operator owes an ./install.sh.
        return "pending"

    return "drift"


def merged_revisions(repo_root, path, limit=20):
    """Return the file's contents at each recent revision on `origin/main`, newest first.

    Used to give `classify_sync_state` the set of things `install.sh` could legitimately have
    installed. Anchoring on the tip alone breaks the moment a merge lands: the installed copy is
    then one revision behind and reads as drift rather than pending.

    Returns an empty tuple if git is unavailable or `origin/main` cannot be resolved, in which
    case the caller's classification degrades to `drift` on any difference — the safe direction.
    """
    try:
        shas = subprocess.run(
            ["git", "rev-list", f"-{limit}", "origin/main", "--", path],
            cwd=repo_root, capture_output=True, text=True, check=True,
        ).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        return ()
    out = []
    for sha in shas:
        try:
            out.append(subprocess.run(
                ["git", "show", f"{sha}:{path}"],
                cwd=repo_root, capture_output=True, text=True, check=True,
            ).stdout)
        except (OSError, subprocess.CalledProcessError):
            continue
    return tuple(out)
