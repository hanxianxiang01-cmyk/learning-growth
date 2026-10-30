import { redirect } from "next/navigation";

export default function Page() {
  // V1.4 游客模式（从主分支移植）：不再拼 child_id。
  // 身份由后端经 Cookie 现场签发，前端不再持有任何默认身份。
  redirect("/child/math");
}
