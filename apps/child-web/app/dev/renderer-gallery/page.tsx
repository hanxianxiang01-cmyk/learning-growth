"use client";

/**
 * DEV ONLY：19 类 Release Renderer 的视觉复核台（FE-1445 复审）。
 *
 * 为什么要这么一个页面：迁移后要看的是「19 类渲染器在真实题目下还画得对不对」，
 * 靠逐页点进去碰运气既不可复现、也覆盖不全。这里把每类渲染器各放一张真实题目
 * （样本由 scripts/iqc/v6_review/dump_renderer_fixtures.py 从生产题库只读导出），
 * 同一套样本 × 两套皮肤顺序渲染，截图与结构断言都由脚本完成。
 *
 * 题目内容**不写进仓库**：页面从 `window.__GALLERY_FIXTURES__` 读，
 * 由采集脚本在浏览器启动时注入。仓库里只有这个通用渲染架子。
 *
 * 用法：/dev/renderer-gallery?skin=exploration-lab|healing
 */
import { useEffect, useState } from "react";
import { ChildSkinProvider } from "@/src/theme/ChildSkinProvider";
import { TaskRenderer, createEmptyTaskResponse } from "@/src/features/task-renderer";
import type { TaskInstance, TaskResponse } from "@/src/lib/api/contracts";

type Fixture = {
  renderer: string;
  resource_version_id: string;
  difficulty?: number;
  goal?: string;
  ui_schema: unknown;
};

declare global {
  interface Window {
    __GALLERY_FIXTURES__?: Fixture[];
  }
}

function Case({ item }: { item: Fixture }) {
  const task = {
    task_instance_id: `gallery-${item.renderer}`,
    ability_id: "gallery",
    difficulty: item.difficulty ?? 2,
    goal: item.goal ?? item.renderer,
    strategy_policy: {},
    resource_version_id: item.resource_version_id,
    ui_schema: item.ui_schema
  } as TaskInstance;
  const [response, setResponse] = useState<TaskResponse>(() => createEmptyTaskResponse());

  return (
    <section
      data-gallery-renderer={item.renderer}
      style={{ border: "1px solid #d8d8d8", borderRadius: 12, margin: "0 0 24px", padding: 16, background: "#fff" }}
    >
      <header style={{ display: "flex", gap: 12, alignItems: "baseline", marginBottom: 12 }}>
        <strong data-gallery-title style={{ fontSize: 14 }}>{item.renderer}</strong>
        <code style={{ fontSize: 11, color: "#666" }}>{item.resource_version_id}</code>
      </header>
      <div data-gallery-canvas={item.renderer}>
        <TaskRenderer
          task={task}
          response={response}
          disabled={false}
          hintAction={null}
          onResponseChange={setResponse}
          onSubmit={() => {}}
        />
      </div>
    </section>
  );
}

export default function Page() {
  const [fixtures, setFixtures] = useState<Fixture[] | null>(null);
  const [skin, setSkin] = useState<"exploration-lab" | "healing">("exploration-lab");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setSkin(params.get("skin") === "healing" ? "healing" : "exploration-lab");
    setFixtures(window.__GALLERY_FIXTURES__ ?? null);
  }, []);

  return (
    <ChildSkinProvider skin={skin} uiVersion="v6">
      <div data-gallery-root data-gallery-skin={skin} style={{ width: 1180, margin: "0 auto", padding: 24, background: "#f4f6f7" }}>
        <h1 style={{ fontSize: 18, margin: "0 0 4px" }}>Renderer 视觉复核台</h1>
        <p data-gallery-count style={{ fontSize: 12, color: "#555", margin: "0 0 20px" }}>
          {fixtures ? `${fixtures.length} 个渲染器 · 皮肤 ${skin}` : "等待注入样本…"}
        </p>
        {fixtures === null ? (
          <p style={{ fontSize: 13 }}>未注入样本：请用 scripts/iqc/v6_review/renderer_visual.mjs 打开本页。</p>
        ) : (
          fixtures.map(item => <Case key={item.renderer} item={item} />)
        )}
      </div>
    </ChildSkinProvider>
  );
}
