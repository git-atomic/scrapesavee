import { NextResponse } from "next/server";
import { Pool } from "pg";

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl:
    process.env.NODE_ENV === "production"
      ? { rejectUnauthorized: false }
      : false,
});

export async function PATCH(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const id = params.id;
    const body = await request.json();
    const { enabled, name, type, url } = body as {
      enabled?: boolean;
      name?: string;
      type?: string;
      url?: string;
    };

    const fields: string[] = [];
    const values: any[] = [];

    if (typeof enabled === "boolean") {
      fields.push(`enabled = $${fields.length + 1}`);
      values.push(enabled);
    }
    if (typeof name === "string") {
      fields.push(`name = $${fields.length + 1}`);
      values.push(name);
    }
    if (typeof type === "string") {
      fields.push(`type = $${fields.length + 1}`);
      values.push(type);
    }
    if (typeof url === "string") {
      fields.push(`url = $${fields.length + 1}`);
      values.push(url);
    }

    if (fields.length === 0) {
      return NextResponse.json(
        { error: "No fields to update" },
        { status: 400 }
      );
    }

    values.push(id);

    const result = await pool.query(
      `UPDATE sources SET ${fields.join(
        ", "
      )}, updated_at = NOW() WHERE id = $$${
        fields.length + 1
      } RETURNING id, name, type, url, enabled, status, next_run_at, created_at, updated_at` as any,
      values
    );

    const row = result.rows[0];
    return NextResponse.json({
      id: row.id,
      name: row.name,
      type: row.type,
      url: row.url,
      enabled: row.enabled,
      status: row.status,
      next_run_at: row.next_run_at?.toISOString() || null,
      created_at: row.created_at.toISOString(),
      updated_at: row.updated_at.toISOString(),
    });
  } catch (error) {
    console.error("Database error:", error);
    return NextResponse.json(
      { error: "Failed to update source" },
      { status: 500 }
    );
  }
}
