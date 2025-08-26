"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Plus,
  Globe,
  Play,
  Pause,
  Settings,
  Trash2,
  ExternalLink,
  TrendingUp,
  Home,
  User,
  Folder,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { workerApi, type Source } from "@/lib/api";
import { toast } from "sonner";

type SourceType = "home" | "trending" | "user" | "collection";

interface SourceTypeInfo {
  type: SourceType;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  description: string;
  frontendRoute: string;
  defaultInterval: string;
}

export function SourcesManager() {
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [newUrl, setNewUrl] = useState("");
  const [detectedType, setDetectedType] = useState<SourceTypeInfo | null>(null);
  const queryClient = useQueryClient();

  const { data: sources, isLoading } = useQuery({
    queryKey: ["sources"],
    queryFn: () => workerApi.getSources().then((res) => res.data),
    refetchInterval: 30000,
  });

  const addSourceMutation = useMutation({
    mutationFn: (sourceData: any) => workerApi.addSource(sourceData),
    onSuccess: () => {
      toast.success("Source added successfully");
      setIsAddDialogOpen(false);
      setNewUrl("");
      setDetectedType(null);
      queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
    onError: () => toast.error("Failed to add source"),
  });

  const toggleSourceMutation = useMutation({
    mutationFn: ({
      sourceId,
      enabled,
    }: {
      sourceId: string;
      enabled: boolean;
    }) => workerApi.toggleSource(sourceId, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
    onError: () => toast.error("Failed to update source"),
  });

  const triggerSweepMutation = useMutation({
    mutationFn: ({
      sourceId,
      sweepType,
    }: {
      sourceId: string;
      sweepType: "tail" | "backfill";
    }) => workerApi.triggerSweep(sourceId, sweepType),
    onSuccess: () => {
      toast.success("Sweep triggered successfully");
    },
    onError: () => toast.error("Failed to trigger sweep"),
  });

  // Smart URL detection
  const detectSourceType = (url: string): SourceTypeInfo | null => {
    const cleanUrl = url.toLowerCase().trim();

    if (
      cleanUrl.includes("savee.com/popular") ||
      cleanUrl.includes("savee.com/trending")
    ) {
      return {
        type: "trending",
        icon: TrendingUp,
        label: "Trending",
        description: "Popular content from Savee",
        frontendRoute: "/trending",
        defaultInterval: "1 hour",
      };
    }

    if (
      cleanUrl === "savee.com" ||
      cleanUrl === "https://savee.com" ||
      cleanUrl === "https://savee.com/"
    ) {
      return {
        type: "home",
        icon: Home,
        label: "Home Feed",
        description: "Main Savee homepage content",
        frontendRoute: "/",
        defaultInterval: "30 minutes",
      };
    }

    const userMatch = cleanUrl.match(/savee\.com\/([a-zA-Z0-9_-]+)$/);
    if (userMatch) {
      const username = userMatch[1];
      return {
        type: "user",
        icon: User,
        label: "User Profile",
        description: `Content from @${username}`,
        frontendRoute: `/users/${username}`,
        defaultInterval: "6 hours",
      };
    }

    return {
      type: "collection",
      icon: Folder,
      label: "Custom Collection",
      description: "Custom URL collection",
      frontendRoute: `/collections/${Date.now()}`,
      defaultInterval: "12 hours",
    };
  };

  const handleUrlChange = (url: string) => {
    setNewUrl(url);
    if (url.trim()) {
      setDetectedType(detectSourceType(url));
    } else {
      setDetectedType(null);
    }
  };

  const handleAddSource = () => {
    if (!newUrl.trim() || !detectedType) return;

    addSourceMutation.mutate({
      name:
        detectedType.label +
        (detectedType.type === "user" ? ` - ${newUrl.split("/").pop()}` : ""),
      url: newUrl,
      type: detectedType.type,
      frontend_route: detectedType.frontendRoute,
      scrape_interval: detectedType.defaultInterval,
      enabled: true,
    });
  };

  const getSourceIcon = (type: string) => {
    switch (type) {
      case "home":
        return <Home className="h-4 w-4" />;
      case "trending":
        return <TrendingUp className="h-4 w-4" />;
      case "user":
        return <User className="h-4 w-4" />;
      default:
        return <Folder className="h-4 w-4" />;
    }
  };

  const displaySources = sources || [];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            Sources Manager
          </CardTitle>
          <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add Source
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>Add New Source</DialogTitle>
                <DialogDescription>
                  Add a Savee.com URL to start scraping content. The system will
                  automatically detect the source type and configure optimal
                  settings.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="url">Savee.com URL</Label>
                  <Input
                    id="url"
                    placeholder="https://savee.com/..."
                    value={newUrl}
                    onChange={(e) => handleUrlChange(e.target.value)}
                  />
                </div>

                {detectedType && (
                  <div className="p-4 bg-blue-50 dark:bg-blue-950/20 rounded-lg border">
                    <div className="flex items-center gap-2 mb-2">
                      <detectedType.icon className="h-5 w-5 text-blue-600" />
                      <span className="font-medium text-blue-900 dark:text-blue-100">
                        {detectedType.label} Detected
                      </span>
                    </div>

                    <div className="space-y-2 text-sm">
                      <p className="text-blue-800 dark:text-blue-200">
                        {detectedType.description}
                      </p>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <span className="font-medium">Frontend Route:</span>
                          <br />
                          <code className="text-xs bg-blue-100 dark:bg-blue-900 px-1 rounded">
                            {detectedType.frontendRoute}
                          </code>
                        </div>
                        <div>
                          <span className="font-medium">Scrape Interval:</span>
                          <br />
                          <span className="text-blue-700 dark:text-blue-300">
                            {detectedType.defaultInterval}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex justify-end gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setIsAddDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleAddSource}
                    disabled={
                      !newUrl.trim() ||
                      !detectedType ||
                      addSourceMutation.isPending
                    }
                  >
                    {addSourceMutation.isPending ? "Adding..." : "Add Source"}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-20 bg-muted animate-pulse rounded" />
            ))}
          </div>
        ) : displaySources.length > 0 ? (
          <div className="space-y-4">
            {displaySources.map((source) => (
              <div key={source.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-3">
                      {getSourceIcon(source.type)}
                      <span className="font-semibold">{source.name}</span>
                      <Badge variant={source.enabled ? "default" : "secondary"}>
                        {source.status}
                      </Badge>
                      <Badge variant="outline">{source.type}</Badge>
                    </div>

                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>{source.url}</span>
                      <Button variant="ghost" size="sm" asChild>
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </Button>
                    </div>

                    <div className="text-xs text-muted-foreground">
                      Next run:{" "}
                      {source.next_run_at
                        ? new Date(source.next_run_at).toLocaleString()
                        : "Not scheduled"}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-2">
                      <Label
                        htmlFor={`toggle-${source.id}`}
                        className="text-sm"
                      >
                        Enabled
                      </Label>
                      <Switch
                        id={`toggle-${source.id}`}
                        checked={source.enabled}
                        onCheckedChange={(enabled) =>
                          toggleSourceMutation.mutate({
                            sourceId: source.id,
                            enabled,
                          })
                        }
                      />
                    </div>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        triggerSweepMutation.mutate({
                          sourceId: source.id,
                          sweepType: "tail",
                        })
                      }
                      disabled={!source.enabled}
                    >
                      <Play className="h-4 w-4 mr-2" />
                      Run Now
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        triggerSweepMutation.mutate({
                          sourceId: source.id,
                          sweepType: "backfill",
                        })
                      }
                      disabled={!source.enabled}
                    >
                      <TrendingUp className="h-4 w-4 mr-2" />
                      Backfill
                    </Button>

                    <Button variant="ghost" size="sm">
                      <Settings className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <Globe className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Sources Added</h3>
            <p className="text-muted-foreground mb-4">
              Add your first Savee.com source to start scraping content
            </p>
            <Button onClick={() => setIsAddDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add First Source
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
