import { notFound } from "next/navigation";
import { UiKitGallery } from "@/src/dev/UiKitGallery";
export default function Page() {
  if (process.env.NODE_ENV === "production") notFound();
  return <UiKitGallery />;
}
