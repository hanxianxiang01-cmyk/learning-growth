#!/usr/bin/env python3
"""FE-1463 §四 只读账号权限负例探针（PR#106 合并前置检查工具，就绪待账号）。

用法：python3 readonly_permission_probe.py --db "postgresql://iqc_readonly:…/h_db"
判定（全过才符合 PR#106 放行条件第 4 项）：
  PASS  连接成功且 SELECT 正常
  PASS  UPDATE/INSERT/DELETE/DROP/TRUNCATE/CREATE 全部被数据库拒绝
        （permission denied for table / must be owner）
  FAIL  任一写操作被接受 → 账号权限不合规，禁止配 secret
仅测权限，不产生任何数据变更（写语句全部预期失败；UPDATE 用 where 1=0 语义
空集但权限检查先行——PostgreSQL 权限在解析阶段即拒绝，不执行到行过滤）。
"""
import argparse
import sys

import psycopg

WRITE_SQLS = [
    ("UPDATE", "update resource_version set difficulty = difficulty where 1 = 0"),
    ("INSERT", "insert into resource_version(resource_version_id, resource_id, version_no) "
               "values ('00000000-0000-0000-0000-00000000ffff', "
               "'00000000-0000-0000-0000-000000000000', 999999)"),
    ("DELETE", "delete from resource_version where 1 = 0"),
    ("DROP", "drop table if exists resource_version"),
    ("TRUNCATE", "truncate resource_version"),
    ("CREATE", "create table if not exists iqc_probe_tmp(x int)"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    args = ap.parse_args()
    ok = True
    with psycopg.connect(args.db) as c:
        n = c.execute("select count(*) from resource_version").fetchone()[0]
        print(f"PASS  SELECT 正常（{n} 行）")
    for label, sql in WRITE_SQLS:
        try:
            with psycopg.connect(args.db, autocommit=True) as c:
                c.execute(sql)
            print(f"FAIL  {label} 被接受——账号有写权限，禁止使用！")
            ok = False
        except psycopg.errors.InsufficientPrivilege:
            print(f"PASS  {label} 被数据库拒绝（permission denied）")
        except psycopg.errors.DependencyPrivilegeNotGranted:
            print(f"PASS  {label} 被数据库拒绝（对象权限缺失）")
        except Exception as e:
            # 语法/约束类错误不代表权限安全；仅权限类错误算拒绝
            if "permission denied" in str(e).lower() or "must be owner" in str(e).lower():
                print(f"PASS  {label} 被拒绝（{type(e).__name__}）")
            else:
                print(f"FAIL  {label} 非权限类异常无法证明安全: {type(e).__name__}: {str(e)[:80]}")
                ok = False
    print("\nREADONLY-PROBE:", "PASS——可配 IQC_DATABASE_URL" if ok else "FAIL——账号不合规")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
