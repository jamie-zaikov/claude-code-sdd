# Frozen spans

Each `*.md` here is a byte-exact copy of a safety-bearing span in an agent contract.
`tests/test_non_code_contracts.py` asserts the live contract still matches.

A freeze is deliberate friction. Any added, removed, or reworded sentence inside a frozen span
turns the assertion RED — that is the point, and it is what a verb-keyed guard could not do.
Eleven reworded bypasses once left a 262-test suite green.

To change a span on purpose:

1. Make the contract edit.
2. Run the regenerator (see `tests/regen_frozen.py`).
3. State in the commit message **which span moved and why**.

Regenerating without step 3 defeats the mechanism entirely.
