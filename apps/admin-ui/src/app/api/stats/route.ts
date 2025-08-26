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
    // Get sources count
    const sourcesResult = await pool.query(`
      SELECT 
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE enabled = true) as enabled
      FROM sources
    `);

    // Get runs count
    const runsResult = await pool.query(`
      SELECT COUNT(*) as total FROM runs
    `);

    // Get blocks count
    const blocksResult = await pool.query(`
      SELECT COUNT(*) as total FROM core.blocks
    `);

    // Get recent activity
    const recentResult = await pool.query(`
      SELECT 
        COUNT(*) as recent_runs,
        MAX(started_at) as last_run
      FROM runs 
      WHERE started_at > NOW() - INTERVAL '24 hours'
    `);

    return NextResponse.json({
      sources: {
        total: parseInt(sourcesResult.rows[0].total),
        enabled: parseInt(sourcesResult.rows[0].enabled),
      },
      runs: {
        total: parseInt(runsResult.rows[0].total),
      },
      blocks: {
        total: parseInt(blocksResult.rows[0].total),
      },
      jobs: {
        running: 0,
        queued: 0,
        success_rate: 95,
      },
      system: {
        cpu_percent: 15,
        memory_percent: 45,
        uptime: "GitHub Actions",
        recent_runs: parseInt(recentResult.rows[0].recent_runs),
        last_run: recentResult.rows[0].last_run,
      },
    });
  } catch (error) {
    console.error("Database error:", error);
    return NextResponse.json(
      { error: "Failed to fetch stats" },
      { status: 500 }
    );
  }
}
