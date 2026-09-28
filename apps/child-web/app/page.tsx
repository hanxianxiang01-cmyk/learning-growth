import { redirect } from "next/navigation";
import { config } from "@/src/config";

export default function Page() {
  redirect(`/child/math?child_id=${encodeURIComponent(config.defaultChildId)}`);
}
