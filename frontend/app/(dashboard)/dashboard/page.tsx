"use client";
import { useEffect, useState } from "react";
import { Header } from "@/components/layouts/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { adminApi } from "@/lib/api/admin";
import type { DashboardStats } from "@/lib/types";
import {
  FileText,
  Briefcase,
  Users,
  TrendingUp,
  Upload,
  Search,
  BarChart3,
  RefreshCw,
} from "lucide-react";
import Link from "next/link";
import toast from "react-hot-toast";

function StatCard({
  title,
  value,
  icon: Icon,
  color,
  subtitle,
}: {
  title: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  subtitle?: string;
}) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500 font-medium">{title}</p>
            <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
            {subtitle && (
              <p className="text-xs text-gray-400 mt-1">{subtitle}</p>
            )}
          </div>
          <div className={`p-3 rounded-xl ${color}`}>
            <Icon className="w-6 h-6 text-white" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  const loadStats = async () => {
    setLoading(true);
    try {
      const data = await adminApi.getStats();
      setStats(data);
    } catch {
      toast.error("Failed to load dashboard stats");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  return (
    <div className="flex flex-col min-h-screen">
      <Header
        title="Dashboard"
        subtitle="Overview of your resume screening activity"
      />

      <div className="flex-1 p-8 space-y-8">
        {/* Quick Actions */}
        <div className="flex flex-wrap gap-3">
          <Link href="/upload">
            <Button>
              <Upload className="w-4 h-4" />
              Upload Resumes
            </Button>
          </Link>
          <Link href="/screen">
            <Button variant="outline">
              <Search className="w-4 h-4" />
              Screen Candidates
            </Button>
          </Link>
          <Button variant="ghost" onClick={loadStats} isLoading={loading}>
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
        </div>

        {/* Stats Grid */}
        {loading && !stats ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="p-6">
                  <div className="animate-pulse space-y-3">
                    <div className="h-4 bg-gray-200 rounded w-2/3" />
                    <div className="h-8 bg-gray-200 rounded w-1/2" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard
              title="Total Resumes"
              value={stats?.total_resumes.toLocaleString() ?? 0}
              icon={FileText}
              color="bg-blue-500"
              subtitle="Resumes indexed"
            />
            <StatCard
              title="Active Jobs"
              value={stats?.total_jobs ?? 0}
              icon={Briefcase}
              color="bg-purple-500"
              subtitle="Job descriptions"
            />
            <StatCard
              title="Shortlisted"
              value={stats?.total_shortlisted ?? 0}
              icon={Users}
              color="bg-green-500"
              subtitle="Candidates shortlisted"
            />
            <StatCard
              title="Shortlist Rate"
              value={`${stats?.shortlist_rate?.toFixed(1) ?? 0}%`}
              icon={TrendingUp}
              color="bg-orange-500"
              subtitle="Match rate"
            />
          </div>
        )}

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Top Skills Matched */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <BarChart3 className="w-5 h-5 text-green-500" />
                Top Skills Matched
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!stats?.top_skills_matched?.length ? (
                <p className="text-sm text-gray-400">No screening data yet</p>
              ) : (
                <div className="space-y-3">
                  {stats.top_skills_matched.slice(0, 6).map((s) => (
                    <div key={s.skill} className="flex items-center gap-3">
                      <span className="text-sm text-gray-700 w-24 shrink-0">
                        {s.skill}
                      </span>
                      <div className="flex-1 bg-gray-100 rounded-full h-2">
                        <div
                          className="bg-green-500 h-2 rounded-full"
                          style={{ width: `${s.percentage}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 w-10 text-right">
                        {s.percentage}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Top Skills Missing */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <BarChart3 className="w-5 h-5 text-red-500" />
                Top Skills Missing
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!stats?.top_skills_missing?.length ? (
                <p className="text-sm text-gray-400">No screening data yet</p>
              ) : (
                <div className="space-y-3">
                  {stats.top_skills_missing.slice(0, 6).map((s) => (
                    <div key={s.skill} className="flex items-center gap-3">
                      <span className="text-sm text-gray-700 w-24 shrink-0">
                        {s.skill}
                      </span>
                      <div className="flex-1 bg-gray-100 rounded-full h-2">
                        <div
                          className="bg-red-400 h-2 rounded-full"
                          style={{ width: `${s.percentage}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 w-10 text-right">
                        {s.percentage}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Recent Jobs */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Job Screenings</CardTitle>
          </CardHeader>
          <CardContent>
            {!stats?.recent_jobs?.length ? (
              <div className="text-center py-8">
                <Search className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500 text-sm">No screenings yet</p>
                <Link href="/screen" className="mt-3 inline-block">
                  <Button size="sm">Start Screening</Button>
                </Link>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left border-b border-gray-100">
                      <th className="pb-3 text-gray-500 font-medium">Job Title</th>
                      <th className="pb-3 text-gray-500 font-medium">Screenings</th>
                      <th className="pb-3 text-gray-500 font-medium">Date</th>
                      <th className="pb-3 text-gray-500 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {stats.recent_jobs.map((job) => (
                      <tr key={job.job_id} className="hover:bg-gray-50">
                        <td className="py-3 font-medium text-gray-900">
                          {job.job_title}
                        </td>
                        <td className="py-3 text-gray-600">
                          {job.screening_count}
                        </td>
                        <td className="py-3 text-gray-500">
                          {new Date(job.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-3">
                          <Link href={`/shortlist?job_id=${job.job_id}`}>
                            <Button size="sm" variant="ghost">
                              View Results
                            </Button>
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
