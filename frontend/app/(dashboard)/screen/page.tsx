"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Header } from "@/components/layouts/Header";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { jobsApi } from "@/lib/api/jobs";
import type { JobDescription } from "@/lib/types";
import { Search, Zap, Info, Trash2, ExternalLink, Filter, X } from "lucide-react";
import toast from "react-hot-toast";

const EMPLOYEE_TYPE_OPTIONS = ["Full-time", "Contract", "Internship"];

export default function ScreenPage() {
  const router = useRouter();

  const [jobs, setJobs] = useState<JobDescription[]>([]);
  const [selectedJobId, setSelectedJobId] = useState("");
  const [maxCandidates, setMaxCandidates] = useState(20);
  const [screening, setScreening] = useState(false);
  const [progress, setProgress] = useState(0);
  const [existingResultCount, setExistingResultCount] = useState(0);
  const [isClearing, setIsClearing] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Filters
  const [jobSearch, setJobSearch] = useState("");
  const [employeeTypeFilter, setEmployeeTypeFilter] = useState("all");

  useEffect(() => {
    jobsApi.listJobs(1, 100).then((resp) => {
      const active = resp.items.filter((j) => {
        const st = j.status ?? "active";
        const isExpired =
          j.valid_till && new Date(j.valid_till) < new Date();
        return st === "active" && !isExpired;
      });
      setJobs(active);
    });
  }, []);

  // Filter jobs for dropdown
  const filteredJobs = jobs.filter((j) => {
    if (jobSearch.trim()) {
      const q = jobSearch.toLowerCase();
      if (
        !j.job_title.toLowerCase().includes(q) &&
        !(j.company && j.company.toLowerCase().includes(q))
      ) {
        return false;
      }
    }
    if (employeeTypeFilter !== "all" && j.employee_type !== employeeTypeFilter) {
      return false;
    }
    return true;
  });

  const hasActiveFilters = jobSearch.trim() !== "" || employeeTypeFilter !== "all";

  const clearFilters = () => {
    setJobSearch("");
    setEmployeeTypeFilter("all");
  };

  // Check for existing screening results when job is selected
  useEffect(() => {
    if (!selectedJobId) {
      setExistingResultCount(0);
      return;
    }
    jobsApi.getScreeningResults(selectedJobId).then((res) => {
      setExistingResultCount(res.length);
    }).catch(() => setExistingResultCount(0));
  }, [selectedJobId]);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const selectedJob = jobs.find((j) => j.job_id === selectedJobId);

  const handleScreen = async () => {
    if (!selectedJobId) {
      toast.error("Please select a job first");
      return;
    }
    setScreening(true);
    setProgress(0);

    try {
      await jobsApi.screenCandidates(selectedJobId, maxCandidates);

      pollRef.current = setInterval(async () => {
        try {
          const st = await jobsApi.getScreeningStatus(selectedJobId);
          if (st.total_resumes > 0) {
            setProgress(
              Math.round((st.processed_resumes / st.total_resumes) * 100)
            );
          }
          if (st.status === "completed") {
            if (pollRef.current) clearInterval(pollRef.current);
            setScreening(false);
            toast.success("Screening complete!");
            router.push(`/shortlist?job_id=${selectedJobId}`);
          } else if (st.status === "failed") {
            if (pollRef.current) clearInterval(pollRef.current);
            setScreening(false);
            const errorMsg = (st as Record<string, unknown>).error;
            toast.error(
              errorMsg
                ? `Screening failed: ${errorMsg}`
                : "Screening failed. Check server logs for details."
            );
          }
        } catch {
          // ignore poll errors
        }
      }, 3000);
    } catch (err) {
      setScreening(false);
      toast.error(
        err instanceof Error ? err.message : "Screening failed. Try again."
      );
    }
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Header
        title="Screen Candidates"
        subtitle="Select an active job posting to screen its uploaded resumes"
      />

      <div className="flex-1 p-8 max-w-3xl mx-auto w-full space-y-6">
        {/* Tips */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex gap-3">
          <Info className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800">
            <p className="font-semibold mb-1">How screening works</p>
            <ol className="list-decimal list-inside space-y-1 text-blue-700">
              <li>Select an active job from the dropdown below</li>
              <li>
                Knockout filters reject candidates that don&apos;t meet hard
                requirements
              </li>
              <li>
                Remaining candidates are scored on 4 weighted dimensions
                (0–100)
              </li>
              <li>
                Top candidates are ranked with explainable insights
              </li>
            </ol>
          </div>
        </div>

        {/* Job Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-500" />
              Select Job to Screen
            </CardTitle>
            <CardDescription>
              Only active job postings are shown. Need to create a new job?{" "}
              <Link
                href="/jobs/new"
                className="text-blue-600 hover:underline"
              >
                New Job Posting
              </Link>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Filters */}
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex items-center gap-1.5 text-sm text-gray-500">
                <Filter className="w-4 h-4" />
                Filters:
              </div>
              <div className="relative flex-1 min-w-[200px] max-w-[300px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="Search by title or company..."
                  value={jobSearch}
                  onChange={(e) => setJobSearch(e.target.value)}
                  className="pl-9"
                  disabled={screening}
                />
              </div>
              <select
                value={employeeTypeFilter}
                onChange={(e) => setEmployeeTypeFilter(e.target.value)}
                className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
                disabled={screening}
              >
                <option value="all">All Types</option>
                {EMPLOYEE_TYPE_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
              {hasActiveFilters && (
                <Button variant="ghost" size="sm" onClick={clearFilters}>
                  <X className="w-3 h-3" />
                  Clear
                </Button>
              )}
            </div>

            {/* Job dropdown */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-gray-700">
                Job Position <span className="text-red-500">*</span>
              </label>
              <select
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
                value={selectedJobId}
                onChange={(e) => setSelectedJobId(e.target.value)}
                disabled={screening}
              >
                <option value="">Select an active job…</option>
                {filteredJobs.map((j) => (
                  <option key={j.job_id} value={j.job_id}>
                    {j.job_title}
                    {j.company ? ` — ${j.company}` : ""}
                    {j.employee_type ? ` (${j.employee_type})` : ""}
                  </option>
                ))}
              </select>
              {filteredJobs.length === 0 && (
                <p className="text-xs text-amber-600">
                  {hasActiveFilters ? (
                    <>
                      No jobs match the current filters.{" "}
                      <button onClick={clearFilters} className="underline">
                        Clear filters
                      </button>
                    </>
                  ) : (
                    <>
                      No active jobs found.{" "}
                      <Link href="/jobs/new" className="underline">
                        Create one first.
                      </Link>
                    </>
                  )}
                </p>
              )}
            </div>

            {/* Selected job preview */}
            {selectedJob && (
              <div className="bg-gray-50 rounded-lg p-3 text-sm space-y-2">
                <p className="font-medium text-gray-900">
                  {selectedJob.job_title}
                </p>
                <p className="text-gray-500">
                  {[
                    selectedJob.company,
                    selectedJob.experience,
                    selectedJob.employee_type,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
                <p className="text-gray-500">
                  Required skills: {selectedJob.required_skills.length}
                  {selectedJob.experience
                    ? ` · Experience: ${selectedJob.experience}`
                    : selectedJob.required_min_exp_years > 0
                    ? ` · Min exp: ${selectedJob.required_min_exp_years}+ yrs`
                    : ""}
                </p>
                {selectedJob.required_skills.length === 0 && (
                  <div className="flex items-center gap-2 pt-1">
                    <span className="text-amber-600 text-xs">
                      Skills not extracted from JD — re-parse to extract them
                    </span>
                    <button
                      type="button"
                      className="text-xs text-blue-600 hover:text-blue-800 font-medium underline"
                      disabled={screening}
                      onClick={async () => {
                        try {
                          const updated = await jobsApi.reparseJob(selectedJobId);
                          setJobs((prev) =>
                            prev.map((j) =>
                              j.job_id === updated.job_id ? updated : j
                            )
                          );
                          toast.success(
                            `Re-parsed: ${updated.required_skills.length} skills found`
                          );
                        } catch {
                          toast.error("Re-parse failed");
                        }
                      }}
                    >
                      Re-parse JD
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Existing results banner */}
            {selectedJobId && existingResultCount > 0 && !screening && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-center justify-between">
                <p className="text-sm text-amber-800">
                  This job already has <strong>{existingResultCount}</strong> screening results.
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => router.push(`/shortlist?job_id=${selectedJobId}`)}
                  >
                    <ExternalLink className="w-3 h-3" />
                    View Results
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    isLoading={isClearing}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    onClick={async () => {
                      if (!confirm("Clear all existing screening results for this job?")) return;
                      setIsClearing(true);
                      try {
                        await jobsApi.clearScreeningResults(selectedJobId);
                        setExistingResultCount(0);
                        toast.success("Results cleared");
                      } catch {
                        toast.error("Failed to clear results");
                      } finally {
                        setIsClearing(false);
                      }
                    }}
                  >
                    <Trash2 className="w-3 h-3" />
                    Clear Results
                  </Button>
                </div>
              </div>
            )}

            {/* Max candidates */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-gray-700">
                Max Candidates
              </label>
              <select
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
                value={maxCandidates}
                onChange={(e) => setMaxCandidates(Number(e.target.value))}
                disabled={screening}
              >
                {[10, 20, 50, 100].map((n) => (
                  <option key={n} value={n}>
                    {n} candidates
                  </option>
                ))}
              </select>
            </div>

            {/* Progress */}
            {screening && (
              <div className="space-y-2 py-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">
                    Screening candidates…{" "}
                    <span className="text-gray-400">
                      (applying filters → scoring → ranking)
                    </span>
                  </span>
                  <span className="font-medium">{progress}%</span>
                </div>
                <Progress value={progress} color="blue" />
              </div>
            )}

            {/* Screen Button */}
            <div className="flex justify-end">
              <Button
                onClick={handleScreen}
                disabled={!selectedJobId || screening}
                isLoading={screening}
                size="lg"
              >
                <Search className="w-5 h-5" />
                {screening ? "Screening…" : "Screen Candidates"}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Scoring Info */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Scoring Methodology</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                {
                  label: "Skills Match",
                  weight: "45%",
                  color: "bg-blue-500",
                },
                {
                  label: "Experience",
                  weight: "30%",
                  color: "bg-purple-500",
                },
                {
                  label: "Career Growth",
                  weight: "15%",
                  color: "bg-orange-500",
                },
                {
                  label: "Achievements",
                  weight: "10%",
                  color: "bg-green-500",
                },
              ].map(({ label, weight, color }) => (
                <div key={label} className="text-center">
                  <div
                    className={`text-2xl font-bold text-white ${color} rounded-xl py-3 mb-2`}
                  >
                    {weight}
                  </div>
                  <p className="text-xs font-medium text-gray-600">{label}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
