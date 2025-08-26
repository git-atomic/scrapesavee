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
        { title: "Overview", url: "/" },
      ],
    },
    {
      title: "Sources",
      url: "/",
      icon: Globe,
      items: [],
    },
    {
      title: "Media Library",
      url: "/",
      icon: Images,
      items: [],
    },
  ],
  projects: [
    {
      name: "System Health",
      url: "/",
      icon: Activity,
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
