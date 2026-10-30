import { MathResultScreen } from "@/src/screens/MathResultScreen";

/**
 * 结果页。
 *
 * V1.4 游客模式：身份由客户端侧 `/v1/guest/me` 取回；结果接口
 * `GET /v1/learning/sessions/{id}/result` 会校验该 session 属于当前游客，
 * 改 sessionId 读不到别人的结果。
 */
export default function Page({ params }: { params: { sessionId: string } }) {
  return <MathResultScreen sessionId={params.sessionId} />;
}