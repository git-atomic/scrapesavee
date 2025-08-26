"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Images,
  Video,
  Download,
  ExternalLink,
  Eye,
  Filter,
  Grid3X3,
  List,
  Search,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { workerApi } from "@/lib/api";

interface MediaItem {
  id: string;
  external_id: string;
  title: string;
  media_type: "image" | "video";
  thumbnail_url: string;
  original_url: string;
  source_page_url: string;
  file_size: number;
  width: number;
  height: number;
  created_at: string;
  tags: string[];
  color_palette: string[];
}

export function MediaLibrary() {
  const [searchTerm, setSearchTerm] = useState("");
  const [mediaType, setMediaType] = useState<"all" | "image" | "video">("all");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [selectedItem, setSelectedItem] = useState<MediaItem | null>(null);

  const { data: mediaItems, isLoading } = useQuery({
    queryKey: ["media", searchTerm, mediaType],
    queryFn: async () => {
      const res = await workerApi.getMedia({
        search: searchTerm,
        type: mediaType,
      });
      return res.data;
    },
    refetchInterval: 30000,
  });

  const { data: storageStats } = useQuery({
    queryKey: ["storage-stats"],
    queryFn: async () => {
      const res = await workerApi.getStorageStats();
      return res.data;
    },
    refetchInterval: 60000,
  });

  const displayItems = mediaItems || [];
  const filteredItems = displayItems.filter((item) => {
    const matchesSearch =
      !searchTerm ||
      item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.tags.some((tag) =>
        tag.toLowerCase().includes(searchTerm.toLowerCase())
      );

    const matchesType = mediaType === "all" || item.media_type === mediaType;

    return matchesSearch && matchesType;
  });

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const stats =
    storageStats ||
    ({
      total_items: 0,
      total_size_gb: 0,
      images: 0,
      videos: 0,
      storage_used_percent: 0,
    } as any);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Images className="h-5 w-5" />
            Media Library
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant={viewMode === "grid" ? "default" : "outline"}
              size="sm"
              onClick={() => setViewMode("grid")}
            >
              <Grid3X3 className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === "list" ? "default" : "outline"}
              size="sm"
              onClick={() => setViewMode("list")}
            >
              <List className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Storage Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold">{stats.total_items}</div>
              <p className="text-xs text-muted-foreground">Total Items</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold">{stats.total_size_gb}GB</div>
              <p className="text-xs text-muted-foreground">Storage Used</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold">{stats.images}</div>
              <p className="text-xs text-muted-foreground">Images</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold">{stats.videos}</div>
              <p className="text-xs text-muted-foreground">Videos</p>
            </CardContent>
          </Card>
        </div>

        {/* Storage Usage Progress */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>Storage Usage</span>
            <span>{stats.storage_used_percent}%</span>
          </div>
          <Progress value={stats.storage_used_percent} />
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search media..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>

          <Select
            value={mediaType}
            onValueChange={(value: any) => setMediaType(value)}
          >
            <SelectTrigger className="w-full sm:w-[180px]">
              <SelectValue placeholder="Media type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Media</SelectItem>
              <SelectItem value="image">Images Only</SelectItem>
              <SelectItem value="video">Videos Only</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Media Grid/List */}
        {isLoading ? (
          <div
            className={
              viewMode === "grid"
                ? "grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
                : "space-y-4"
            }
          >
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={i}
                className="aspect-square bg-muted animate-pulse rounded-lg"
              />
            ))}
          </div>
        ) : filteredItems.length > 0 ? (
          <div
            className={
              viewMode === "grid"
                ? "grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
                : "space-y-4"
            }
          >
            {filteredItems.map((item) => (
              <div
                key={item.id}
                className={
                  viewMode === "grid"
                    ? "group relative aspect-square bg-muted rounded-lg overflow-hidden cursor-pointer hover:shadow-lg transition-shadow"
                    : "flex items-center gap-4 p-4 border rounded-lg hover:shadow-sm transition-shadow"
                }
              >
                {viewMode === "grid" ? (
                  <>
                    <img
                      src={item.thumbnail_url}
                      alt={item.title}
                      className="w-full h-full object-cover"
                      onClick={() => setSelectedItem(item)}
                    />

                    <div className="absolute top-2 right-2">
                      <Badge
                        variant={
                          item.media_type === "image" ? "default" : "secondary"
                        }
                      >
                        {item.media_type === "image" ? (
                          <Images className="h-3 w-3" />
                        ) : (
                          <Video className="h-3 w-3" />
                        )}
                      </Badge>
                    </div>

                    <div className="absolute inset-x-0 bottom-0 bg-black/60 text-white p-2 transform translate-y-full group-hover:translate-y-0 transition-transform">
                      <p className="text-sm font-medium truncate">
                        {item.title}
                      </p>
                      <p className="text-xs text-gray-300">
                        {formatFileSize(item.file_size)}
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <img
                      src={item.thumbnail_url}
                      alt={item.title}
                      className="w-16 h-16 object-cover rounded"
                    />

                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium">{item.title}</h3>
                        <Badge
                          variant={
                            item.media_type === "image"
                              ? "default"
                              : "secondary"
                          }
                        >
                          {item.media_type}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {item.width} × {item.height} •{" "}
                        {formatFileSize(item.file_size)}
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {item.tags.slice(0, 3).map((tag) => (
                          <Badge
                            key={tag}
                            variant="outline"
                            className="text-xs"
                          >
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedItem(item)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="sm" asChild>
                        <a
                          href={item.source_page_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      </Button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <Images className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Media Found</h3>
            <p className="text-muted-foreground">
              {searchTerm
                ? "Try adjusting your search terms"
                : "Media will appear here as sources are scraped"}
            </p>
          </div>
        )}

        {/* Media Detail Dialog */}
        <Dialog
          open={!!selectedItem}
          onOpenChange={() => setSelectedItem(null)}
        >
          <DialogContent className="max-w-4xl">
            {selectedItem && (
              <>
                <DialogHeader>
                  <DialogTitle>{selectedItem.title}</DialogTitle>
                  <DialogDescription>
                    {selectedItem.media_type.charAt(0).toUpperCase() +
                      selectedItem.media_type.slice(1)}{" "}
                    •{selectedItem.width} × {selectedItem.height} •
                    {formatFileSize(selectedItem.file_size)}
                  </DialogDescription>
                </DialogHeader>

                <div className="space-y-4">
                  <div className="aspect-video bg-muted rounded-lg overflow-hidden">
                    <img
                      src={selectedItem.original_url}
                      alt={selectedItem.title}
                      className="w-full h-full object-contain"
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <h4 className="font-semibold mb-2">Tags</h4>
                      <div className="flex flex-wrap gap-2">
                        {selectedItem.tags.map((tag) => (
                          <Badge key={tag} variant="outline">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h4 className="font-semibold mb-2">Color Palette</h4>
                      <div className="flex gap-2">
                        {selectedItem.color_palette.map((color, index) => (
                          <div
                            key={index}
                            className="w-8 h-8 rounded border"
                            style={{ backgroundColor: color }}
                            title={color}
                          />
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-end gap-2">
                    <Button variant="outline" asChild>
                      <a
                        href={selectedItem.source_page_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <ExternalLink className="h-4 w-4 mr-2" />
                        View Original
                      </a>
                    </Button>
                    <Button asChild>
                      <a href={selectedItem.original_url} download>
                        <Download className="h-4 w-4 mr-2" />
                        Download
                      </a>
                    </Button>
                  </div>
                </div>
              </>
            )}
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}
