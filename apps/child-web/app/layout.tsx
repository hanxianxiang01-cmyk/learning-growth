import "./globals.css";
import { ChildSkinProvider } from "@/src/theme/ChildSkinProvider";
import { config } from "@/src/config";

export const metadata = {
  title: "数学探索实验室",
  description: "儿童数学能力成长系统 Sprint 3 前端"
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <ChildSkinProvider skin={config.childMathSkin}>
          {children}
        </ChildSkinProvider>
      </body>
    </html>
  );
}
