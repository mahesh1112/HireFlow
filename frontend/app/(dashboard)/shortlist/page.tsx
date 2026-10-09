"use client";
import { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { Header } from "@/components/layouts/Header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CandidateCard } from "@/components/cards/CandidateCard";
import { useScreening } from "@/lib/hooks/useScreening";
import { jobsApi } from "@/lib/api/jobs";
import type { ScreeningResult } from "@/lib/types";
import {
  Download,
  Users,
  CheckSquare,
  Square,
  Filter,
  Star,
  Trash2,
} from "lucide-react";
import toast from "react-hot-toast";
import Link from "next/link";

type FilterStatus = "ALL" | "EXCELLENT" | "GOOD" | "ADEQUATE" | "POOR";

export default function ShortlistPage() {
  const searchParams = useSearchParams();
  const jobIdParam = searchParams.get("job_id");

  const {
    results,
    selectedResults,
    toggleSelected,
    selectAll,
    clearSelection,
    shortlistSelected,
    exportToCSV,
    currentJob,
    setResults,
    setCurrentJob,
  } = useScreening();

  const [filter, setFilter] = useState<FilterStatus>("ALL");
  const [loading, setLoading] = useState(false);
  const [isShortlisting, setIsShortlisting] = useState(false);
  const [isClearing, setIsClearing] = useState(false);

  // Load results from URL param (if navigating directly)
  useEffect(() => {
    if (jobIdParam && !results.length) {
      setLoading(true);
      Promise.all([
        jobsApi.getScreeningResults(jobIdParam),
        jobsApi.getJob(jobIdParam),
      ])
        .then(([res, job]) => {
          setResults(res);
          setCurrentJob(job);
        })
        .catch(() => toast.error("Failed to load results"))
        .finally(() => setLoading(false));
    }
  }, [jobIdParam, results.length, setResults, setCurrentJob]);

  const filteredResults = results.filter(
    (r) => filter === "ALL" || r.status === filter
  );

  const passedResults = results.filter((r) => r.passed_knockouts);
  const shortlistRate = results.length
    ? ((passedResults.length / results.length) * 100).toFixed(0)
    : 0;

  const handleBulkShortlist = async () => {
    if (!selectedResults.size) {
      toast.error("Select candidates first");
      return;
    }
    setIsShortlisting(true);
    try {
      await shortlistSelected();
      toast.success(
        `${selectedResults.size} candidate(s) shortlisted!`
      );
      clearSelection();
    } catch {
      toast.error("Failed to shortlist candidates");
    } finally {
      setIsShortlisting(false);
    }
  };

  const handleShortlist = useCallback(
    async (resultId: string) => {
      try {
        await jobsApi.shortlistCandidate(resultId);
        toast.success("Candidate shortlisted!");
      } catch {
        toast.error("Failed to shortlist");
      }
    },
    []
  );

  const handleExport = () => {
    exportToCSV();
    toast.success("CSV export started!");
  };

  if (loading) {
    return (
      <div className="flex flex-col min-h-screen">
        <Header title="Shortlist" />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="spinner mx-auto mb-4" />
            <p className="text-gray-500">Loading results…</p>
          </div>
        </div>
      </div>
    );
  }

  if (!results.length) {
    return (
      <div className="flex flex-col min-h-screen">
        <Header title="Shortlist" subtitle="No screening results yet" />
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center max-w-sm">
            <Users className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-700 mb-2">
              No results yet
            </h3>
            <p className="text-gray-500 mb-6">
              Screen candidates against a job description to see ranked results
              here.
            </p>
            <Link href="/screen">
              <Button>Start Screening</Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Header
        title="Candidate Shortlist"
        subtitle={
          currentJob
            ? `${currentJob.job_title} · ${results.length} candidates evaluated`
            : `${results.length} candidates evaluated`
        }
      />

      <div className="flex-1 p-8 space-y-6">
        {/* Summary Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            {
              label: "Total Evaluated",
              value: results.length,
              color: "text-gray-700",
            },
            {
              label: "Passed Filters",
              value: passedResults.length,
              color: "text-green-600",
            },
            {
              label: "Match Rate",
              value: `${shortlistRate}%`,
              color: "text-blue-600",
            },
            {
              label: "Selected",
              value: selectedResults.size,
              color: "text-purple-600",
            },
          ].map(({ label, value, color }) => (
            <Card key={label}>
              <CardContent className="p-4 text-center">
                <div className={`text-2xl font-bold ${color}`}>{value}</div>
                <div className="text-xs text-gray-500 mt-0.5">{label}</div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Filter Tabs */}
          <div className="flex items-center gap-1 bg-gray-100 p-1 rounded-lg flex-wrap">
            {(["ALL", "EXCELLENT", "GOOD", "ADEQUATE", "POOR"] as FilterStatus[]).map(
              (f) => {
                const counts = {
                  ALL: results.length,
                  EXCELLENT: results.filter((r) => r.status === "EXCELLENT").length,
                  GOOD: results.filter((r) => r.status === "GOOD").length,
                  ADEQUATE: results.filter((r) => r.status === "ADEQUATE").length,
                  POOR: results.filter((r) => r.status === "POOR").length,
                };
                return (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                      filter === f
                        ? "bg-white shadow-sm text-gray-900"
                        : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    {f === "ALL" ? "All" : f.charAt(0) + f.slice(1).toLowerCase()}
                    <span className="ml-1.5 text-xs text-gray-400">
                      ({counts[f]})
                    </span>
                  </button>
                );
              }
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={
                selectedResults.size === filteredResults.length
                  ? clearSelection
                  : selectAll
              }
            >
              {selectedResults.size === filteredResults.length ? (
                <CheckSquare className="w-4 h-4" />
              ) : (
                <Square className="w-4 h-4" />
              )}
              {selectedResults.size === filteredResults.length
                ? "Deselect All"
                : "Select All"}
            </Button>

            {selectedResults.size > 0 && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleBulkShortlist}
                isLoading={isShortlisting}
              >
                <Star className="w-4 h-4" />
                Shortlist ({selectedResults.size})
              </Button>
            )}

            <Button size="sm" variant="outline" onClick={handleExport}>
              <Download className="w-4 h-4" />
              Export CSV
            </Button>

            <Button
              size="sm"
              variant="outline"
              isLoading={isClearing}
              className="text-red-600 hover:text-red-700 hover:bg-red-50"
              onClick={async () => {
                if (!confirm("Clear all screening results for this job? This cannot be undone.")) return;
                const jobId = currentJob?.job_id || jobIdParam;
                if (!jobId) return;
                setIsClearing(true);
                try {
                  const resp = await jobsApi.clearScreeningResults(jobId);
                  toast.success(`Cleared ${resp.deleted} screening results`);
                  setResults([]);
                  clearSelection();
                } catch {
                  toast.error("Failed to clear results");
                } finally {
                  setIsClearing(false);
                }
              }}
            >
              <Trash2 className="w-4 h-4" />
              Clear Results
            </Button>
          </div>
        </div>

        {/* Results */}
        {filteredResults.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Filter className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">
                No candidates match the selected filter
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {filteredResults.map((result, i) => (
              <CandidateCard
                key={result.result_id}
                result={result}
                rank={result.rank || i + 1}
                isSelected={selectedResults.has(result.result_id)}
                onToggleSelect={toggleSelected}
                onShortlist={handleShortlist}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
