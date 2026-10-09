"use client";
import { Bell, HelpCircle } from "lucide-react";
import { useSession } from "next-auth/react";

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  const { data: session } = useSession();

  return (
    <header className="flex items-center justify-between px-8 py-4 bg-white border-b border-gray-200">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
        {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-3">
        <button className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
        </button>
        <button className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg">
          <HelpCircle className="w-5 h-5" />
        </button>
        <div className="w-px h-6 bg-gray-200" />
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-600 text-white text-sm font-semibold">
            {session?.user?.name?.[0]?.toUpperCase() ?? "R"}
          </div>
          <span className="text-sm font-medium text-gray-700 hidden sm:block">
            {session?.user?.name ?? "Recruiter"}
          </span>
        </div>
      </div>
    </header>
  );
}
