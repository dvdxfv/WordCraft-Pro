# Smoke Test Matrix

## Goal

This matrix defines smoke testing for real sample documents based on:

- application feature chains
- historical bug clusters from `docs/CHANGELOG.md`
- previous batch plans under `PLANS/`

Smoke testing here means:

1. use many real sample files
2. validate the main user-visible feature chains end to end
3. focus on "can the app handle this document correctly" rather than only "does one function return expected JSON"

---

## Core Principle

Existing tests in `tests/` mostly cover:

- unit behavior
- regression points
- API contracts
- a few browser E2E happy paths

Those are necessary but not sufficient for smoke.

Real smoke should be organized by **feature** and executed against **sample sets**.

The correct testing question is not:

- "Which pytest files exist?"

The correct testing question is:

- "For each user-facing feature, can a diverse set of real documents run through it without breaking, regressing, or producing obviously wrong output?"

---

## Feature-Based Smoke Scope

### 1. File Open / Parse / Preview

User chain:

`upload/open file -> parse -> preview renders -> tabs and metadata are correct`

Must verify:

- file can be opened successfully
- preview is not blank
- document text is visible
- `docContents` is populated
- structured metadata exists when expected
- file type routing is correct (`doc`, `docx`, `pdf`, `xlsx`, `txt`, `md`)

Bug history relevance:

- `.doc` conversion fallback chain
- docx-preview rendering regressions
- HTML-vs-structured-content drift
- document structure recognition issues

Current related tests:

- `tests/e2e/test_upload_preview_flow.py`
- `tests/test_bridge_api.py`
- `tests/test_compatibility.py`

Gap:

- no batch sample sweep
- no `.doc` sample corpus coverage
- no structured pass/fail report by sample

### 2. Rule QA

User chain:

`open file -> run rule QA -> issues appear -> locate works -> no false blank result`

Must verify:

- issues can be produced on realistic files
- zero-issue files do not crash
- known bad files produce expected classes of issues
- `location_text` can locate content in preview
- categories are not silently skipped

Bug history relevance:

- runQA empty-result chain bugs
- punctuation / typo false positives
- format QA integration
- location and highlight failures

Current related tests:

- `tests/test_batch_regression.py`
- `tests/test_format_checker.py`
- `tests/e2e/test_qa_rule_flow.py`

Gap:

- E2E test currently mocks `runQA`
- not validating real QA behavior on many samples

### 3. AI QA / AI Parse

User chain:

`upload template or document -> AI parse / AI QA -> result shown -> saved rules usable`

Must verify:

- AI parse input path uses real extracted text
- parse result is structurally usable
- saved format rules can be reused
- long or messy documents do not break the flow

Bug history relevance:

- AI format parser wrong extraction
- parse result field loss
- save-as-format-rules path

Current related tests:

- `tests/e2e/test_format_qa_workflow.py`
- `tests/e2e/test_qa_ai_flow.py`

Gap:

- much of current E2E is interaction-oriented
- sample diversity is too low

### 4. Cross-Reference Check

User chain:

`open file -> run XRef -> targets and issues are correct -> click location is correct`

Must verify:

- references section is recognized
- target scanning is correct
- result ordering follows document order
- duplicate reference-number scenarios remain stable
- click location jumps to the right instance

Bug history relevance:

- reference section not recognized
- duplicated matches
- wrong ordering
- wrong click target
- paragraph occurrence mapping problems

Current related tests:

- `tests/test_phase5.py`
- `tests/test_batch_regression.py`
- `tests/e2e/test_xref_flow.py`

Gap:

- browser smoke does not assert real semantic correctness deeply
- only one fixed sample is effectively used

### 5. Format Compliance

User chain:

`save rules -> upload document -> run QA -> detect font/size/spacing mismatches correctly`

Must verify:

- body vs heading rules work on real Word files
- TOC / cover / references are not wrongly treated as body
- partial rules do not break QA
- run-level inherited styles still surface correctly

Bug history relevance:

- format checker integration
- style inheritance
- TOC / cover / reference misclassification
- false positives on non-body sections

Current related tests:

- `tests/test_format_checker.py`
- `tests/test_document_structure.py`
- `tests/e2e/test_format_qa_workflow.py`

Gap:

- no broad real-sample sweep

### 6. Export / Roundtrip

User chain:

`open file -> export -> resulting docx is readable and not obviously damaged`

Must verify:

- export succeeds
- output file is downloadable
- file opens in Word/python-docx
- paragraph/style signature is not badly broken
- adopted xref output remains usable

Bug history relevance:

- export format regressions
- font fields missing
- REF field generation

Current related tests:

- `tests/e2e/test_export_docx_regression.py`
- `tests/test_batch7_clone_export.py`
- `tests/test_batch7_refresh_fields.py`

Gap:

- current E2E compares one sample only
- no batch export sweep across mixed document styles

### 7. Auth / Plan / Gating

User chain:

`login -> feature visibility -> quota/gating behavior -> upgrade/redeem path`

Must verify:

- free/pro/team/admin boundaries
- activation code path
- team visibility restrictions
- admin-only interfaces

Bug history relevance:

