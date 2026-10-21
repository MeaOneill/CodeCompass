# A-D07 submission format usability revision

`A-D07-submission-ui-v1` is a separate, opt-in presentation revision on the unchanged `A-D07-runtime-v1` collector. The original B/A scripts and frozen snapshot remain intact. The new entry is `scripts/A/serve_d07_submission_v1.py`.

The original form label suggested plain text while the handler parses JSON; the citation field requires `path:start-end` while errors appear above the form. New generic labels explain the required serialization, and a MutationObserver mirrors existing errors beside the submit button. The script never changes input values, intercepts submissions, scores answers or supplies solutions. All methods receive identical format-only hints in the new entry. Old and new UI sessions must not be treated as a controlled method comparison.

Verification: two HTTP checks pass, including byte-for-byte original scripts, unchanged planner output and token protection. JavaScript syntax and a mock-DOM check of visible JSON/citation errors and preserved draft pass; the mock is not browser evidence. Parent candidate integrity remains 43 checks passed. One initial test failed because it incorrectly assumed additive script injection order; the corrected dependency assertion passes. Real-browser acceptance of the new presentation remains pending; CUA documentation access timed out.

Source hashes and snapshots: `configs/frozen/A-D07-submission-ui-v1/manifest.json`. Technical logs: `experiments/A/A-D07-submission-ui01`. This is not a formal G2 freeze. Human consent, background and original observations are local-only and excluded from Git; no participant record is part of this code checkpoint.
