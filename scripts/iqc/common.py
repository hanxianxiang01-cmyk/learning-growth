#!/usr/bin/env python3
"""IQC 共享接口层（FE-1460/1462 开工裁决 §一）：
- 唯一题库发现入口 = FE-1459 inventory manifest（本模块只消费，不再各自发现）
- Finding 十字段契约 = rules.json iqc.output_schema（单一真相源引用）
- 资源全量 JSON 按 manifest rvid 清单只读加载（SELECT by id，无枚举逻辑）
"""
import hashlib, json, pathlib, sys
import psycopg

RULES = json.load(open(pathlib.Path.home() / ".workbuddy/skills/math-prototype-review/rules.json"))
FINDING_REQUIRED = RULES["iqc"]["output_schema"]["finding"]["required"]
RULES_VERSION = RULES["version"] + "/" + RULES["iqc"]["mode"]

def load_manifest(path):
    m = json.load(open(path))
    return m

def load_items(db, rvids, batch=100):
    """按 manifest 的 rvid 清单只读拉全量字段（发现逻辑不在这里）。"""
    out = {}
    with psycopg.connect(db) as c:
        for i in range(0, len(rvids), batch):
            chunk = rvids[i:i+batch]
            rows = c.execute("""select rv.resource_version_id::text, rv.resource_id::text,
                rv.version_no, rv.review_status, rv.difficulty, rv.task_type,
                r.ability_id, rv.content::text, rv.ui_schema::text,
                rv.error_models::text, rv.hint_policy::text, rv.mastery_rule::text,
                rv.transfer_distance
                from resource_version rv join resource r using(resource_id)
                where rv.resource_version_id = any(%s)""", ([__import__("uuid").UUID(x) for x in chunk],)).fetchall()
            for row in rows:
                out[row[0]] = {"resource_version_id": row[0], "resource_id": row[1],
                    "version_no": row[2], "review_status": row[3], "difficulty": row[4],
                    "task_type": row[5], "ability_id": row[6],
                    "content": json.loads(row[7] or "{}"), "ui_schema": json.loads(row[8] or "{}"),
                    "error_models": json.loads(row[9] or "null"), "hint_policy": json.loads(row[10] or "null"),
                    "mastery_rule": json.loads(row[11] or "null"), "transfer_distance": row[12]}
    return out

def audit_input_sha(item):
    """检查点2 同口径单题审计哈希（九域规范化）。"""
    ui = item["ui_schema"]
    return hashlib.sha256(json.dumps({
        "ui_schema": ui, "content": item["content"], "error_models": item["error_models"],
        "hint_policy": item["hint_policy"], "mastery_rule": item["mastery_rule"],
        "ability_id": item["ability_id"], "difficulty": item["difficulty"],
        "version_no": item["version_no"], "review_status": item["review_status"],
        "response_axis": ui.get("response_contract") or ui.get("response_schema")},
        ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()

def finding(rvid, rule_id, severity, status, evidence_pointer, field_path,
            suggestion, regression_required, run_id, snapshot_sha256):
    """十字段 Finding 构造器（缺字段=编程错误，直接 assert）。"""
    f = {"rvid": rvid, "rule_id": rule_id, "severity": severity, "status": status,
         "evidence_pointer": evidence_pointer, "field_path": field_path,
         "suggestion": suggestion, "regression_required": regression_required,
         "run_id": run_id, "snapshot_sha256": snapshot_sha256,
         "rules_version": RULES_VERSION}
    assert all(k in f for k in FINDING_REQUIRED), "Finding 十字段不齐"
    return f
