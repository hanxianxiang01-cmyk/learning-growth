"use client";

import { ChildSkinProvider } from "@/src/theme/ChildSkinProvider";
import {
  AbilityBadge,
  AbilityGrowthCard,
  AbilityMap,
  AnswerComposer,
  CoachPanel,
  CompletionHero,
  GrowthEntryCard,
  LearningBehaviorChecklist,
  ManipulativeToolbar,
  MathQuestionCard,
  MathTaskCard,
  MathWorkspace,
  NextTaskCard,
  PrimaryButton,
  ProgressDots,
  SessionStats,
  SurfaceCard,
  TodayGoalCard
} from "@/src/components";

const abilities = [
  { ability_id: "REL", name: "数量关系", level: 2, confidence: 0.72, evidence_count: 6, trend: "up" as const },
  { ability_id: "STRAT", name: "数学策略", level: 3, confidence: 0.81, evidence_count: 8, trend: "stable" as const }
];

function Gallery({ skin }: { skin: "healing" | "math-lab" }) {
  return (
    <ChildSkinProvider skin={skin}>
      <div className="ui-kit-column">
        <div className="ui-kit-title">
          <strong>{skin === "healing" ? "轻量治愈" : "数学探索实验室"}</strong>
          <span>18个组件样例</span>
        </div>

        <Preview name="01 PrimaryButton"><PrimaryButton>开始任务</PrimaryButton></Preview>
        <Preview name="02 SurfaceCard"><SurfaceCard>这是一个基础内容卡</SurfaceCard></Preview>
        <Preview name="03 ProgressDots"><ProgressDots current={2} total={5}/></Preview>
        <Preview name="04 AbilityBadge"><AbilityBadge>数量关系 · 成长中</AbilityBadge></Preview>
        <Preview name="05 TodayGoalCard"><TodayGoalCard title="看懂数量关系" tip="先观察，再动手"/></Preview>
        <Preview name="06 MathTaskCard"><MathTaskCard icon="🧪" title="数量关系实验" goal="摆一摆、画一画" minutes={8} difficulty={2}/></Preview>
        <Preview name="07 GrowthEntryCard"><GrowthEntryCard summary="本周又成长了一点" href="#"/></Preview>
        <Preview name="08 MathQuestionCard"><MathQuestionCard prompt="8个苹果比5个苹果多几个？" goal="数量关系"/></Preview>
        <Preview name="09 MathWorkspace"><MathWorkspace uiSchema={{visual:{rows:[{label:"小明",count:8,symbol:"🍎"},{label:"小红",count:5,symbol:"🍎"}]}}}/></Preview>
        <Preview name="10 ManipulativeToolbar"><ManipulativeToolbar/></Preview>
        <Preview name="11 AnswerComposer"><AnswerComposer value="" onChange={()=>{}} onSubmit={()=>{}} placeholder="输入答案"/></Preview>
        <Preview name="12 CoachPanel"><CoachPanel status="hint_available" hint={null} onHint={()=>{}} onRetry={()=>{}} onNext={()=>{}}/></Preview>
        <Preview name="13 CompletionHero"><CompletionHero subtitle="你完成了这次数学挑战。"/></Preview>
        <Preview name="14 LearningBehaviorChecklist"><LearningBehaviorChecklist items={[{label:"自己读懂题目",done:true},{label:"主动检查",done:false}]}/></Preview>
        <Preview name="15 AbilityGrowthCard"><AbilityGrowthCard ability="数量关系" afterLevel={2} trend="up"/></Preview>
        <Preview name="16 SessionStats"><SessionStats duration="6分钟" hints={1} attempts={3}/></Preview>
        <Preview name="17 NextTaskCard"><NextTaskCard title="继续挑战" description="进入下一项数学任务" href="#"/></Preview>
        <Preview name="18 AbilityMap"><AbilityMap abilities={abilities}/></Preview>
      </div>
    </ChildSkinProvider>
  );
}

function Preview({
  name,
  children
}: {
  name: string;
  children: React.ReactNode;
}) {
  return (
    <section className="ui-kit-preview">
      <div className="ui-kit-label">{name}</div>
      {children}
    </section>
  );
}

export default function Page() {
  return (
    <main className="ui-kit-page">
      <header>
        <span className="eyebrow">DEV ONLY</span>
        <h1>Built-in Skin UI Kit · 36个真实组件样例</h1>
        <p className="muted">18个功能组件 × healing/math-lab 两套系统内置皮肤。</p>
      </header>
      <div className="ui-kit-grid">
        <Gallery skin="healing"/>
        <Gallery skin="math-lab"/>
      </div>
    </main>
  );
}
