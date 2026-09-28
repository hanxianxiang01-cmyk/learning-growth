# ADR-0001 — DeepTutor External Extension SPI Gate (V1.3.1)

Status: Proposed / Gate Pending  
Date: 2026-09-24

## Context
The target architecture requires Learning Engine education logic to remain outside DeepTutor Core.
DeepTutor public architecture exposes Tool/Capability registries and protocols, and the project has publicly discussed Python entry-point loading for external Tools and Capabilities.
However, this project has not yet proven the exact combination we need: external package discovery, Capability→Tool invocation, target runtime entry points, restart/uninstall behavior, and failure isolation.

References:
- https://github.com/HKUDS/DeepTutor/blob/main/AGENTS.md
- https://github.com/HKUDS/DeepTutor/blob/main/deeptutor/api/main.py
- https://github.com/HKUDS/DeepTutor/issues/1307

## Decision
`DeepTutor Core Patch = 0` is an architecture target until E0-01 passes.
E3 Agent Integration MUST NOT start while this Gate is unresolved.

## Spike package
Create an independent package outside the DeepTutor repository containing:
- one minimal external Tool;
- one minimal external Capability;
- package metadata / entry points;
- one intentionally failing plugin for isolation testing.

## Acceptance criteria
1. Install via wheel.
2. Install via editable mode.
3. Runtime discovers external Tool.
4. Runtime discovers external Capability.
5. Capability invokes external Tool.
6. Required production entry points work.
7. Restart preserves discovery.
8. Uninstall removes the extension cleanly.
9. A broken plugin does not make the whole DeepTutor runtime unavailable.
10. `git diff <pinned-baseline>` confirms DeepTutor Core source patch = 0.

## Decision branches
- PASS: Core Patch=0 becomes a hard architectural constraint.
- PARTIAL: prefer Tool/MCP/Adapter seam; do not patch Core just to preserve a custom Capability abstraction.
- FAIL: block E3 and create a replacement ADR for API/MCP/sidecar integration.

## Evidence to retain
- pinned DeepTutor commit/tag;
- install logs;
- plugin discovery logs;
- runtime invocation logs;
- failure-isolation logs;
- git diff output;
- ADR conclusion.
