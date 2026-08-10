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

__all__ = ["classify_sync_state"]


def classify_sync_state(repo_text, global_text, invariants=(), merged_text=None):
    """Classify the relationship between a repository copy and its installed copy.

    Args:
        repo_text:   contents of the repository copy (the source of truth).
        global_text: contents of the installed copy under ``~/.claude/``.
        invariants:  strings that must be present in the repository copy. A missing one is
                     ``drift`` regardless of how the two copies otherwise relate.
        merged_text: contents of the file at the last merged revision, if the caller can obtain
                     them (``git show origin/main:<path>``). This is what ``install.sh`` would
                     have installed. Without it, any difference can only be reported as ``drift``,
                     because content alone cannot prove the installed copy is merely older.

    Returns:
        One of ``"identical"``, ``"pending"``, or ``"drift"``.

    Why ``merged_text`` and not a content heuristic: an earlier version of this helper defined
    ``pending`` as "the repository copy only added lines". That is wrong, because a real edit
    *modifies* lines, so the previous wording survives only in the installed copy and looks exactly
    like divergence. There is no way to tell "the repo edited this line" from "someone hand-edited
    the installed copy" by comparing the two texts. The last merged revision settles it: that, and
    only that, is what a correct install would have produced.
    """
    if any(inv not in repo_text for inv in invariants):
        # Both copies agreeing on a lost invariant is not agreement worth having.
        return "drift"

    if repo_text == global_text:
        return "identical"

    if merged_text is not None and global_text == merged_text:
        # The installed copy is exactly the last merged revision. The repository copy carries
        # unmerged work ahead of it. The operator owes an ./install.sh once that work merges.
        return "pending"

    return "drift"
