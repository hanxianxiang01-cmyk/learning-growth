/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // 双皮肤 E2E：NEXT_PUBLIC_* 是编译期内联，两个 dev 实例共享 .next 会互相覆盖皮肤产物。
  // 允许用 NEXT_DIST_DIR 隔离构建目录（默认 .next，产品本地行为不变）。
  distDir: process.env.NEXT_DIST_DIR || ".next"
};
export default nextConfig;
