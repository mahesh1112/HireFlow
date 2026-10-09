"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/layouts/Header";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { jobsApi } from "@/lib/api/jobs";
import type { JobDescription, JobStatus } from "@/lib/types";
import {
  Plus,
  Eye,
  Pencil,
  Play,
  Pause,
  CheckCircle,
  Calendar,
  Search,
  Filter,
  X,
  Check,
} from "lucide-react";
import toast from "react-hot-toast";

function JobStatusBadge({ status }: { status: JobStatus }) {
  const config: Record<JobStatus, { label: string; cls: string }> = {
    active: { label: "Active", cls: "bg-green-100 text-green-800 border-green-200" },
    expired: { label: "Expired", cls: "bg-red-100 text-red-800 border-red-200" },
    filled: { label: "Filled", cls: "bg-gray-100 text-gray-600 border-gray-200" },
    paused: { label: "Paused", cls: "bg-yellow-100 text-yellow-800 border-yellow-200" },
  };
  const { label, cls } = config[status] ?? config.active;
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${cls}`}>
      {label}
    </span>
  );
}

function effectiveStatus(job: JobDescription): JobStatus {
  if (job.status === "active" && job.valid_till) {
    if (new Date(job.valid_till) < new Date()) return "expired";
  }
  return (job.status as JobStatus) ?? "active";
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobDescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [actioning, setActioning] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Extend date
  const [extendingJobId, setExtendingJobId] = useState<string | null>(null);
  const [extendDate, setExtendDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 30);
    return d.toISOString().split("T")[0];
  });

  const loadJobs = async () => {
    setLoading(true);
    try {
      const resp = await jobsApi.listJobs(1, 100);
      setJobs(resp.items);
    } catch {
      toast.error("Failed to load jobs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  // Client-side filtering
  const filteredJobs = jobs.filter((job) => {
    const st = effectiveStatus(job);
    if (statusFilter !== "all" && st !== statusFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      if (
        !job.job_title.toLowerCase().includes(q) &&
        !(job.company && job.company.toLowerCase().includes(q)) &&
        !job.job_id.toLowerCase().includes(q)
      ) {
        return false;
      }
    }
    return true;
  });

  const hasActiveFilters = searchQuery.trim() !== "" || statusFilter !== "all";

  const clearFilters = () => {
    setSearchQuery("");
    setStatusFilter("all");
  };

  const handleAction = async (
    jobId: string,
    action: "activate" | "pause" | "fill"
  ) => {
    setActioning(jobId);
    try {
      const updated = await jobsApi.updateJobStatus(jobId, { action });
      setJobs((prev) =>
        prev.map((j) => (j.job_id === updated.job_id ? updated : j))
      );
      toast.success(
        action === "activate"
          ? "Job activated (+30 days)"
          : action === "pause"
          ? "Job paused"
          : "Job marked as filled"
      );
    } catch {
      toast.error(`Failed to ${action} job`);
    } finally {
      setActioning(null);
    }
  };

  const handleExtendDate = async (jobId: string) => {
    if (!extendDate) {
      toast.error("Please select a new date");
      return;
    }
    const selectedDate = new Date(extendDate);
    if (selectedDate <= new Date()) {
      toast.error("Please select a future date");
      return;
    }
    setActioning(jobId);
    try {
      const updated = await jobsApi.updateJobStatus(jobId, {
        action: "activate",
        valid_till: new Date(extendDate).toISOString(),
      });
      setJobs((prev) =>
        prev.map((j) => (j.job_id === updated.job_id ? updated : j))
      );
      setExtendingJobId(null);
      toast.success("Job posting extended successfully!");
    } catch {
      toast.error("Failed to extend job posting");
    } finally {
      setActioning(null);
    }
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Header title="Jobs" subtitle="Manage your active job postings" />
      <div className="flex-1 p-8 space-y-6">
        {/* Top bar: search + new job */}
        <div className="flex items-center justify-between gap-4">
          <div className="relative w-80">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="Search by title, company, or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <Link href="/jobs/new">
            <Button>
              <Plus className="w-4 h-4" />
              New Job Posting
            </Button>
          </Link>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5 text-sm text-gray-500">
            <Filter className="w-4 h-4" />
            Filters:
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All</option>
            <option value="active">Active</option>
            <option value="expired">Expired</option>
            <option value="paused">Paused</option>
            <option value="filled">Filled</option>
          </select>
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              <X className="w-3 h-3" />
              Clear
            </Button>
          )}
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              All Job Postings{" "}
              {!loading && (
                <span className="text-gray-400 font-normal">
                  ({filteredJobs.length}{hasActiveFilters ? ` of ${jobs.length}` : ""})
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center py-12">
                <div className="spinner w-6 h-6" />
              </div>
            ) : filteredJobs.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                {hasActiveFilters ? (
                  <>
                    <Filter className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                    <p className="font-medium">No jobs match the current filters</p>
                    <Button size="sm" variant="outline" className="mt-3" onClick={clearFilters}>
                      Clear Filters
                    </Button>
                  </>
                ) : (
                  <>
                    <p className="font-medium">No job postings yet</p>
                    <Link href="/jobs/new" className="mt-3 inline-block">
                      <Button size="sm">Create your first job</Button>
                    </Link>
                  </>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 text-left">
                      <th className="pb-3 pr-4 text-gray-500 font-medium">Title</th>
                      <th className="pb-3 pr-4 text-gray-500 font-medium">Company</th>
                      <th className="pb-3 pr-4 text-gray-500 font-medium">Unit</th>
                      <th className="pb-3 pr-4 text-gray-500 font-medium">Job ID</th>
                      <th className="pb-3 pr-4 text-gray-500 font-medium">Recruiter</th>
                      <th className="pb-3 pr-4 text-gray-500 font-medium">Uploaded</th>
                      <th className="pb-3 pr-4 text-gray-500 font-medium">Valid Till</th>
                      <th className="pb-3 pr-4 text-gray-500 font-medium">Status</th>
                      <th className="pb-3 text-gray-500 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {filteredJobs.map((job) => {
                      const st = effectiveStatus(job);
                      const busy = actioning === job.job_id;
                      return (
                        <tr key={job.job_id} className="hover:bg-gray-50 transition-colors">
                          <td className="py-3 pr-4 font-medium text-gray-900">
                            {job.job_title}
                          </td>
                          <td className="py-3 pr-4 text-gray-600">{job.company ?? "—"}</td>
                          <td className="py-3 pr-4 text-gray-600">{job.unit_name ?? "—"}</td>
                          <td className="py-3 pr-4 text-gray-700 font-mono text-xs font-semibold">
                            {job.job_id}
                          </td>
                          <td className="py-3 pr-4 text-gray-600">{job.recruiter_name ?? "—"}</td>
                          <td className="py-3 pr-4 text-gray-500 text-xs">
                            {new Date(job.created_at).toLocaleDateString()}
                          </td>
                          <td className="py-3 pr-4 text-gray-500 text-xs">
                            {job.valid_till
                              ? new Date(job.valid_till).toLocaleDateString()
                              : "—"}
                          </td>
                          <td className="py-3 pr-4">
                            <JobStatusBadge status={st} />
                          </td>
                          <td className="py-3">
                            <div className="flex items-center gap-1.5">
                              <Link href={`/jobs/${job.job_id}`}>
                                <Button size="sm" variant="ghost" title="View">
                                  <Eye className="w-3 h-3" />
                                </Button>
                              </Link>
                              <Link href={`/jobs/${job.job_id}/edit`}>
                                <Button size="sm" variant="ghost" title="Edit">
                                  <Pencil className="w-3 h-3" />
                                </Button>
                              </Link>
                              {st === "expired" && (
                                <>
                                  {extendingJobId === job.job_id ? (
                                    <div className="flex items-center gap-1">
                                      <input
                                        type="date"
                                        className="px-2 py-1 text-xs rounded border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        value={extendDate}
                                        onChange={(e) => setExtendDate(e.target.value)}
                                        min={new Date().toISOString().split("T")[0]}
                                      />
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        disabled={busy}
                                        onClick={() => handleExtendDate(job.job_id)}
                                        title="Confirm extend"
                                        className="text-green-600 hover:text-green-700 hover:bg-green-50"
                                      >
                                        <Check className="w-3 h-3" />
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => setExtendingJobId(null)}
                                        title="Cancel"
                                      >
                                        <X className="w-3 h-3" />
                                      </Button>
                                    </div>
                                  ) : (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      disabled={busy}
                                      onClick={() => setExtendingJobId(job.job_id)}
                                      title="Extend posting date"
                                    >
                                      <Calendar className="w-3 h-3" />
                                    </Button>
                                  )}
                                </>
                              )}
                              {(st === "paused") && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  disabled={busy}
                                  onClick={() => handleAction(job.job_id, "activate")}
                                  title="Activate (+30 days)"
                                >
                                  <Play className="w-3 h-3" />
                                </Button>
                              )}
                              {st === "active" && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  disabled={busy}
                                  onClick={() => handleAction(job.job_id, "pause")}
                                  title="Pause"
                                >
                                  <Pause className="w-3 h-3" />
                                </Button>
                              )}
                              {(st === "active" || st === "paused") && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  disabled={busy}
                                  onClick={() => handleAction(job.job_id, "fill")}
                                  title="Mark Filled"
                                >
                                  <CheckCircle className="w-3 h-3" />
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
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
