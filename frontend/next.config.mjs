/** @type {import('next').NextConfig} */
export default {
  // 8001/3002 rather than the usual 8000/3000: this machine runs another project there.
  env: { NEXT_PUBLIC_API: process.env.NEXT_PUBLIC_API ?? "http://localhost:8001" },
};
