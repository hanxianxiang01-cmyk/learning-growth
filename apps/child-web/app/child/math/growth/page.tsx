import { MathGrowthScreen } from "@/src/screens/MathGrowthScreen";

/**
 * 成长页。
 *
 * V1.4 游客模式：身份不再来自 URL，由客户端侧通过 `/v1/guest/me` 取回；
 * 服务端按 Cookie 校验归属，改 URL 看不到别人的成长记录。
 */
export default function Page() {
  return <MathGrowthScreen />;
}