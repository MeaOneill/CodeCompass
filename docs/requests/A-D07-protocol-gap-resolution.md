> 授权状态更新：用户已于2026-10-21明确批准为完成A-D07的必要开发验证扩展。本提案已落实为独立v0.3；以下保留原提案历史，不能把其中旧的NOT_AUTHORIZED当当前状态。

# A-D07 frozen protocol reachability gap: proposed resolution

Status: PROPOSED, NOT IMPLEMENTED, NOT AUTHORIZED AS A PROTOCOL CHANGE. Owner A. Applies to technical source checkpoint `588920db9c9b5c041d9687724203da941aef7296`. Contains no participant records.

## Conflict requiring a decision

The A-D07 card requires an actual evidence update with a change in remaining route, while restricting the work to implementation fixes without tuning. The v0.2 entry resets each round to an unknown Beta(1,1) state, permits one common quiz, and uses threshold .7 / lower quantile .1. A pass yields Beta(2,1) and lower bound sqrt(.1), about .316; a fail is lower still. Both remain unmastered. Reading is not mastery evidence. With alpha=gamma=0, these observations do not change the planner's mastery set. Removing a completed unit before the quiz is not a feedback-driven route change. Single-unit tasks have no unread suffix after the quiz at all.

Existing positive repair examples use explicitly simulated independent history. They verify an implementation branch but cannot be relabeled real-human history. Repeated exposure, combining different people's records, carrying unrelated projects' evidence, lowering the threshold after observing results, or adding free quizzes would not solve the acceptance condition legitimately.

## Concrete proposed path, not an executed experiment

Keep v0.2 and its unchanged-route outcomes intact. Register a separate development-only protocol/interface version for a pre-existing-evidence repair scenario. Preserve threshold, lower quantile and planner parameters. Before any new run, fix the project-scoped evidence import rules, evidence collection cost accounting, candidate task and item bank, stopping rule, and actual timestamps/source hashes. Imported history must come from the same real individual and project, with genuinely distinct assessments; no simulated history and no repeated item counted twice. Reading/background pretest answers cannot be silently promoted to calibrated mastery evidence. Equivalent evidence, collection cost and help must be available to every method.

The scenario needs enough legitimate pre-existing evidence to support a skippable concept and a new independent diagnosis capable of revising that evidence. Then run the same planner before/after, retain completed prefix, and record both routes, budget and switching costs. This is conditional: if the actual evidence does not open or close a gate, retain the unchanged route and do not claim the acceptance condition passed. Numerical branch examples are engineering feasibility checks, not evidence that a short-question bank is reliable.

Before collecting any new responses, independently review the non-redundant task coverage and distinct evidence bank. No final-test answers may be accessed. Human operating effort is requested only after this proposed protocol amendment is explicitly authorized and the materials pass review. This would extend A-D07's original no-protocol-change scope; therefore it is not silently implemented as a bug fix.

The alternative is an explicit amendment of the day-card acceptance criterion to allow an unchanged route. That would waive the original requirement, not demonstrate it; this proposal does not recommend calling the original card passed by that route.

## Current limits

No new threshold, evidence bank, participant history or formal outcome is produced by this document. Independent AI review is separate from human protocol approval. Formal G2, main integration and formal freeze tags remain unapproved. The task remains unpassed until the original requirement is met or the user explicitly changes its scope; it must not be advanced merely because engineering checks pass.
