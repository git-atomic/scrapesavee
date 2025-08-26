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
  const startTime = Date.now();

  try {
    // Test database connection
    await pool.query("SELECT 1");

    const responseTime = Date.now() - startTime;

    return NextResponse.json({
      status: "healthy",
      database: "connected",
      message: "All systems operational",
      response_time_ms: responseTime,
      timestamp: new Date().toISOString(),
      version: "1.0.0",
    });
  } catch (error) {
    const responseTime = Date.now() - startTime;

    return NextResponse.json(
      {
        status: "unhealthy",
        database: "disconnected",
        message: `Database error: ${error}`,
        response_time_ms: responseTime,
        timestamp: new Date().toISOString(),
        version: "1.0.0",
      },
      { status: 503 }
    );
  }
}
