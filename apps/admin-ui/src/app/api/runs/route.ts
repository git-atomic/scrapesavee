import { NextResponse } from "next/server";
import { Pool } from "pg";

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl:
    process.env.NODE_ENV === "production"
      ? { rejectUnauthorized: false }
      : false,
});

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get("limit") || "20");

    const result = await pool.query(
      `
      SELECT 
        r.id, r.source_id, r.kind, r.status, 
        r.started_at, r.finished_at, r.counters, r.error,
        s.name as source_name
      FROM runs r
      LEFT JOIN sources s ON r.source_id = s.id
      ORDER BY r.started_at DESC 
      LIMIT $1
    `,
      [limit]
    );

    const runs = result.rows.map((row) => ({
      id: row.id,
      source_id: row.source_id,
      source_name: row.source_name,
      kind: row.kind,
      status: row.status,
      started_at: row.started_at.toISOString(),
      finished_at: row.finished_at?.toISOString() || null,
      counters: row.counters || {},
      error: row.error,
    }));

    return NextResponse.json(runs);
  } catch (error) {
    console.error("Database error:", error);
    return NextResponse.json(
      { error: "Failed to fetch runs" },
      { status: 500 }
    );
  }
}
