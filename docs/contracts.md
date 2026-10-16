# CodeCompass数据契约1.0.0

A-D01提出并冻结供B加载的结构版本，待B独立审核。机器入口schemas/contracts.schema.json使用JSON Schema Draft 2020-12，七种顶层对象各有JSON样例。

## 对象数量冲突与版本决定

V6.2 Word总说明书和01说明书实际仅列六种对象，任务卡要求七种。本轮保留原六种并补充CodeTask承载明确要求的真实任务，不声称说明书原来已定义七种。B先按本版接入，有分歧在docs/requests登记，由A集成升版。新增必填、删除字段或语义改变属于破坏变更。

## 通用语义

所有schema字段必填；仅anyOf包含null者允许未知。0是已知零，不能代表未测；[]是已知无条目，不能代替未采集。额外字段拒绝。is_fixture=true为序列化夹具，禁止计入实测；任务/源码记录为false只表示设计与来源记录真实，不表示学习有效。时间必须带时区，启用FormatChecker；SHA使用小写十六进制。路径是仓库相对POSIX，禁止绝对路径和..。

SourceSpan行号1起，首尾包含，start<=end。content_hash=源码UTF8解码后splitlines取闭区间，以LF连接并补末尾LF的SHA256。RepoSnapshot.files保留固定Git blob原始字节hash；hash是files数组按path排序、json.dumps(sort_keys=True,separators=(',',':'))编码UTF8后SHA256。本轮是partial_source_bundle，不是完整仓库。

LearningUnit.prerequisites必须引用存在的unit；静态调用不等于教学先修。teaching_judgment/model_candidate的边只有人工reviewer非空且approved才可hard=true；当前均pending/soft。base_cost未知为null，不能按0规划；proxy_cost不能称分钟。

LearnerEvidence的unscored、self_report、fixture或independent=false不能更新跳过门控；同用户/概念/item_id重复作答不可重复计独立证据。State.alpha/beta>0，lower_bound未计算为null，不能因此跳过；跨项目须同概念新题确认。

PlanningRequest的快照、任务、单元引用须存在且成本单位一致；成本缺失应在调用层报输入错误，不补0。FEASIBLE须全目标覆盖、硬先修合法、unmet_constraints为空且成本已知<=预算。coverage仅为计划涉及概念，不代表已学会；目标分母0时ratio=null。INFEASIBLE_PROVEN必须proof_path；启发式失败仅NO_FEASIBLE_FOUND；TIMEOUT不算成功。

ExperimentEvent正式实验code/data/config hash必须齐全；开发未提交code_commit可null且留内容hash。started/paused/resumed可exit_code=null；succeeded须0，failed须非零或明确error；未测metrics=null，未计时elapsed_seconds=null。事件保留失败/暂停/恢复；B扩展字段先提请求。

CodeTask总分等于rubric分值之和；评分独立于规划目标。时长预演、评估器实现与人工审核分别标状态。开发题共享rubric不能用于放开终测答案。

Schema检查类型/必填/枚举/范围/格式；本轮验证脚本检查实际文件引用与hash及部分跨对象规则。它不替代未来规划可行性验证器或B独立评分器。

## 字段类型及空值

下表直接对应schema；完整嵌套定义见$defs，所有字段必填。

### RepoSnapshot

| 字段 | 类型与约束 |
|---|---|
| schema_version | `{"const": "1.0.0"}` |
| object_type | `{"const": "RepoSnapshot"}` |
| is_fixture | `{"type": "boolean"}` |
| snapshot_id | `{"type": "string", "minLength": 1}` |
| url | `{"type": "string", "format": "uri"}` |
| commit | `{"type": "string", "pattern": "^[0-9a-f]{40}$"}` |
| license | `{"type": "string", "minLength": 1}` |
| retrieved_at | `{"type": "string", "format": "date-time"}` |
| hash | `{"type": "string", "pattern": "^[0-9a-f]{64}$"}` |
| hash_scope | `{"const": "selected_files_manifest_sha256"}` |
| files | `{"type": "array", "items": {"type": "object", "properties": {"path": {"type": "string", "minLength": 1}, "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}, "bytes": {"type": "integer", "minimum": 0}, "git_blob": {"type": "string", "pattern": "^[0-9a-f]{40}$"}}, "required": ["path", "sha256", "bytes", "git_blob"], "additionalProperties": false}}` |
| license_path | `{"type": "string", "minLength": 1}` |
| snapshot_scope | `{"const": "partial_source_bundle"}` |
| complete_checkout_included | `{"const": false}` |

### LearningUnit

