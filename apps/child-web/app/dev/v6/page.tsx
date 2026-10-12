import { notFound } from "next/navigation";
import { V6Gallery } from "@/src/dev/v6/V6Gallery";

export default function Page() {
  if (process.env.NODE_ENV === "production") notFound();
  return <main><V6Gallery /></main>;
}
