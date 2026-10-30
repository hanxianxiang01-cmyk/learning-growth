import { MathHomeScreen } from "@/src/screens/MathHomeScreen";

export default function Page() {
  // V1.4 游客模式（从主分支移植）：身份由屏幕层经 bootstrap 解析，
  // 页面不再从 query 或默认值取 child_id。
  return <MathHomeScreen />;
}
