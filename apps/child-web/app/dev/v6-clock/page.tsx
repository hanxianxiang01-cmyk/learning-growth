import { notFound } from "next/navigation";
import { V6SliceGallery } from "@/src/components/ui-v6/V6SliceGallery";

export default function Page() {
  if (process.env.NODE_ENV === "production") notFound();
  return <main style={{ maxWidth: 1060, margin: "0 auto", padding: 12 }}><V6SliceGallery /></main>;
}
