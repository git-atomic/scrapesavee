import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

async function verifyJwtEdge(token: string, secret: string): Promise<boolean> {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return false;
    const [h, p, s] = parts;
    const enc = new TextEncoder();
    const key = await crypto.subtle.importKey(
      "raw",
      enc.encode(secret),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"]
    );
    const data = `${h}.${p}`;
    const sigBuf = await crypto.subtle.sign("HMAC", key, enc.encode(data));
    const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sigBuf)))
      .replace(/=/g, "")
      .replace(/\+/g, "-")
      .replace(/\//g, "_");
    if (sigB64 !== s) return false;
    const payloadJson = atob(p.replace(/-/g, "+").replace(/_/g, "/"));
    const payload = JSON.parse(payloadJson) as { exp?: number };
    if (payload?.exp && Math.floor(Date.now() / 1000) > payload.exp) return false;
    return true;
  } catch {
    return false;
  }
}

// Basic gate for serverless API routes: require admin token cookie (placeholder)
export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (pathname.startsWith("/api")) {
    // Allow public health and stats reads
    const isPublic =
      pathname.startsWith("/api/health") ||
      pathname.startsWith("/api/stats") ||
      pathname.startsWith("/api/blocks") ||
      pathname.startsWith("/api/runs") ||
      (pathname.startsWith("/api/sources") && req.method === "GET") ||
      pathname.startsWith("/api/login");

    if (isPublic) return NextResponse.next();

    const token = req.cookies.get("ss_token")?.value;
    if (!token) {
      return new NextResponse(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }
    const secret = process.env.SECRET_KEY || "dev-secret";
    const ok = await verifyJwtEdge(token, secret);
    if (!ok) {
      return new NextResponse(JSON.stringify({ error: "Invalid token" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }
  }
  // Protect app pages except /login
  if (!pathname.startsWith("/login")) {
    const token = req.cookies.get("ss_token")?.value;
    if (!token) {
      return NextResponse.redirect(new URL("/login", req.url));
    }
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/api/:path*"],
};
