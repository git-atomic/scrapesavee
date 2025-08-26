import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import { EngineOverview } from "@/components/engine-overview";
import { JobsManager } from "@/components/jobs-manager";
import { MediaLibrary } from "@/components/media-library";
import { SourcesManager } from "@/components/sources-manager";

export default function Home() {
  // Auth handled by middleware; no client-side token checks
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
