"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Database,
  Globe,
  HardDrive,
  Images,
  Play,
  TrendingUp,
  Users,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { workerApi } from "@/lib/api";

interface StatsCard {
  title: string;
  value: string | number;
  change?: string;
  icon: React.ComponentType<{ className?: string }>;
  color?: "default" | "green" | "blue" | "orange" | "red";
}

export function EngineOverview() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["engine-stats"],
    queryFn: () => workerApi.getStats().then((res) => res.data),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const { data: healthData } = useQuery({
    queryKey: ["engine-health"],
    queryFn: () => workerApi.getHealth().then((res) => res.data),
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 px-4 lg:px-6">
        {Array.from({ length: 8 }).map((_, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="h-4 w-20 bg-muted animate-pulse rounded" />
              <div className="h-4 w-4 bg-muted animate-pulse rounded" />
            </CardHeader>
            <CardContent>
              <div className="h-8 w-16 bg-muted animate-pulse rounded mb-2" />
              <div className="h-3 w-24 bg-muted animate-pulse rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const statsCards: StatsCard[] = [
    {
      title: "Active Sources",
      value: stats?.sources?.enabled || 0,
      change: `${stats?.sources?.total || 0} total`,
      icon: Globe,
      color: "green",
    },
    {
      title: "Running Jobs",
      value: stats?.jobs?.running || 0,
      change: `${stats?.jobs?.queued || 0} queued`,
      icon: Play,
      color: "blue",
    },
    {
      title: "Total Blocks",
      value: stats?.blocks?.total || 0,
      change: `+${stats?.blocks?.today || 0} today`,
      icon: Images,
      color: "default",
    },
    {
      title: "Discovered Users",
      value: stats?.users?.total || 0,
      change: `+${stats?.users?.new || 0} new`,
      icon: Users,
      color: "orange",
    },
    {
      title: "Storage Used",
      value: `${stats?.storage?.used_gb || 0}GB`,
      change: `${stats?.storage?.total_gb || 100}GB total`,
      icon: HardDrive,
      color: "default",
    },
    {
      title: "Database Size",
      value: `${stats?.database?.size_mb || 0}MB`,
      change: `${stats?.database?.tables || 0} tables`,
      icon: Database,
      color: "default",
    },
    {
      title: "Success Rate",
      value: `${stats?.jobs?.success_rate || 0}%`,
      change: "Last 24h",
      icon: TrendingUp,
      color: stats?.jobs?.success_rate >= 90 ? "green" : "orange",
    },
    {
      title: "System Health",
      value: healthData?.status === "healthy" ? "Healthy" : "Issues",
      change: `${healthData?.response_time_ms?.toFixed(0) || 0}ms`,
      icon: Activity,
      color: healthData?.status === "healthy" ? "green" : "red",
    },
  ];

  const getCardColorClasses = (color: StatsCard["color"]) => {
    switch (color) {
      case "green":
        return "text-green-600 dark:text-green-400";
      case "blue":
        return "text-blue-600 dark:text-blue-400";
      case "orange":
        return "text-orange-600 dark:text-orange-400";
      case "red":
        return "text-red-600 dark:text-red-400";
      default:
        return "text-muted-foreground";
    }
  };

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 px-4 lg:px-6">
        {statsCards.map((card, index) => (
          <Card key={index} className="hover:shadow-md transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {card.title}
              </CardTitle>
              <card.icon
                className={`h-4 w-4 ${getCardColorClasses(card.color)}`}
              />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{card.value}</div>
              {card.change && (
                <p className="text-xs text-muted-foreground">{card.change}</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Actions & Status */}
      <div className="grid gap-4 md:grid-cols-3 px-4 lg:px-6">
        {/* Engine Status */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Engine Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm">Overall Health</span>
              <Badge
                variant={
                  healthData?.status === "healthy" ? "default" : "destructive"
                }
              >
                {healthData?.status === "healthy" ? "Healthy" : "Issues"}
              </Badge>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>CPU Usage</span>
                <span>{stats?.system?.cpu_percent || 0}%</span>
              </div>
              <Progress value={stats?.system?.cpu_percent || 0} />
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Memory Usage</span>
                <span>{stats?.system?.memory_percent || 0}%</span>
              </div>
              <Progress value={stats?.system?.memory_percent || 0} />
            </div>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 bg-green-500 rounded-full" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Job completed</p>
                  <p className="text-xs text-muted-foreground">
                    Savee Home - 2 min ago
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="w-2 h-2 bg-blue-500 rounded-full" />
                <div className="flex-1">
                  <p className="text-sm font-medium">New user discovered</p>
                  <p className="text-xs text-muted-foreground">
                    @designer123 - 5 min ago
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="w-2 h-2 bg-orange-500 rounded-full" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Storage alert</p>
                  <p className="text-xs text-muted-foreground">
                    85% capacity - 10 min ago
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Quick Stats */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm">Avg. Job Time</span>
                <span className="text-sm font-medium">
                  {stats?.performance?.avg_job_time || "2.3"}min
                </span>
              </div>

              <div className="flex justify-between">
                <span className="text-sm">Items/Hour</span>
                <span className="text-sm font-medium">
                  {stats?.performance?.items_per_hour || "156"}
                </span>
              </div>

              <div className="flex justify-between">
                <span className="text-sm">Success Rate</span>
                <span className="text-sm font-medium">
                  {stats?.jobs?.success_rate || "94"}%
                </span>
              </div>

              <div className="flex justify-between">
                <span className="text-sm">Uptime</span>
                <span className="text-sm font-medium">
                  {stats?.system?.uptime || "2d 14h"}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

