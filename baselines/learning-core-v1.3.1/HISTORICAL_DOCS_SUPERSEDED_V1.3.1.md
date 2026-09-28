# Historical Design Documents — Superseded by Freeze Baseline V1.3.1

Status: APPROVED FOR ARCHIVE  
Effective: 2026-09-28

The documents below remain available only as design-history/background material.
They MUST NOT be used as implementation SSOT for:
- database entity/field names;
- HTTP/API contracts;
- system error codes;
- Mastery weights or evidence gates;
- DeepTutor extension/Core-patch decisions;
- Sprint totals or release gates.

## Superseded documents
- `儿童学习成长系统_V2.0_设计说明书.docx`
- `儿童学习成长系统_V2.0_详细设计说明书.docx`
- `儿童学习成长系统_V2.0_研发详细设计说明书.docx`
- `儿童学习成长系统_V2.0_工程设计文档.docx`
- `儿童学习成长系统_V2.0_开发规格说明书.docx`
- `儿童学习成长系统_V2.0_开发实施设计包.docx`
- `儿童学习成长系统_V2.0_研发执行设计包/00_儿童学习成长系统_V2.0_研发执行设计说明书.docx`
- `儿童学习成长系统_V2.0_研发进场冻结基线_V1.0.docx`
- `儿童学习成长系统_V2.0_冻结基线_V1.1同步包/儿童学习成长系统_V2.0_研发进场冻结基线_V1.1.docx`
- `儿童学习成长系统_V2.0_冻结基线_V1.2同步包/儿童学习成长系统_V2.0_研发进场冻结基线_V1.2.docx`
- `儿童学习成长系统_V2.0_冻结基线_V1.3同步包/儿童学习成长系统_V2.0_研发进场冻结基线_V1.3.docx`

## Current SSOT
- Database: `01_schema_postgresql_v1.3.1.sql`
- API: `02_openapi_v1.3.1.yaml`
- Freeze rules / gates: `儿童学习成长系统_V2.0_研发进场冻结基线_V1.3.1.docx`
- DeepTutor SPI architecture decision: `ADR-0001_DeepTutor_SPI_Gate_V1.3.1.md`
- Delivery backlog: `05_Sprint_Backlog_v1.3.1.xlsx`

## Naming ruling
Historical names such as `Child`, `Ability_State`, `Learning Event`, `Learner Model` are domain-language labels only.
Implementation names are the snake_case identifiers defined in the V1.3.1 DDL.
