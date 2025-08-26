import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import { workerApi } from "@/lib/api";
import { EngineOverview } from "@/components/engine-overview";
import { JobsManager } from "@/components/jobs-manager";
import { MediaLibrary } from "@/components/media-library";
import { SourcesManager } from "@/components/sources-manager";

export default function Home() {
  // Redirect to login if not authenticated (client-side guard)
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("ss_token");
    if (!token) {
      window.location.href = "/login";
      return null as any;
    }
  }
  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Engine Overview Cards */}
        <EngineOverview />

        {/* Jobs Manager */}
        <JobsManager />

        {/* Sources Manager */}
        <SourcesManager />

        {/* Media Library */}
        <MediaLibrary />
      </div>
    </DashboardLayout>
  );
}
