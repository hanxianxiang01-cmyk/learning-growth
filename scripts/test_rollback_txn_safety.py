#!/usr/bin/env python3
"""BUG-1456 事务安全回归（PR#100 合并前两项强制检查）。

环境约束如实说明：账号无 CREATE DATABASE 权限 → 采用 h_db 实例内**独立测试
schema** `bug1456_test`（最小表结构拷贝：resource_version/task_instance/
mastery_evidence 三张，零生产数据），通过 `search_path` 把被测脚本限定在
测试 schema 内，测毕 DROP SCHEMA CASCADE。生产 schema public 全程零触碰。

检查一【DRY 零写入】：对含 可回退/引用保护/幂等跳过 三态 fixture 的测试库跑
  rollback DRY → 前后全表 (count, md5 内容哈希, 状态分布) **完全一致**。
检查二【异常原子性】：--apply --inject-error-test（第 2 条写前抛异常）→
  全部数据回到执行前（无部分删除/部分恢复）。
附加【正向 apply】：确认真写路径工作正常（可回退项生效、保护项不动）。
"""
import hashlib
import json
import os
import subprocess
import sys
import uuid

import psycopg

URL = os.environ["DATABASE_URL"].replace("+psycopg", "")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = "bug1456_test"

OLD1 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "rb-old1"))   # superseded + 新版无引用 → 可回退
NEW1 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "rb-new1"))
OLD2 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "rb-old2"))   # superseded + 新版被 task 引用 → 保护
NEW2 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "rb-new2"))
OLD3 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "rb-old3"))   # published → 幂等跳过
NEW3 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "rb-new3"))
OLD4 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "rb-old4"))   # superseded + 无引用（异常测试第二可回退项）
NEW4 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "rb-new4"))

MANIFEST = {"applied": True, "items": [
    {"old_rvid": OLD1, "new_rvid": NEW1, "kind": "axis_max_fix", "new_version_no": 2},
    {"old_rvid": OLD2, "new_rvid": NEW2, "kind": "shape_name_neutralize", "new_version_no": 2},
    {"old_rvid": OLD3, "new_rvid": NEW3, "kind": "axis_max_fix", "new_version_no": 2},
    {"old_rvid": OLD4, "new_rvid": NEW4, "kind": "shape_name_neutralize", "new_version_no": 2},
]}


def setup_schema(c):
    c.execute(f"drop schema if exists {SCHEMA} cascade")
    c.execute(f"create schema {SCHEMA}")
    c.execute(f"""create table {SCHEMA}.resource_version(
        resource_version_id uuid primary key, review_status text not null)""")
    c.execute(f"""create table {SCHEMA}.task_instance(
        task_instance_id uuid primary key, resource_version_id uuid)""")
    c.execute(f"""create table {SCHEMA}.mastery_evidence(
        evidence_id uuid primary key, task_instance_id uuid)""")
    ins = f"insert into {SCHEMA}.resource_version values (%s,%s)"
    c.execute(ins, (OLD1, "superseded")); c.execute(ins, (NEW1, "published"))
    c.execute(ins, (OLD2, "superseded")); c.execute(ins, (NEW2, "published"))
    c.execute(ins, (OLD3, "published"));  c.execute(ins, (NEW3, "published"))
    c.execute(ins, (OLD4, "superseded")); c.execute(ins, (NEW4, "published"))
    c.execute(f"insert into {SCHEMA}.task_instance values (%s,%s)",
              (str(uuid.uuid4()), NEW2))  # NEW2 被任务引用 → 保护
    c.commit()


def snapshot(c):
    h = {}
    for t in ("resource_version", "task_instance", "mastery_evidence"):
        rows = c.execute(
            f"select * from {SCHEMA}.{t} order by 1").fetchall()
        blob = json.dumps([list(map(str, r)) for r in rows])
        h[t] = (len(rows), hashlib.md5(blob.encode()).hexdigest())
    return h


def run_script(env_extra, args):
    env = dict(os.environ)
    env.update(env_extra)
    r = subprocess.run([sys.executable,
                        os.path.join(REPO, "scripts", "rollback_content_fixes.py")] + args,
                       capture_output=True, text=True, env=env)
    return r


def main():
    outdir = "/tmp/rb1456"
    os.makedirs(os.path.join(outdir, "q4_reva_devfix"), exist_ok=True)
    with open(os.path.join(outdir, "q4_reva_devfix", "fix_manifest.json"), "w") as f:
        json.dump(MANIFEST, f)
    test_url = URL.split("?")[0].rstrip("/") + f"?options=-c%20search_path%3D{SCHEMA}"
    env = {"DATABASE_URL": test_url, "R2_OUT": outdir, "RB_SCHEMA": SCHEMA}

    with psycopg.connect(URL) as c:
        setup_schema(c)
        results = {}

        # ---- 检查一：DRY 零写入 ----
        before = snapshot(c)
        r = run_script(env, [])
        after = snapshot(c)
        results["check1_dry_zero_write"] = {
            "identical": before == after, "rc": r.returncode, "stdout_tail": r.stdout[-200:]}

        # ---- 检查二：apply 中途异常 → 整体原子回滚 ----
        before2 = snapshot(c)
        r2 = run_script(env, ["--apply", "--inject-error-test"])
        after2 = snapshot(c)
        results["check2_exception_atomicity"] = {
            "rolled_back_identical": before2 == after2, "script_raised": r2.returncode != 0,
            "rc": r2.returncode, "stderr_tail": r2.stderr[-150:]}

        # ---- 附加：正向 apply（OLD1/OLD4 应回退；OLD2 保护；OLD3 幂等）----
        r3 = run_script(env, ["--apply"])
        state = dict(c.execute(f"select resource_version_id::text, review_status "
                               f"from {SCHEMA}.resource_version").fetchall())
        results["check3_apply_semantics"] = {
            "rc": r3.returncode,
            "old1_published": state.get(OLD1) == "published",
            "old4_published": state.get(OLD4) == "published",
            "old2_still_superseded": state.get(OLD2) == "superseded",
            "new2_not_deleted": NEW2 in state, "new1_deleted": NEW1 not in state,
            "new3_untouched": state.get(NEW3) == "published", "stdout_tail": r3.stdout[-200:]}

        c.execute(f"drop schema if exists {SCHEMA} cascade")
        c.commit()
        # 生产 schema 完整性哨兵（测试库删除后主数据未受任何影响）
        pub = c.execute("select count(*) from resource_version where review_status='published'").fetchone()[0]
        results["production_published_after"] = pub

    ok = (results["check1_dry_zero_write"]["identical"]
          and results["check2_exception_atomicity"]["rolled_back_identical"]
          and results["check2_exception_atomicity"]["script_raised"]
          and all(v for k, v in results["check3_apply_semantics"].items() if isinstance(v, bool))
          and pub == 224)
    print(json.dumps(results, ensure_ascii=False, indent=1))
    print("OVERALL:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
