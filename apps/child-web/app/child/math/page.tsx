import { MathHomeScreen } from "@/src/screens/MathHomeScreen";

/**
 * 数学学习首页。
 *
 * V1.4 游客模式：不接收 `child_id`。身份由服务端在 `/v1/guest/bootstrap`
 * 签发（HttpOnly Cookie），客户端组件启动时 bootstrap 再取回自己的 id。
 *
 * 方案 1.2「不展示登录页、注册弹窗或强制授权流程」：本页就是入口，
 * 打开即有身份，没有任何额外步骤。
 */
export default function Page() {
  return <MathHomeScreen />;
}