| 字段 | 类型与约束 |
|---|---|
| schema_version | `{"const": "1.0.0"}` |
| object_type | `{"const": "LearningUnit"}` |
| is_fixture | `{"type": "boolean"}` |
| id | `{"type": "string", "minLength": 1}` |
| source_spans | `{"type": "array", "items": {"$ref": "#/$defs/SourceSpan"}}` |
| concept_ids | `{"type": "array", "items": {"type": "string", "minLength": 1}}` |
| prerequisites | `{"type": "array", "items": {"$ref": "#/$defs/Prerequisite"}}` |
| provenance | `{"$ref": "#/$defs/Provenance"}` |
| base_cost | `{"anyOf": [{"type": "number", "minimum": 0}, {"type": "null"}]}` |
| cost_unit | `{"enum": ["proxy_cost"]}` |
| cost_basis | `{"anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]}` |

### LearnerEvidence

| 字段 | 类型与约束 |
|---|---|
| schema_version | `{"const": "1.0.0"}` |
| object_type | `{"const": "LearnerEvidence"}` |
| is_fixture | `{"type": "boolean"}` |
| evidence_id | `{"type": "string", "minLength": 1}` |
| pseudonymous_user_id | `{"type": "string", "minLength": 1}` |
| concept_id | `{"type": "string", "minLength": 1}` |
| item_id | `{"type": "string", "minLength": 1}` |
| outcome | `{"enum": ["pass", "fail", "unscored"]}` |
| timestamp | `{"type": "string", "format": "date-time"}` |
| project | `{"type": "string", "minLength": 1}` |
| evidence_type | `{"enum": ["independent_quiz", "independent_code_task", "self_report", "fixture"]}` |
| attempt_id | `{"type": "string", "minLength": 1}` |
| independent | `{"type": "boolean"}` |

### PlanningRequest

| 字段 | 类型与约束 |
|---|---|
| schema_version | `{"const": "1.0.0"}` |
| object_type | `{"const": "PlanningRequest"}` |
| is_fixture | `{"type": "boolean"}` |
| request_id | `{"type": "string", "minLength": 1}` |
| snapshot_id | `{"type": "string", "minLength": 1}` |
| task_id | `{"type": "string", "minLength": 1}` |
| learner_state | `{"type": "array", "items": {"$ref": "#/$defs/State"}}` |
| budget | `{"type": "number", "minimum": 0}` |
| cost_unit | `{"enum": ["proxy_cost"]}` |
| config_version | `{"type": "string", "minLength": 1}` |
| target_concept_ids | `{"type": "array", "items": {"type": "string", "minLength": 1}}` |
| unit_ids | `{"type": "array", "items": {"type": "string", "minLength": 1}}` |
| prior_plan_id | `{"anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]}` |

### PlanResult

| 字段 | 类型与约束 |
|---|---|
| schema_version | `{"const": "1.0.0"}` |
| object_type | `{"const": "PlanResult"}` |
| is_fixture | `{"type": "boolean"}` |
| plan_id | `{"type": "string", "minLength": 1}` |
| request_id | `{"type": "string", "minLength": 1}` |
| status | `{"enum": ["FEASIBLE", "INFEASIBLE_PROVEN", "NO_FEASIBLE_FOUND", "TIMEOUT"]}` |
| ordered_units | `{"type": "array", "items": {"type": "string", "minLength": 1}}` |
| coverage | `{"type": "object", "properties": {"required_concept_ids": {"type": "array", "items": {"type": "string", "minLength": 1}}, "covered_concept_ids": {"type": "array", "items": {"type": "string", "minLength": 1}}, "ratio": {"anyOf": [{"type": "number", "minimum": 0, "maximum": 1}, {"type": "null"}]}}, "required": ["required_concept_ids", "covered_concept_ids", "ratio"], "additionalProperties": false}` |
| unmet_constraints | `{"type": "array", "items": {"type": "string", "minLength": 1}}` |
| estimated_cost | `{"anyOf": [{"type": "number", "minimum": 0}, {"type": "null"}]}` |
| cost_unit | `{"enum": ["proxy_cost"]}` |
| reason_trace | `{"type": "array", "items": {"type": "object", "properties": {"step": {"type": "integer", "minimum": 0}, "unit_id": {"anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]}, "reason": {"type": "string", "minLength": 1}, "evidence_ids": {"type": "array", "items": {"type": "string", "minLength": 1}}}, "required": ["step", "unit_id", "reason", "evidence_ids"], "additionalProperties": false}}` |
| proof_path | `{"anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]}` |

### ExperimentEvent

