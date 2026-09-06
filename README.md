# Superspreadsheets

### Making Qwen3.8-27B reliable at real spreadsheet work through measurement, verification and adaptive inference.

Built for the **Ylookup × Encode AI Hackathon — Research Track**.

Given an Excel workbook and a natural-language instruction, the system must return the modified workbook. A task only passes when **every graded cell is correct after recalculation**.

We kept the required `Qwen/Qwen3.8-27B` model and treated the project as an ML-systems research problem:

> measure the failures → identify the mechanism → change one thing → evaluate → keep only what survives.

## Results

| Evaluation | Exact task pass rate |
|---|---:|
| Organizer one-shot reference | **59.0%** |
| Our final public 400-task run | **78.0% — 312/400** |
| Fixed dev split | **85.0% — 51/60** |
| Held-out local test (single use) | **91.67% — 55/60** |

The 59.0% number is the organizer-provided reference rather than a run reproduced by us. Dev, local-test and full-400 numbers are different evaluation sets and should not be compared as if they were repeated measurements of the same sample.

Final full-400 metrics:

- **Exact pass:** 312 / 400
- **Cell-level task pass:** 83.64%
- **Sheet-level task pass:** 65.6%
- **Missing tasks:** 0
- **Evaluation errors:** 0

Compared with our earlier full-400 champion, the finalist produced **22 FAIL→PASS and 15 PASS→FAIL transitions, net +7 tasks**.

---

## What we built

The final system is not a single prompt.

It is a conservative inference cascade around Qwen3.8-27B that gives additional compute and spreadsheet-specific handling only when there is evidence that the ordinary path is failing.

```text
workbook + instruction
        │
        ▼
┌─────────────────────────┐
│ Qwen3.8-27B             │
│ values-first solve      │
│ 24,576 token budget     │
└────────────┬────────────┘
             │
             ▼
      golden-free checks
             │
       ┌─────┴─────┐
       │           │
    healthy     distressed /
       │        view-doomed
       │           │
       │           ▼
       │   expanded workbook view
       │   formula-capable solve
       │   32,768 token budget
       │           │
       │     evidence-fed repair
       │           │
       └─────┬─────┘
             ▼
      structural invariants
             │
             ▼
       artifact selection
             │
             ▼
 typed + sheet-aware writer
             │
             ▼
   LibreOffice recalculation
             │
             ▼
        final workbook
```
