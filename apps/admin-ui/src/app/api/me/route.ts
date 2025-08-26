import { NextResponse } from "next/server";

export async function GET() {
  // If middleware passed, we have a valid cookie
  return NextResponse.json({ username: "admin", roles: ["admin"] });
}


