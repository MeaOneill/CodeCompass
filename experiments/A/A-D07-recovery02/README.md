# A-D07 committed recovery 02

Same-machine clean local clone of committed checkpoint 36e100346d4aacf3cbd86e00656105992b4d7893. No independent-person or second-machine claim. Original venv reused; credentials and private final keys not copied.

Commands and exit statuses: recovery_receipt.json. All four commands exit 0; 21 new tests, 43 version checks, saved 72-loop audit, 72 new fixture replays match on declared semantic fields. These repeat observations add no human samples. Original full-suite result remains 384 tests, not 405. Archive retains replay raw JSON/CSV without duplicate code snapshots; code comes from checkpoint.

Reproduction helper source is recovery_entry_snapshot.py. Restore this file to tmp/recover_d07.py at a checkout root, provision a fresh clean clone at tmp/A-D07-replay-36e100, and select fresh output/run IDs before rerunning; existing evidence must not be overwritten. Attempt01 records the missing temporary-parent setup failure. Formal G2 and real pretests remain unpassed.
