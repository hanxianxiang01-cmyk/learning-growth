#!/usr/bin/env python3
"""OpenAPI 契约校验 —— 验证错误码分层没有漂移。

依据冻结基线 V1.3.1：
- 系统错误码（HTTP 4xx/5xx error.code）只允许 LE-4001/4091/4221/4291/5001 + AG-5031。
- 教育诊断码 E01~E07 只能出现在 HTTP 2xx 业务载荷的 diagnosis.code，不得进 error.code。
- LE-004 等历史漂移码一律禁止。

退出码：0 = 通过；1 = 发现漂移。
"""
import sys
import yaml

ALLOWED_SYSTEM_CODES = {"LE-4001", "LE-4091", "LE-4221", "LE-4291", "LE-5001", "AG-5031"}
ALLOWED_DIAGNOSIS_CODES = {f"E0{i}" for i in range(1, 8)}  # E01~E07


def main(path: str) -> int:
    with open(path, encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    failures: list[str] = []

    # 1. 校验 ErrorResponse schema 的 code 枚举
    error_enum = spec["components"]["schemas"]["ErrorResponse"]["properties"]["error"]["properties"]["code"]["enum"]
    if set(error_enum) != ALLOWED_SYSTEM_CODES:
        failures.append(f"ErrorResponse.code 枚举漂移: {error_enum}")

    # 2. 校验 DiagnosisResult schema 的 code 枚举
    diag_enum = spec["components"]["schemas"]["DiagnosisResult"]["properties"]["code"]["enum"]
    if set(diag_enum) != ALLOWED_DIAGNOSIS_CODES:
        failures.append(f"DiagnosisResult.code 枚举漂移: {diag_enum}")

    # 3. 扫描所有响应 example，确认 error.code 都在系统码内
    for route, ops in spec["paths"].items():
        for method, op in ops.items():
            for status, resp in op.get("responses", {}).items():
                if not status.startswith("2"):
                    content = resp.get("content", {})
                    example = (
                        content.get("application/json", {}).get("example", {})
                        if isinstance(content, dict)
                        else {}
                    )
                    code = example.get("error", {}).get("code")
                    if code and code not in ALLOWED_SYSTEM_CODES:
                        failures.append(f"{route} {status} 错误码漂移: {code}")

    # 4. 检查全文是否出现禁止的历史漂移码
    raw = open(path, encoding="utf-8").read()
    for forbidden in ("LE-004",):
        if forbidden in raw:
            failures.append(f"发现禁止的历史漂移码: {forbidden}")

    if failures:
        print("FAIL: OpenAPI 契约校验未通过")
        for f in failures:
            print("  -", f)
        return 1

    print("PASS: OpenAPI 契约校验通过（错误码分层无漂移）")
    print(f"  - 系统错误码: {sorted(ALLOWED_SYSTEM_CODES)}")
    print(f"  - 教育诊断码: {sorted(ALLOWED_DIAGNOSIS_CODES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "openapi.yaml"))