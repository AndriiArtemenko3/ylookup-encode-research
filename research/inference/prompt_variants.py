"""Task 6: prompt micro-ablation variants. NOT wired into any serving path.

Each is an ADDITIVE clause appended to the champion prompt in a matched-control
experiment (byte-identical everything else; one variant per experiment).
Deliberately excluded by E012's lesson: anything that asks for brevity or
suppressed reasoning.
"""

P_COMPLETE = (
    "\n\nCompleteness contract: the answer range contains exactly {n_cells} target cells. "
    "Return each target cell exactly once — no omissions, no duplicates, no cells outside the range."
)

P_TYPE = (
    "\n\nType contract: numeric values must be JSON numbers (not quoted). Dates must be written "
    "as YYYY-MM-DD HH:MM:SS and times as HH:MM:SS. Use null only when a cell must genuinely be empty."
)

P_CHECK = (
    "\n\nBefore writing your final JSON, verify internally: every required coordinate is present "
    "exactly once; values are not shifted by a row or copied from an adjacent header; the values "
    "implement the instruction rather than echoing nearby cells."
)

P_META = (
    "\n\nTask metadata: instruction_type={instruction_type}; the relevant source data lies at "
    "{data_position}."
)

VARIANTS = {"P-COMPLETE": P_COMPLETE, "P-TYPE": P_TYPE, "P-CHECK": P_CHECK, "P-META": P_META}