- Batch 17 / 19 entitlement and admin issues

Current related tests:

- `tests/test_entitlements.py`
- `tests/test_plan_gating.py`
- `tests/test_activation_entry_contract.py`
- `tests/test_team_workspace_contract.py`
- `tests/test_admin_dashboard_contract.py`

Gap:

- this is mostly contract/regression coverage, not sample-file smoke

---

## Sample-Based Coverage Model

Smoke should not use one golden document only. Sample sets should be grouped by document traits.

### Group A: Standard thesis/report docx

Used to verify:

- preview
- QA
- xref
- export

### Group B: Formatting-spec documents

Used to verify:

- AI parse
- save format rules
- format compliance

### Group C: Cross-reference-heavy documents

Used to verify:

- references section scan
- repeated citation numbers
- figure/table/chapter references
- click-to-location correctness

### Group D: Messy real-world Word docs

Used to verify:

- style inheritance
- mixed heading styles
- fragmented runs
- partial formatting metadata

### Group E: Legacy `.doc` files

Used to verify:

- `.doc` conversion fallback
- open/preview success
- downstream QA/xref/export survival

This is the most important current gap.

---

## Recommended Smoke Layers

### Layer 1: Fast gate

Run on a very small sample set after each code change.

Recommended scope:

- one thesis/report docx
- one formatting-spec docx
- one xref-heavy docx
- one legacy `.doc`

Checks:

- open/preview
- rule QA
- xref
- export

### Layer 2: Daily smoke

Run on a larger curated sample corpus.

Recommended scope:

- 10-30 representative files
- include at least 3-5 `.doc` files
- include both good and intentionally messy files

Checks:

- open/preview
- QA
- xref
- export
- result report with failures per file

### Layer 3: Batch verification

Run before declaring a batch closed.

Recommended scope:

- all curated samples
- all features touched by that batch
- explicit replay of the bug classes mentioned in the batch plan/changelog

---

## Mapping Historical Bugs Into Smoke

Smoke cases should explicitly reference historical risk, not only file type.

Example mapping:

- Batch 14:
  - format rules save/load
  - format checker integration
  - partial rules fallback
- Batch 15:
  - AI parse from document text
  - save parsed rules into QA flow
- Batch 16:
  - xref ordering
  - repeated reference-number click location
- Batch 18:
  - cover / TOC / reference structure recognition
  - exclusion from format-body checks
- Batch 17/19:
  - not sample-driven document smoke, but still part of release smoke for gated features

So smoke should be defined as:

- `feature x sample-trait x historical-risk`

not just:

- `run all pytest`

---

## What Existing Tests Are Good For

Use current tests for the following roles:

- `tests/test_batch_regression.py`
  - protects previously fixed bug points
- `tests/test_format_checker.py`
  - protects format-checking core logic
- `tests/test_document_structure.py`
  - protects structure-recognition heuristics
- `tests/test_phase5.py`
  - protects xref engine behavior
- `tests/e2e/*.py`
  - protects a few visible browser chains

These should remain mandatory.

But they are still **supporting gates**, not the full smoke system.

---

## Missing Pieces To Build

### 1. Real sample inventory

Need a maintained sample root with labels such as:

- `format-spec`
- `xref-heavy`
- `good-doc`
- `bad-format`
- `legacy-doc`
- `mixed-style`

Current external sample root:

- `G:\开发项目\备份\samples`

Current manifest:

- `samples/manifest.json`

### 2. Batch sample runner

Need a script or pytest suite that:

1. reads all files from a sample directory
2. uploads each file
3. runs selected features
4. captures pass/fail
5. writes a machine-readable summary

### 3. Feature-specific assertions

Per sample, tests should declare expected behavior such as:

- must open
- must preview
- should have xref targets
- export must succeed
- should not produce empty `docContents`

### 4. Failure report

Need an output report like:

- file name
- file type
- feature
- result
- error summary
- screenshot/artifact path if browser-based

---

## Immediate Practical Conclusion

When planning smoke for this app, the right order is:

1. define feature chains
2. map historical bug classes from `CHANGELOG` and `PLANS`
3. build a labeled real-sample corpus
4. run batch smoke against that corpus
5. keep unit/regression/E2E as supporting gates

If we only look at current pytest filenames, we will miss the real question:

- whether the app still works on the kinds of documents users actually upload

---

## Recommended Next Implementation Steps

1. Create a real sample manifest file under `samples/`.
2. Add labels and expectations per sample.
3. Build a batch smoke runner for `open -> preview -> QA -> xref -> export`.
4. Prioritize `.doc` corpus support first, because that is the largest current blind spot.
5. Keep mandatory regression gates:
   - `tests/test_batch_regression.py`
   - `tests/test_format_checker.py`
   - `tests/e2e/test_batch7_e2e.py -m "e2e and no_login"`

---

## Planning Rule

Every active batch plan that changes product behavior should map its testing
strategy onto this matrix instead of using a vague line like "run regression".

At minimum, each plan should answer:

- which feature chain is changing
- which automated regression test protects the historical bug class
- whether no-login browser coverage is needed
- whether real-sample smoke is required
- what remains as residual risk after the automated checks

