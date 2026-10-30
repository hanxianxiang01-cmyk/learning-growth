import { redirect } from "next/navigation";

/**
 * 站点根路径。
 *
 * V1.4 游客模式：原先这里 redirect 到 `/child/math?child_id=<固定默认 id>`。
 * 那个固定 id 是所有人共用的演示身份（且被治理脚本标为「真实孩子」），
 * 正是方案 2.1 明令禁止的「固定的公共游客 ID」。现在不带任何身份参数跳转，
 * 身份由 `/child/math` 页面 bootstrap 时由服务端签发。
 */
export default function Page() {
  redirect("/child/math");
}