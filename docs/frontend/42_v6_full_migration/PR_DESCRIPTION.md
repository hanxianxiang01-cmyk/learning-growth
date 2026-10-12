# FE-1443-FULL · PR交接草稿（未创建、未合并）

范围：V6双皮肤全量页面与19个生产V2 Renderer，原接口与数学契约保留；应用默认V6，支持显式legacy回滚。详情见MIGRATION.md、TEST_REPORT.md与根目录README_V6_FULL.md。

已执行的隔离/静态检查通过；锁定工具链typecheck/build、真实Next浏览器、后端与数据库验收未完成。不要将本PR标记为DONE，直到这些条件在有依赖的环境完成、人工视觉复核结束且PR合并。

补丁必须以用户原ZIP对应Git基线应用，不能盲目覆盖开发人员已有的其他改动。请先`git apply --check`；发生冲突按文件合并。package-lock、应用版本、后端及数学纯模块的未改动证据附在evidence中。
