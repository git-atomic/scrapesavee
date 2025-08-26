import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { verifyToken } from "@/src/lib/auth";

// Basic gate for serverless API routes: require admin token cookie (placeholder)
export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (pathname.startsWith("/api")) {
    // Allow public health and stats reads
    const isPublic =
      pathname.startsWith("/api/health") ||
      pathname.startsWith("/api/stats") ||
      pathname.startsWith("/api/blocks") ||
      pathname.startsWith("/api/runs") ||
      (pathname.startsWith("/api/sources") && req.method === "GET");

    if (isPublic) return NextResponse.next();

    const token = req.cookies.get("ss_token")?.value;
    if (!token) {
      return new NextResponse(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }
    const secret = process.env.SECRET_KEY || "dev-secret";
    const payload = verifyToken(token, secret);
    if (!payload) {
      return new NextResponse(JSON.stringify({ error: "Invalid token" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/api/:path*"],
};
