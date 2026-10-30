#!/usr/bin/env python3
"""FE-1469 builder Dry Run 零写入证明测试（PR#119 合并前置，裁决 §二.1）。

方法（测试库隔离，不碰生产 public）：
1 建临时 schema iqc_dry_proof，克隆 resource/resource_version（含数据）；
2 快照：两张表全行内容哈希（md5 聚合）+ 记录数 + 状态分布；
3 以 search_path 指向该 schema 运行 build_b6_alternatives（无 --apply=Dry）；
4 重算快照对比：哈希/行数/状态全部不变 = Dry 零写入证明；
5 --apply 对照（同 schema）：行数增加且新行为 qa_staged = 写路径确实生效；
6 清理 schema。
"""
import hashlib
import os
import subprocess
import sys

import psycopg

DB = (os.environ.get("IQC_MIGRATE_DB")
      or sys.exit("缺 IQC_MIGRATE_DB（测试需建临时 schema）"))
SCHEMA = "iqc_dry_proof"


def tables_hash(conn):
    agg = []
    for t in ("resource", "resource_version"):
        rows = conn.execute(
            f"select md5(string_agg(row_data, '|' order by a)) from "
            f"(select {t}::text as row_data, 1 as a from {SCHEMA}.{t}) x").fetchone()[0]
        n = conn.execute(f"select count(*) from {SCHEMA}.{t}").fetchone()[0]
        agg.append((t, rows, n))
    return agg


def main():
    uri = DB + ("&" if "?" in DB else "?") + f"options=-csearch_path%3D{SCHEMA}"
    with psycopg.connect(DB, autocommit=True) as c:
        c.execute(f"drop schema if exists {SCHEMA} cascade")
        c.execute(f"create schema {SCHEMA}")
        for t in ("resource", "resource_version"):
            c.execute(f"create table {SCHEMA}.{t} (like public.{t} including all)")
        # 只灌本裁决涉及的行（B6 相关 + 两道原题），控制测试规模
        c.execute(f"""insert into {SCHEMA}.resource select * from public.resource
            where title like 'B6-ALT%%' or resource_id in
            (select resource_id from public.resource_version where resource_version_id::text
             in ('2c46c271-1a2f-4f45-ad3c-b5719ad58ded','845c6fea-418f-4365-a25e-b50e5b5040f8'))""")
        c.execute(f"""insert into {SCHEMA}.resource_version select * from public.resource_version
            where resource_id in (select resource_id from {SCHEMA}.resource)""")
        # 关键：清掉 B6-ALT 行，让 Dry 真正走"计划分支"、apply 真正建行
        c.execute(f"""delete from {SCHEMA}.resource_version where resource_id in
            (select resource_id from {SCHEMA}.resource where title like 'B6-ALT%%')""")
        c.execute(f"delete from {SCHEMA}.resource where title like 'B6-ALT%%'")
    with psycopg.connect(uri) as c:
        before = tables_hash(c)
    env = dict(os.environ, DATABASE_URL="", IQC_MIGRATE_DB=uri,
           PYTHONPATH=os.path.abspath('scripts'))
    r = subprocess.run([sys.executable, "scripts/iqc/rt1464/build_b6_alternatives.py"],
                       capture_output=True, text=True, env=env)
    dry_out = r.stdout + r.stderr
    if r.returncode != 0: print("DRY subprocess rc", r.returncode, r.stderr[-400:])
    with psycopg.connect(uri) as c:
        after = tables_hash(c)
    planned = "DRY 计划" in dry_out
    dry_ok = before == after and planned
    print("Dry stdout 计划分支:", planned, "| 哈希不变:", before == after)
    # 对照：--apply 应写入（证明确实测得到写路径，防假阴）
    r2 = subprocess.run([sys.executable, "scripts/iqc/rt1464/build_b6_alternatives.py", "--apply"],
                        capture_output=True, text=True, env=env)
    if r2.returncode != 0: print("APPLY subprocess rc", r2.returncode, r2.stderr[-400:])
    with psycopg.connect(uri) as c:
        post = tables_hash(c)
        staged = c.execute(f"select count(*) from {SCHEMA}.resource_version where review_status='qa_staged'").fetchone()[0]
    apply_ok = post != before and staged == 2  # 两题各新建 1 行 qa_staged
    print("证明2 --apply 写入生效（对照）:", "PASS" if apply_ok else "FAIL",
          f"qa_staged={staged}")
    with psycopg.connect(DB, autocommit=True) as c:
        c.execute(f"drop schema if exists {SCHEMA} cascade")
    print("临时 schema 已清理")
    ok = dry_ok and apply_ok
    print("DRY-ZERO-WRITE-PROOF:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
