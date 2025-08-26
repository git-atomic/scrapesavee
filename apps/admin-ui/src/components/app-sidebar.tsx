"use client";

import * as React from "react";
import {
  Activity,
  BarChart3,
  Database,
  FileText,
  Folder,
  Globe,
  Images,
  Play,
  Settings,
  Users,
  Zap,
} from "lucide-react";

import { NavMain } from "@/components/nav-main";
import { NavProjects } from "@/components/nav-projects";
import { NavUser } from "@/components/nav-user";
import { TeamSwitcher } from "@/components/team-switcher";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
} from "@/components/ui/sidebar";

// ScrapeSavee Engine navigation data
const data = {
  user: {
    name: "Engine Admin",
    email: "admin@scrapesavee.com",
    avatar: "/avatars/engine-admin.jpg",
  },
  teams: [
    {
      name: "ScrapeSavee Engine",
      logo: Zap,
      plan: "Production",
    },
  ],
  navMain: [
    {
      title: "Dashboard",
      url: "/",
      icon: BarChart3,
      isActive: true,
      items: [
        {
          title: "Overview",
          url: "/",
        },
        {
          title: "Analytics",
          url: "/analytics",
        },
        {
          title: "Reports",
          url: "/reports",
        },
      ],
    },
    {
      title: "Jobs Manager",
      url: "/jobs",
      icon: Play,
      items: [
        {
          title: "Running Jobs",
          url: "/jobs/running",
        },
        {
          title: "Queued Jobs",
          url: "/jobs/queued",
        },
        {
          title: "Completed",
          url: "/jobs/completed",
        },
        {
          title: "Failed Jobs",
          url: "/jobs/failed",
        },
      ],
    },
    {
      title: "Sources",
      url: "/sources",
      icon: Globe,
      items: [
        {
          title: "All Sources",
          url: "/sources",
        },
        {
          title: "Savee Home",
          url: "/sources/home",
        },
        {
          title: "Trending",
          url: "/sources/trending",
        },
        {
          title: "User Profiles",
          url: "/sources/users",
        },
        {
          title: "Add New",
          url: "/sources/new",
        },
      ],
    },
    {
      title: "Media Library",
      url: "/media",
      icon: Images,
      items: [
        {
          title: "All Media",
          url: "/media",
        },
        {
          title: "Images",
          url: "/media/images",
        },
        {
          title: "Videos",
          url: "/media/videos",
        },
        {
          title: "Storage Stats",
          url: "/media/storage",
        },
      ],
    },
    {
      title: "Content",
      url: "/content",
      icon: FileText,
      items: [
        {
          title: "All Blocks",
          url: "/content/blocks",
        },
        {
          title: "Published",
          url: "/content/published",
        },
        {
          title: "Draft",
          url: "/content/draft",
        },
        {
          title: "Review Queue",
          url: "/content/review",
        },
      ],
    },
    {
      title: "Users",
      url: "/users",
      icon: Users,
      items: [
        {
          title: "Discovered Users",
          url: "/users/discovered",
        },
        {
          title: "Popular Users",
          url: "/users/popular",
        },
        {
          title: "User Analytics",
          url: "/users/analytics",
        },
      ],
    },
  ],
  projects: [
    {
      name: "Database",
      url: "/database",
      icon: Database,
    },
    {
      name: "System Health",
      url: "/health",
      icon: Activity,
    },
    {
      name: "Settings",
      url: "/settings",
      icon: Settings,
    },
    {
      name: "Logs",
      url: "/logs",
      icon: Folder,
    },
  ],
};

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <TeamSwitcher teams={data.teams} />
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={data.navMain} />
        <NavProjects projects={data.projects} />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={data.user} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
