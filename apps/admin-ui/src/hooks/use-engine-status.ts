"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { workerApi } from "@/lib/api";
import { toast } from "sonner";

export function useEngineStatus() {
  const [isRunning, setIsRunning] = useState(false);
  const queryClient = useQueryClient();

  // Query engine status
  const { data: healthData } = useQuery({
    queryKey: ["engine-health"],
    queryFn: () => workerApi.getHealth().then((res) => res.data),
    refetchInterval: 5000, // Check every 5 seconds
  });

  // Update running state based on health data
  useEffect(() => {
    if (healthData) {
      setIsRunning(healthData.status === "healthy");
    }
  }, [healthData]);

  // Toggle engine mutation
  const toggleEngineMutation = useMutation({
    mutationFn: async () => {
      // In dev, run one cycle locally
      return workerApi.runOnce();
    },
    onSuccess: () => {
      toast.success("Run triggered");
      queryClient.invalidateQueries({ queryKey: ["engine-health"] });
    },
    onError: (error) => {
      toast.error("Failed to trigger run");
      console.error("Engine toggle error:", error);
    },
  });

  const getStatus = (): string => {
    if (!healthData) return "Unknown";

    switch (healthData.status) {
      case "healthy":
        return "Running";
      case "unhealthy":
        return "Error";
      default:
        return "Stopped";
    }
  };

  return {
    status: getStatus(),
    isRunning,
    isLoading: toggleEngineMutation.isPending,
    toggleEngine: toggleEngineMutation.mutate,
    healthData,
  };
}

