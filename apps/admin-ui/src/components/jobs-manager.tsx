"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Play,
  Pause,
  Square,
  RefreshCw,
  MoreVertical,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Eye,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { workerApi } from "@/lib/api";
import { toast } from "sonner";

interface Job {
  id: string;
  source_id: string;
  source_name: string;
  source_url: string;
  type: "tail" | "backfill" | "manual";
  status: "running" | "queued" | "completed" | "failed" | "paused";
  progress: number;
  started_at: string;
  estimated_completion?: string;
  stats: {
    items_discovered: number;
    items_processed: number;
    media_uploaded: number;
    errors: number;
  };
  error_message?: string;
}

export function JobsManager() {
  const [selectedTab, setSelectedTab] = useState("running");
  const queryClient = useQueryClient();

  const { data: jobs, isLoading } = useQuery({
    queryKey: ["jobs", selectedTab],
    queryFn: () =>
      workerApi.getJobs?.(selectedTab).then((res) => res.data) ||
      Promise.resolve([]),
    refetchInterval: 2000, // Real-time updates every 2 seconds
  });

  const pauseJobMutation = useMutation({
    mutationFn: (jobId: string) =>
      workerApi.pauseJob?.(jobId) ||
      Promise.resolve({ data: { success: true } }),
    onSuccess: () => {
      toast.success("Job paused");
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
    onError: () => toast.error("Failed to pause job"),
  });

  const resumeJobMutation = useMutation({
    mutationFn: (jobId: string) =>
      workerApi.resumeJob?.(jobId) ||
      Promise.resolve({ data: { success: true } }),
    onSuccess: () => {
      toast.success("Job resumed");
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
    onError: () => toast.error("Failed to resume job"),
  });

  const cancelJobMutation = useMutation({
    mutationFn: (jobId: string) =>
      workerApi.cancelJob?.(jobId) ||
      Promise.resolve({ data: { success: true } }),
    onSuccess: () => {
      toast.success("Job cancelled");
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
    onError: () => toast.error("Failed to cancel job"),
  });

  const getStatusIcon = (status: Job["status"]) => {
    switch (status) {
      case "running":
        return <Play className="h-4 w-4 text-green-500" />;
      case "queued":
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "paused":
        return <Pause className="h-4 w-4 text-orange-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: Job["status"]) => {
    const variants = {
      running: "default",
      queued: "secondary",
      completed: "outline",
      failed: "destructive",
      paused: "secondary",
    } as const;

    return (
      <Badge
        variant={variants[status] || "secondary"}
        className="flex items-center gap-1"
      >
        {getStatusIcon(status)}
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    );
  };

  const displayJobs = jobs || [];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Play className="h-5 w-5" />
            Jobs Manager
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                queryClient.invalidateQueries({ queryKey: ["jobs"] })
              }
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs value={selectedTab} onValueChange={setSelectedTab}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="running">Running</TabsTrigger>
            <TabsTrigger value="queued">Queued</TabsTrigger>
            <TabsTrigger value="completed">Completed</TabsTrigger>
            <TabsTrigger value="failed">Failed</TabsTrigger>
          </TabsList>

          <TabsContent value={selectedTab} className="mt-6">
            {isLoading ? (
              <div className="space-y-4">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-16 bg-muted animate-pulse rounded"
                  />
                ))}
              </div>
            ) : displayJobs.length > 0 ? (
              <div className="space-y-4">
                {displayJobs
                  .filter((job) =>
                    selectedTab === "running"
                      ? job.status === "running"
                      : selectedTab === "queued"
                      ? job.status === "queued"
                      : selectedTab === "completed"
                      ? job.status === "completed"
                      : job.status === "failed"
                  )
                  .map((job) => (
                    <div
                      key={job.id}
                      className="border rounded-lg p-4 space-y-3"
                    >
                      {/* Job Header */}
                      <div className="flex items-center justify-between">
                        <div className="space-y-1">
                          <div className="flex items-center gap-3">
                            {getStatusBadge(job.status)}
                            <span className="font-semibold">
                              {job.source_name}
                            </span>
                            <Badge variant="outline">{job.type}</Badge>
                          </div>
                          <p className="text-sm text-muted-foreground">
                            {job.source_url}
                          </p>
                        </div>

                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            {job.status === "running" && (
                              <DropdownMenuItem
                                onClick={() => pauseJobMutation.mutate(job.id)}
                              >
                                <Pause className="h-4 w-4 mr-2" />
                                Pause Job
                              </DropdownMenuItem>
                            )}
                            {job.status === "paused" && (
                              <DropdownMenuItem
                                onClick={() => resumeJobMutation.mutate(job.id)}
                              >
                                <Play className="h-4 w-4 mr-2" />
                                Resume Job
                              </DropdownMenuItem>
                            )}
                            {(job.status === "running" ||
                              job.status === "queued") && (
                              <DropdownMenuItem
                                onClick={() => cancelJobMutation.mutate(job.id)}
                              >
                                <Square className="h-4 w-4 mr-2" />
                                Cancel Job
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuItem>
                              <Eye className="h-4 w-4 mr-2" />
                              View Logs
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>

                      {/* Progress Bar */}
                      {job.status === "running" && (
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span>Progress</span>
                            <span>{job.progress}%</span>
                          </div>
                          <Progress value={job.progress} />
                        </div>
                      )}

                      {/* Job Stats */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <div className="text-muted-foreground">
                            Discovered
                          </div>
                          <div className="font-medium">
                            {job.stats.items_discovered}
                          </div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Processed</div>
                          <div className="font-medium">
                            {job.stats.items_processed}
                          </div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Uploaded</div>
                          <div className="font-medium">
                            {job.stats.media_uploaded}
                          </div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Errors</div>
                          <div
                            className={`font-medium ${
                              job.stats.errors > 0 ? "text-red-500" : ""
                            }`}
                          >
                            {job.stats.errors}
                          </div>
                        </div>
                      </div>

                      {/* Timing Info */}
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>
                          Started: {new Date(job.started_at).toLocaleString()}
                        </span>
                        {job.estimated_completion && (
                          <span>
                            ETA:{" "}
                            {new Date(
                              job.estimated_completion
                            ).toLocaleString()}
                          </span>
                        )}
                      </div>

                      {/* Error Message */}
                      {job.error_message && (
                        <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
                          {job.error_message}
                        </div>
                      )}
                    </div>
                  ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No {selectedTab} jobs found
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
