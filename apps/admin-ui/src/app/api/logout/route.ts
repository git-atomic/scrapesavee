import { NextResponse } from "next/server";

export async function POST() {
  const res = NextResponse.json({ success: true });
  res.headers.append("Set-Cookie", "ss_token=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax; Secure");
  return res;
}


