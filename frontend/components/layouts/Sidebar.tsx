"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
import {
  LayoutDashboard,
  Upload,
  Search,
  Users,
  LogOut,
  Briefcase,
  FileText,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/resumes", label: "Resumes", icon: FileText },
  { href: "/upload", label: "Upload Resumes", icon: Upload },
  { href: "/screen", label: "Screen Candidates", icon: Search },
  { href: "/shortlist", label: "Shortlist", icon: Users },
];

export function Sidebar() {
  const pathname = usePathname();
  const { data: session } = useSession();

  return (
    <aside className="flex flex-col w-64 min-h-screen bg-gray-900 text-white">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-gray-700">
        <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-blue-600">
          <Briefcase className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-white">HireFlow</h1>
          <p className="text-xs text-gray-400">Resume Screening</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors group",
                isActive
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:bg-gray-800 hover:text-white"
              )}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
              {isActive && <ChevronRight className="ml-auto w-4 h-4" />}
            </Link>
          );
        })}
      </nav>

      {/* User info + logout */}
      <div className="px-4 py-4 border-t border-gray-700">
        <div className="flex items-center gap-3 mb-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-600 text-white text-sm font-semibold">
            {session?.user?.name?.[0]?.toUpperCase() ?? "R"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">
              {session?.user?.name ?? "Recruiter"}
            </p>
            <p className="text-xs text-gray-400 truncate">
              {session?.user?.email ?? ""}
            </p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="w-full text-gray-400 hover:text-white hover:bg-gray-800 justify-start"
          onClick={() => signOut({ callbackUrl: "/auth/login" })}
        >
          <LogOut className="w-4 h-4" />
          Sign Out
        </Button>
      </div>
    </aside>
  );
}