| 字段 | 类型与约束 |
|---|---|
| schema_version | `{"const": "1.0.0"}` |
| object_type | `{"const": "ExperimentEvent"}` |
| is_fixture | `{"type": "boolean"}` |
| event_id | `{"type": "string", "minLength": 1}` |
| run_id | `{"type": "string", "minLength": 1}` |
| actor | `{"type": "object", "properties": {"role": {"enum": ["A", "B"]}, "owner": {"type": "string", "minLength": 1}, "executor": {"type": "string", "minLength": 1}, "machine": {"type": "string", "minLength": 1}, "model_id": {"anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]}}, "required": ["role", "owner", "executor", "machine", "model_id"], "additionalProperties": false}` |
| code_commit | `{"anyOf": [{"type": "string", "pattern": "^[0-9a-f]{40}$"}, {"type": "null"}]}` |
| data_hash | `{"anyOf": [{"type": "string", "pattern": "^[0-9a-f]{64}$"}, {"type": "null"}]}` |
| config_hash | `{"anyOf": [{"type": "string", "pattern": "^[0-9a-f]{64}$"}, {"type": "null"}]}` |
| timestamp | `{"type": "string", "format": "date-time"}` |
| event_type | `{"enum": ["started", "succeeded", "failed", "paused", "resumed"]}` |
| payload | `{"type": "object", "properties": {"task_id": {"type": "string", "minLength": 1}, "evidence_type": {"enum": ["development_validation", "real_repository_offline", "human", "synthetic"]}, "command": {"type": "array", "items": {"type": "string", "minLength": 1}}, "exit_code": {"anyOf": [{"type": "integer"}, {"type": "null"}]}, "elapsed_seconds": {"anyOf": [{"type": "number", "minimum": 0}, {"type": "null"}]}, "raw_result_path": {"anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]}, "error": {"anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]}, "resume_from": {"anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]}, "metrics": {"anyOf": [{"type": "object", "properties": {"success": {"anyOf": [{"type": "boolean"}, {"type": "null"}]}, "score": {"anyOf": [{"type": "number", "minimum": 0}, {"type": "null"}]}}, "required": ["success", "score"], "additionalProperties": false}, {"type": "null"}]}}, "required": ["task_id", "evidence_type", "command", "exit_code", "elapsed_seconds", "raw_result_path", "error", "resume_from", "metrics"], "additionalProperties": false}` |

### CodeTask

| 字段 | 类型与约束 |
|---|---|
| schema_version | `{"const": "1.0.0"}` |
| object_type | `{"const": "CodeTask"}` |
| is_fixture | `{"type": "boolean"}` |
| task_id | `{"type": "string", "minLength": 1}` |
| split | `{"enum": ["dev", "test"]}` |
| snapshot_id | `{"type": "string", "minLength": 1}` |
| repo_commit | `{"type": "string", "pattern": "^[0-9a-f]{40}$"}` |
| title | `{"type": "string", "minLength": 1}` |
| task_type | `{"enum": ["local_modification", "locate_explain", "debug"]}` |
| source_spans | `{"type": "array", "items": {"$ref": "#/$defs/SourceSpan"}}` |
| origin | `{"type": "object", "properties": {"kind": {"const": "upstream_todo_adapted"}, "description": {"type": "string", "minLength": 1}, "issue_url": {"anyOf": [{"type": "string", "format": "uri"}, {"type": "null"}]}}, "required": ["kind", "description", "issue_url"], "additionalProperties": false}` |
| goal | `{"type": "string", "minLength": 1}` |
| requirements | `{"type": "array", "items": {"type": "string", "minLength": 1}}` |
| required_concept_ids | `{"type": "array", "items": {"type": "string", "minLength": 1}}` |
| learning_unit_ids | `{"type": "array", "items": {"type": "string", "minLength": 1}}` |
| allowed_context | `{"type": "array", "items": {"type": "string", "minLength": 1}}` |
| prohibited_help | `{"type": "array", "items": {"type": "string", "minLength": 1}}` |
| time_limit_minutes | `{"type": "integer", "minimum": 20, "maximum": 25}` |
| timing_status | `{"const": "design_target_not_piloted"}` |
| difficulty | `{"type": "string", "minLength": 1}` |
| rubric | `{"type": "array", "items": {"$ref": "#/$defs/Rubric"}}` |
| max_score | `{"type": "integer", "minimum": 1}` |
| success_rule | `{"type": "string", "minLength": 1}` |
| submission | `{"type": "array", "items": {"type": "string", "minLength": 1}}` |
| evaluation_owner | `{"const": "B"}` |
| evaluator_status | `{"enum": ["spec_only_not_implemented", "implemented_not_reviewed", "reviewed"]}` |
| review_status | `{"enum": ["pending", "approved"]}` |
| reviewer | `{"anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]}` |
| contribution_preparation | `{"type": "string", "minLength": 1}` |
| answer_access | `{"type": "string", "minLength": 1}` |

## A-D03兼容扩展 1.1.0（开发用）

旧schemas/contracts.schema.json保持1.0.0，不修改B现有加载器。新增schemas/contracts-1.1.schema.json接受旧1.0.0与1.1.0，Task的origin.kind兼容新增source_behavior_adapted/team_designed_debug（新kind必须1.1.0）；用于如实表达B真实行为设计题目，避免错误称upstream TODO。七对象数量/原字段不变。

D03带明确proxy_cost的任务/单元覆盖文件在benchmarks/dev/D03；不回填旧D01空成本以假装早期已冻结。plan_request入口采用扩展schema与真实字节/span校验，见scripts/A/README_D03.md。Beta ledger是内部状态0.1.0，不冒称第八个共享数据对象；B负责持久化迁移与原子性。正式题目/教学边/成本标定未冻结。
