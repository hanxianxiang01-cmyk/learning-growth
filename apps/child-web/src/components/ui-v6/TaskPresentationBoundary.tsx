"use client";

import { Component, type ReactNode } from "react";

/** Render failures never expose parser assertions or a developer stack to the child. */
export class TaskPresentationBoundary extends Component<{ children: ReactNode; onReload: () => void }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (!this.state.failed) return this.props.children;
    return <section className="surface-card v6-task-unavailable" role="alert"><h2>这项任务暂时没有准备好</h2><p>请重新准备任务后再试。</p><button type="button" className="primary-button" onClick={this.props.onReload}>重新准备任务</button></section>;
  }
}
