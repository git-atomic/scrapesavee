import { NextResponse } from "next/server";

// Dispatches the GitHub Actions workflow via REST API
// Requires the following Vercel env vars:
// - GITHUB_REPO (e.g. "YOUR_USERNAME/scrapesavee")
// - GITHUB_TOKEN (a classic PAT with workflow scope) OR use a proxy action

export async function POST() {
  const repo = process.env.GITHUB_REPO;
  const token = process.env.GITHUB_TOKEN;

  if (!repo || !token) {
    return NextResponse.json(
      { error: "GITHUB_REPO or GITHUB_TOKEN not configured" },
      { status: 500 }
    );
  }

  try {
    const res = await fetch(
      `https://api.github.com/repos/${repo}/actions/workflows/worker.yml/dispatches`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/vnd.github+json",
          "X-GitHub-Api-Version": "2022-11-28",
        },
        body: JSON.stringify({
          ref: "main",
          inputs: {
            max_items: "10",
          },
        }),
      }
    );

    if (!res.ok) {
      const text = await res.text();
      return NextResponse.json(
        { error: `Failed to dispatch workflow: ${res.status} ${text}` },
        { status: 500 }
      );
    }

    return NextResponse.json({ success: true });
  } catch (e: any) {
    return NextResponse.json(
      { error: e?.message || "Unknown error" },
      { status: 500 }
    );
  }
}
