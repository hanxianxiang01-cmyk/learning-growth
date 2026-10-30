"""DDL ↔ ORM 双向对账（游客模式 4 张表）。

为什么需要它：增量 DDL 与 SQLAlchemy 模型是两份独立手写的定义。字段名拼错、
漏列、可空性不一致，在**没有连接数据库时完全不会报错**，只会在建表那一刻
或运行期第一个 null 约束违规时暴露。本脚本把这件事变成可复跑的门禁。

判据（全部绝对断言）：
  A. DDL 表集合 == ORM 表集合（双向，防多写/漏写）
  B. 每张表列名集合完全相等
  C. 每张表 PRIMARY KEY 列集合完全相等
  D. 每列可空性一致（DDL NOT NULL vs ORM nullable）
  E. 术语：PRIMARY KEY 隐含 NOT NULL（Postgres 语义），判据按真实语义算，
     否则三张表的主键列会被集体误报 —— 这是判据自身的 bug，不是代码 bug。

退出码：0 = 全对齐；1 = 判据失败；2 = 环境/文件/导入问题（不算判据失败）。

用法：
    ~/.workbuddy/binaries/python/envs/learning-engine/bin/python scripts/iqc/guest_mode/audit_ddl_orm.py
变异验证（指向被改坏的副本，证明判据真会红）：
    IQC_DDL_PATH=/tmp/mutants/m1.sql python scripts/iqc/guest_mode/audit_ddl_orm.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
API = REPO / "apps" / "learning-api"
SQL_PATH = Path(
    os.environ.get("IQC_DDL_PATH") or (API / "migrations" / "sql" / "2026_guest_mode.sql")
)


def parse_ddl(text: str) -> dict[str, dict]:
    """从 DDL 抽取 {table: {columns: {name: (type, not_null)}, pk: [...]}}。"""
    text = re.sub(r"--[^\n]*", "", text)  # 剥行注释，防注释里的逗号/括号干扰
    tables: dict[str, dict] = {}
    for m in re.finditer(r"CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\((.*?)\n\);", text, re.S):
        name, body = m.group(1), m.group(2)
        cols: dict[str, tuple[str, bool]] = {}
        pk_inline: list[str] = []
        pk_table: list[str] = []
        for raw in body.split("\n"):
            line = raw.strip().rstrip(",")
            if not line or line.upper().startswith("CONSTRAINT"):
                continue
            if re.match(r"(?i)^PRIMARY\s+KEY\s*\(", line):
                inner = re.search(r"\((.*?)\)", line).group(1)
                pk_table = [c.strip() for c in inner.split(",")]
                continue
            fm = re.match(r"^(\w+)\s+([A-Za-z][\w ()]*)", line)
            if not fm:
                continue
            cname = fm.group(1)
            rest = fm.group(2).upper()
            cols[cname] = (rest.split()[0] if rest.split() else "", "NOT NULL" in rest)
            if "PRIMARY KEY" in rest:
                pk_inline.append(cname)
        tables[name] = {"columns": cols, "pk": sorted(pk_inline or pk_table)}
        # Postgres：PRIMARY KEY 隐含 NOT NULL。按真实语义补齐，否则主键列集体误报。
        for cname in tables[name]["pk"]:
            if cname in cols:
                ctype, _ = cols[cname]
                cols[cname] = (ctype, True)
    return tables


def parse_orm() -> dict[str, dict]:
    """以 SQLAlchemy 元数据为准抽 ORM 表结构（不是读源码文本）。"""
    sys.path.insert(0, str(API))
    import importlib

    # 只导入 guest 模块，避开 app.models.__init__ 可能触发的重依赖
    mod = importlib.import_module("app.models.guest")
    out: dict[str, dict] = {}
    for attr in dir(mod):
        tbl = getattr(getattr(mod, attr), "__table__", None)
        if tbl is None:
            continue
        out[tbl.name] = {
            "columns": {c.name: (str(c.type), not c.nullable) for c in tbl.columns},
            "pk": sorted(c.name for c in tbl.primary_key.columns),
        }
    return out


def main() -> int:
    if not SQL_PATH.exists():
        print(f"[rc=2] 找不到 DDL：{SQL_PATH}")
        return 2
    ddl = parse_ddl(SQL_PATH.read_text(encoding="utf-8"))
    try:
        orm = parse_orm()
    except Exception as e:  # 环境/导入问题一律 rc=2
        print(f"[rc=2] ORM 导入失败（环境问题，非判据失败）：{type(e).__name__}: {e}")
        return 2

    print(f"DDL：{SQL_PATH}")
    print(f"DDL 表 {sorted(ddl)}")
    print(f"ORM 表 {sorted(orm)}")
    print("=" * 68)

    fails: list[str] = []
    only_ddl = sorted(set(ddl) - set(orm))
    only_orm = sorted(set(orm) - set(ddl))
    if only_ddl:
        fails.append(f"A 仅 DDL 有：{only_ddl}")
    if only_orm:
        fails.append(f"A 仅 ORM 有：{only_orm}")
    print(f"A 表集合双向：{'PASS' if not only_ddl and not only_orm else 'FAIL'}")

    for t in sorted(set(ddl) & set(orm)):
        d, o = ddl[t], orm[t]
        dcols, ocols = set(d["columns"]), set(o["columns"])

        miss, extra = sorted(dcols - ocols), sorted(ocols - dcols)
        ok_b = not miss and not extra
        if not ok_b:
            fails.append(f"B {t} 列不齐：DDL独有={miss} ORM独有={extra}")
        print(f"B {t:<20} 列集合({len(dcols)} vs {len(ocols)})：{'PASS' if ok_b else 'FAIL'}")

        ok_c = d["pk"] == o["pk"]
        if not ok_c:
            fails.append(f"C {t} 主键不同：DDL={d['pk']} ORM={o['pk']}")
        print(f"C {t:<20} 主键 {d['pk']}：{'PASS' if ok_c else 'FAIL'}")

        bad = [
            f"{c}(DDL NOT NULL={d['columns'][c][1]} / ORM nullable={not o['columns'][c][1]})"
            for c in sorted(dcols & ocols)
            if d["columns"][c][1] != o["columns"][c][1]
        ]
        if bad:
            fails.append(f"D {t} 可空性不一致：{bad}")
        print(f"D {t:<20} 可空性：{'PASS' if not bad else 'FAIL'}")

    print("=" * 68)
    if fails:
        print(f"结论：FAIL（{len(fails)} 项）")
        for f in fails:
            print("  - " + f)
        return 1
    print("结论：PASS（DDL 与 ORM 完全对齐）")
    return 0


if __name__ == "__main__":
    sys.exit(main())