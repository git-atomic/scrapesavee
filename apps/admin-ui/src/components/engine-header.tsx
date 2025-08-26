"use client";

import {
  Bell,
  Play,
  Pause,
  RefreshCw,
  Settings,
  Zap,
  Database,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { useEngineStatus } from "@/hooks/use-engine-status";

export function EngineHeader() {
  const { status, isRunning, toggleEngine } = useEngineStatus();

  return (
    <header className="flex h-16 shrink-0 items-center gap-2 transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-12 border-b">
      <div className="flex items-center gap-2 px-4 flex-1">
        <SidebarTrigger className="-ml-1" />
        <Separator orientation="vertical" className="mr-2 h-4" />

        {/* Breadcrumb */}
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem className="hidden md:block">
              <BreadcrumbLink href="/" className="flex items-center gap-2">
                <Zap className="h-4 w-4" />
                ScrapeSavee Engine
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator className="hidden md:block" />
            <BreadcrumbItem>
              <BreadcrumbPage>Dashboard</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>

      {/* Engine Status & Controls */}
      <div className="flex items-center gap-3 px-4">
        {/* Engine Status */}
        <div className="flex items-center gap-2">
          <Badge
            variant={isRunning ? "default" : "secondary"}
            className="flex items-center gap-1"
          >
            <div
              className={`w-2 h-2 rounded-full ${
                isRunning ? "bg-green-500 animate-pulse" : "bg-gray-400"
              }`}
            />
            {status}
          </Badge>
        </div>

        {/* Engine Controls */}
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            onClick={toggleEngine}
            className="flex items-center gap-2"
          >
            {isRunning ? (
              <>
                <Pause className="h-4 w-4" />
                <span className="hidden sm:inline">Pause Engine</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                <span className="hidden sm:inline">Start Engine</span>
              </>
            )}
          </Button>

          <Button variant="outline" size="sm">
            <RefreshCw className="h-4 w-4" />
            <span className="hidden sm:inline ml-2">Refresh</span>
          </Button>
        </div>

        {/* Notifications placeholder removed for production cleanliness */}

        {/* Settings */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm">
              <Settings className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Engine Settings</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <Settings className="h-4 w-4 mr-2" />
              General Settings
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Database className="h-4 w-4 mr-2" />
              Database Config
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Zap className="h-4 w-4 mr-2" />
              Performance
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
