# Frozen Baselines

该目录保存**不可原地修改**的冻结研发基线。

当前收录：

```text
learning-core-v1.3.1/
```

规则：

1. 已冻结目录禁止直接改写。
2. 基线修订必须创建新目录，例如 `learning-core-v1.3.2/`。
3. 每个冻结版本必须包含 `SHA256SUMS`。
4. `openapi / schema / backlog / ADR` 的冻结版本必须保持彼此对应。
5. 应用代码可以领先于冻结基线，但所有差异必须登记到：
   `docs/governance/CONTRACT_DRIFT_REGISTER.md`。

这能避免两个工作者把“当前实现”“冻结规范”“临时接口约定”混成同一真相源。
