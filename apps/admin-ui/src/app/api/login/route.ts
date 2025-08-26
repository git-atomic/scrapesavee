import { NextResponse } from "next/server";
import crypto from "crypto";

function base64url(input: Buffer | string): string {
  return (typeof input === "string" ? Buffer.from(input) : input)
    .toString("base64")
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
}

function signJwtHS256(payload: Record<string, any>, secret: string): string {
  const header = { alg: "HS256", typ: "JWT" };
  const headerB64 = base64url(JSON.stringify(header));
  const payloadB64 = base64url(JSON.stringify(payload));
  const data = `${headerB64}.${payloadB64}`;
  const sig = crypto.createHmac("sha256", secret).update(data).digest();
  const sigB64 = base64url(sig);
  return `${data}.${sigB64}`;
}

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  const { username, password } = (body || {}) as {
    username?: string;
    password?: string;
  };

  const adminUser = process.env.ADMIN_USER || "admin";
  const adminPass = process.env.ADMIN_PASS || "admin123";
  const secret = process.env.SECRET_KEY || "dev-secret";

  if (!username || !password) {
    return NextResponse.json({ error: "Missing credentials" }, { status: 400 });
  }

  if (username !== adminUser || password !== adminPass) {
    return NextResponse.json({ error: "Invalid credentials" }, { status: 401 });
  }

  const exp = Math.floor(Date.now() / 1000) + 60 * 60 * 24; // 24h
  const token = signJwtHS256({ sub: username, exp, roles: ["admin"] }, secret);

  const res = NextResponse.json({ success: true });
  res.headers.append(
    "Set-Cookie",
    `ss_token=${token}; HttpOnly; Path=/; Max-Age=${60 * 60 * 24}; SameSite=Lax; Secure`
  );
  return res;
}
