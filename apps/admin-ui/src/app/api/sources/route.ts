import { NextResponse } from "next/server";
import { Pool } from "pg";

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl:
    process.env.NODE_ENV === "production"
      ? { rejectUnauthorized: false }
      : false,
});

export async function GET() {
  try {
    const result = await pool.query(`
      SELECT 
        id, name, type, url, enabled, status, 
        next_run_at, created_at, updated_at
      FROM sources 
      ORDER BY created_at DESC
    `);

    const sources = result.rows.map((row) => ({
      id: row.id,
      name: row.name,
      type: row.type,
      url: row.url,
      enabled: row.enabled,
      status: row.status,
      next_run_at: row.next_run_at?.toISOString() || null,
      created_at: row.created_at.toISOString(),
      updated_at: row.updated_at.toISOString(),
    }));

    return NextResponse.json(sources);
  } catch (error) {
    console.error("Database error:", error);
    return NextResponse.json(
      { error: "Failed to fetch sources" },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { name, type, url, enabled = true } = body;

    const result = await pool.query(
      `
      INSERT INTO sources (name, type, url, enabled, status)
      VALUES ($1, $2, $3, $4, 'active')
      RETURNING id, name, type, url, enabled, status, next_run_at, created_at, updated_at
    `,
      [name, type, url, enabled]
    );

    const source = result.rows[0];
    return NextResponse.json({
      id: source.id,
      name: source.name,
      type: source.type,
      url: source.url,
      enabled: source.enabled,
      status: source.status,
      next_run_at: source.next_run_at?.toISOString() || null,
      created_at: source.created_at.toISOString(),
      updated_at: source.updated_at.toISOString(),
    });
  } catch (error) {
    console.error("Database error:", error);
    return NextResponse.json(
      { error: "Failed to create source" },
      { status: 500 }
    );
  }
}
