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
        b.id, b.source_id, b.external_id, b.title_raw, 
        b.media_type, b.media_key, b.video_poster_key,
        b.url, b.created_at, b.updated_at,
        s.name as source_name
      FROM core.blocks b
      LEFT JOIN sources s ON b.source_id = s.id
      ORDER BY b.created_at DESC 
      LIMIT $1
    `,
      [limit]
    );

    const blocks = result.rows.map((row) => ({
      id: row.id,
      source_id: row.source_id,
      source_name: row.source_name,
      external_id: row.external_id,
      title_raw: row.title_raw,
      media_type: row.media_type,
      media_key: row.media_key,
      video_poster_key: row.video_poster_key,
      url: row.url,
      created_at: row.created_at.toISOString(),
      updated_at: row.updated_at.toISOString(),
    }));

    return NextResponse.json(blocks);
  } catch (error) {
    console.error("Database error:", error);
    return NextResponse.json(
      { error: "Failed to fetch blocks" },
      { status: 500 }
    );
  }
}
