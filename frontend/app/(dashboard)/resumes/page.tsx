"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { Header } from "@/components/layouts/Header";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { resumesApi } from "@/lib/api/resumes";
import { unitsApi } from "@/lib/api/units";
import { jobsApi } from "@/lib/api/jobs";
import type { Resume, BusinessUnit } from "@/lib/types";
import {
  CheckCircle2,
  MinusCircle,
  Eye,
  RefreshCw,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Search,
  Upload,
  CheckSquare,
  Square,
  X,
  Filter,
} from "lucide-react";
import toast from "react-hot-toast";

function ParseStatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; cls: string }> = {
    completed: { label: "Parsed", cls: "bg-green-100 text-green-800 border-green-200" },
    processing: { label: "Processing", cls: "bg-yellow-100 text-yellow-800 border-yellow-200" },
    pending: { label: "Pending", cls: "bg-gray-100 text-gray-600 border-gray-200" },
    failed: { label: "Failed", cls: "bg-red-100 text-red-800 border-red-200" },
  };
  const { label, cls } = config[status] ?? config.pending;
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${cls}`}>
      {label}
    </span>
  );
}

function IndexedIndicator({ indexed }: { indexed: boolean }) {
  return indexed ? (
    <span className="inline-flex items-center gap-1 text-green-600 text-xs font-medium">
      <CheckCircle2 className="w-3.5 h-3.5" />
      Yes
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-gray-400 text-xs">
      <MinusCircle className="w-3.5 h-3.5" />
      No
    </span>
  );
}

interface Filters {
  parse_status?: string;
  unit_id?: string;
  job_position_id?: string;
  is_indexed?: boolean;
  search?: string;
}

export default function ResumesPage() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [actioningId, setActioningId] = useState<string | null>(null);
  const [reparsingAll, setReparsingAll] = useState(false);
  const pageSize = 20;

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [parseStatusFilter, setParseStatusFilter] = useState("all");
  const [unitFilter, setUnitFilter] = useState("all");
  const [jobFilter, setJobFilter] = useState("all");
  const [indexedFilter, setIndexedFilter] = useState("all");

  // Filter options
  const [units, setUnits] = useState<BusinessUnit[]>([]);
  const [jobs, setJobs] = useState<{ job_id: string; job_title: string }[]>([]);

  // Multi-selection
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [bulkReparsing, setBulkReparsing] = useState(false);

  // Debounce search
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const buildFilters = useCallback((): Filters => {
    const filters: Filters = {};
    if (parseStatusFilter !== "all") filters.parse_status = parseStatusFilter;
    if (unitFilter !== "all") filters.unit_id = unitFilter;
    if (jobFilter !== "all") filters.job_position_id = jobFilter;
    if (indexedFilter === "yes") filters.is_indexed = true;
    else if (indexedFilter === "no") filters.is_indexed = false;
    if (searchQuery.trim()) filters.search = searchQuery.trim();
    return filters;
  }, [parseStatusFilter, unitFilter, jobFilter, indexedFilter, searchQuery]);

  const loadResumes = useCallback(async (p: number) => {
    setLoading(true);
    try {
      const resp = await resumesApi.listResumes(p, pageSize, buildFilters());
      setResumes(resp.items);
      setTotal(resp.total);
      setTotalPages(resp.total_pages);
      setPage(resp.page);
    } catch {
      toast.error("Failed to load resumes");
    } finally {
      setLoading(false);
    }
  }, [buildFilters]);

  // Load filter options on mount
  useEffect(() => {
    unitsApi.listUnits().then(setUnits).catch(() => {});
    jobsApi.listJobs(1, 100).then((r) =>
      setJobs(r.items.map((j) => ({ job_id: j.job_id, job_title: j.job_title })))
    ).catch(() => {});
  }, []);

  // Load resumes when filters change (except search, which is debounced)
  useEffect(() => {
    setSelectedIds(new Set());
    loadResumes(1);
  }, [parseStatusFilter, unitFilter, jobFilter, indexedFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounced search
  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      setSelectedIds(new Set());
      loadResumes(1);
    }, 400);
    return () => {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    };
  }, [searchQuery]); // eslint-disable-line react-hooks/exhaustive-deps

  const hasActiveFilters =
    parseStatusFilter !== "all" ||
    unitFilter !== "all" ||
    jobFilter !== "all" ||
    indexedFilter !== "all" ||
    searchQuery.trim() !== "";

  const clearFilters = () => {
    setSearchQuery("");
    setParseStatusFilter("all");
    setUnitFilter("all");
    setJobFilter("all");
    setIndexedFilter("all");
  };

  // Selection helpers
  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === resumes.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(resumes.map((r) => r.id)));
    }
  };

  // Page change clears selection
  const goToPage = (p: number) => {
    setSelectedIds(new Set());
    loadResumes(p);
  };

  const handleViewFile = async (resumeId: string) => {
    try {
      const blob = await resumesApi.getResumeFile(resumeId);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank");
    } catch {
      toast.error("Failed to load resume file");
    }
  };

  const handleReparse = async (resumeId: string) => {
    setActioningId(resumeId);
    try {
      await resumesApi.reparse(resumeId);
      toast.success("Re-parse initiated");
      setTimeout(() => loadResumes(page), 1500);
    } catch {
      toast.error("Failed to re-parse resume");
    } finally {
      setActioningId(null);
    }
  };

  const handleDelete = async (resumeId: string) => {
    if (!confirm("Delete this resume? This cannot be undone.")) return;
    setActioningId(resumeId);
    try {
      await resumesApi.deleteResume(resumeId);
      toast.success("Resume deleted");
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(resumeId);
        return next;
      });
      loadResumes(page);
    } catch {
      toast.error("Failed to delete resume");
    } finally {
      setActioningId(null);
    }
  };

  const handleBulkDelete = async () => {
    const count = selectedIds.size;
    if (!confirm(`Delete ${count} selected resume(s)? This cannot be undone.`)) return;
    setBulkDeleting(true);
    try {
      const resp = await resumesApi.bulkDelete(Array.from(selectedIds));
      toast.success(`Deleted ${resp.deleted} resume(s)`);
      setSelectedIds(new Set());
      loadResumes(page);
    } catch {
      toast.error("Failed to delete resumes");
    } finally {
      setBulkDeleting(false);
    }
  };

  const handleBulkReparse = async () => {
    setBulkReparsing(true);
    try {
      const resp = await resumesApi.bulkReparse(Array.from(selectedIds));
      toast.success(`Re-parsing ${resp.total} resume(s). Refresh in a moment.`);
      setSelectedIds(new Set());
      setTimeout(() => loadResumes(page), 3000);
    } catch {
      toast.error("Failed to re-parse resumes");
    } finally {
      setBulkReparsing(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Header title="Resumes" subtitle="View and manage all uploaded resumes" />
      <div className="flex-1 p-8 space-y-6">
        {/* Top bar: search + actions */}
        <div className="flex items-center justify-between gap-4">
          <div className="relative w-80">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="Search by name or filename..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              disabled={reparsingAll || resumes.length === 0}
              isLoading={reparsingAll}
              onClick={async () => {
                setReparsingAll(true);
                try {
                  const resp = await resumesApi.reparseAll();
                  toast.success(`Re-parsing ${resp.total} resumes. Refresh in a moment.`);
                  setTimeout(() => loadResumes(page), 5000);
                } catch {
                  toast.error("Failed to re-parse resumes");
                } finally {
                  setReparsingAll(false);
                }
              }}
            >
              <RefreshCw className="w-4 h-4" />
              Re-parse All
            </Button>
            <Link href="/upload">
              <Button>
                <Upload className="w-4 h-4" />
                Upload Resumes
              </Button>
            </Link>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5 text-sm text-gray-500">
            <Filter className="w-4 h-4" />
            Filters:
          </div>
          <select
            value={parseStatusFilter}
            onChange={(e) => setParseStatusFilter(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All</option>
            <option value="completed">Parsed</option>
            <option value="processing">Processing</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>
          <select
            value={unitFilter}
            onChange={(e) => setUnitFilter(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Units</option>
            {units.map((u) => (
              <option key={u.id} value={u.id}>
                {u.unit_name}
              </option>
            ))}
          </select>
          <select
            value={jobFilter}
            onChange={(e) => setJobFilter(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Jobs</option>
            {jobs.map((j) => (
              <option key={j.job_id} value={j.job_id}>
                {j.job_title}
              </option>
            ))}
          </select>
          <select
            value={indexedFilter}
            onChange={(e) => setIndexedFilter(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Indexed</option>
            <option value="yes">Indexed</option>
            <option value="no">Not Indexed</option>
          </select>
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              <X className="w-3 h-3" />
              Clear
            </Button>
          )}
        </div>

        {/* Bulk Action Bar */}
        {selectedIds.size > 0 && (
          <div className="flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2.5">
            <span className="text-sm font-medium text-blue-700">
              {selectedIds.size} selected
            </span>
            <div className="h-4 w-px bg-blue-200" />
            <Button
              size="sm"
              variant="outline"
              onClick={handleBulkReparse}
              isLoading={bulkReparsing}
              disabled={bulkDeleting}
            >
              <RefreshCw className="w-3 h-3" />
              Re-parse Selected
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleBulkDelete}
              isLoading={bulkDeleting}
              disabled={bulkReparsing}
              className="text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200"
            >
              <Trash2 className="w-3 h-3" />
              Delete Selected
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setSelectedIds(new Set())}
            >
              Cancel
            </Button>
          </div>
        )}

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">
                All Resumes {!loading && <span className="text-gray-400 font-normal">({total})</span>}
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center py-12">
                <div className="spinner w-6 h-6" />
              </div>
            ) : resumes.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                {hasActiveFilters ? (
                  <>
                    <Filter className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                    <p className="font-medium">No resumes match the current filters</p>
                    <Button size="sm" variant="outline" className="mt-3" onClick={clearFilters}>
                      Clear Filters
                    </Button>
                  </>
                ) : (
                  <>
                    <p className="font-medium">No resumes uploaded yet</p>
                    <Link href="/upload" className="mt-3 inline-block">
                      <Button size="sm">Upload your first resumes</Button>
                    </Link>
                  </>
                )}
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 text-left">
                        <th className="pb-3 pr-2 w-10">
                          <button
                            onClick={toggleSelectAll}
                            className="text-gray-400 hover:text-gray-600"
                          >
                            {selectedIds.size === resumes.length && resumes.length > 0 ? (
                              <CheckSquare className="w-4 h-4 text-blue-600" />
                            ) : (
                              <Square className="w-4 h-4" />
                            )}
                          </button>
                        </th>
                        <th className="pb-3 pr-4 text-gray-500 font-medium">Candidate</th>
                        <th className="pb-3 pr-4 text-gray-500 font-medium">Filename</th>
                        <th className="pb-3 pr-4 text-gray-500 font-medium">Job Title</th>
                        <th className="pb-3 pr-4 text-gray-500 font-medium">Unit</th>
                        <th className="pb-3 pr-4 text-gray-500 font-medium">Parse Status</th>
                        <th className="pb-3 pr-4 text-gray-500 font-medium">Indexed</th>
                        <th className="pb-3 pr-4 text-gray-500 font-medium">Uploaded</th>
                        <th className="pb-3 text-gray-500 font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {resumes.map((r) => {
                        const busy = actioningId === r.id;
                        const selected = selectedIds.has(r.id);
                        return (
                          <tr
                            key={r.id}
                            className={`hover:bg-gray-50 transition-colors ${selected ? "bg-blue-50/50" : ""}`}
                          >
                            <td className="py-3 pr-2">
                              <button
                                onClick={() => toggleSelect(r.id)}
                                className="text-gray-400 hover:text-gray-600"
                              >
                                {selected ? (
                                  <CheckSquare className="w-4 h-4 text-blue-600" />
                                ) : (
                                  <Square className="w-4 h-4" />
                                )}
                              </button>
                            </td>
                            <td className="py-3 pr-4 font-medium text-gray-900">
                              {r.candidate_name || "—"}
                            </td>
                            <td className="py-3 pr-4 text-gray-600 max-w-[200px] truncate" title={r.filename}>
                              {r.filename}
                            </td>
                            <td className="py-3 pr-4 text-gray-600">
                              {r.job_title || "—"}
                            </td>
                            <td className="py-3 pr-4 text-gray-600">
                              {r.unit_name || "—"}
                            </td>
                            <td className="py-3 pr-4">
                              <ParseStatusBadge status={r.parse_status} />
                            </td>
                            <td className="py-3 pr-4">
                              <IndexedIndicator indexed={r.is_indexed ?? false} />
                            </td>
                            <td className="py-3 pr-4 text-gray-500 text-xs">
                              {new Date(r.created_at).toLocaleDateString()}
                            </td>
                            <td className="py-3">
                              <div className="flex items-center gap-1">
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  title="View file"
                                  onClick={() => handleViewFile(r.id)}
                                >
                                  <Eye className="w-3 h-3" />
                                </Button>
                                {r.parse_status === "failed" && (
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    title="Re-parse"
                                    disabled={busy}
                                    onClick={() => handleReparse(r.id)}
                                  >
                                    <RefreshCw className="w-3 h-3" />
                                  </Button>
                                )}
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  title="Delete"
                                  disabled={busy}
                                  onClick={() => handleDelete(r.id)}
                                  className="text-red-500 hover:text-red-700"
                                >
                                  <Trash2 className="w-3 h-3" />
                                </Button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between pt-4 border-t border-gray-100 mt-4">
                    <p className="text-sm text-gray-500">
                      Page {page} of {totalPages}
                    </p>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={page <= 1}
                        onClick={() => goToPage(page - 1)}
                      >
                        <ChevronLeft className="w-4 h-4" />
                        Previous
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={page >= totalPages}
                        onClick={() => goToPage(page + 1)}
                      >
                        Next
                        <ChevronRight className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
