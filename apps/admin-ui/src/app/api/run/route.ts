import { NextResponse } from "next/server";
import { exec } from "child_process";
import path from "path";

export async function POST() {
  try {
    if (process.env.NODE_ENV === "production") {
      return NextResponse.json(
        { error: "Not allowed in production" },
        { status: 403 }
      );
    }

    const repoRoot = path.resolve(process.cwd(), "../../..");
    const workerDir = path.join(repoRoot, "apps", "worker");
    const cmd =
      process.platform === "win32"
        ? `cd /d "${workerDir}" && python -m app.cli --max-items 5`
        : `cd "${workerDir}" && python -m app.cli --max-items 5`;

    const execPromise = () =>
      new Promise<{ code: number; stdout: string; stderr: string }>(
        (resolve) => {
          exec(
            cmd,
            { env: process.env, windowsHide: true, timeout: 1000 * 60 * 10 },
            (error, stdout, stderr) => {
              resolve({
                code: error ? (error as any).code || 1 : 0,
                stdout: stdout || "",
                stderr: stderr || "",
              });
            }
          );
        }
      );

    const { code, stdout, stderr } = await execPromise();
    if (code !== 0) {
      return NextResponse.json(
        { ok: false, code, stdout, stderr },
        { status: 500 }
      );
    }
    return NextResponse.json({ ok: true, stdout });
  } catch (e: any) {
    return NextResponse.json(
      { error: e?.message || "run failed" },
      { status: 500 }
    );
  }
}
