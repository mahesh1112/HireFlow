"use client";
import { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  MapPin,
  Clock,
  CheckCircle,
  XCircle,
  Star,
  AlertTriangle,
  Eye,
  FileText,
} from "lucide-react";
import { FitStatusBadge } from "@/components/ui/badge";
import { ScoreBar } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { cn, getScoreColor } from "@/lib/utils";
import type { ScreeningResult } from "@/lib/types";
import { resumesApi } from "@/lib/api/resumes";
import { jobsApi } from "@/lib/api/jobs";
import toast from "react-hot-toast";

interface CandidateCardProps {
  result: ScreeningResult;
  isSelected: boolean;
  onToggleSelect: (resultId: string) => void;
  onShortlist?: (resultId: string) => void;
  rank: number;
}

export function CandidateCard({
  result,
  isSelected,
  onToggleSelect,
  onShortlist,
  rank,
}: CandidateCardProps) {
  const [expanded, setExpanded] = useState(false);

  const handleShortlist = (e: React.MouseEvent) => {
    e.stopPropagation();
    onShortlist?.(result.result_id);
  };

  return (
    <div
      className={cn(
        "candidate-card",
        isSelected && "ring-2 ring-blue-500 border-blue-500"
      )}
    >
      {/* Main Row */}
      <div className="flex items-center gap-4">
        {/* Checkbox */}
        <input
          type="checkbox"
          checked={isSelected}
          onChange={() => onToggleSelect(result.result_id)}
          className="w-4 h-4 text-blue-600 rounded border-gray-300 cursor-pointer"
          onClick={(e) => e.stopPropagation()}
        />

        {/* Rank */}
        <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-full bg-gray-100 text-sm font-bold text-gray-600">
          {rank}
        </div>

        {/* Candidate Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-gray-900 text-base">
              {result.candidate_name}
            </h3>
            <FitStatusBadge status={result.status} />
            {result.is_shortlisted && (
              <span className="inline-flex items-center gap-1 text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">
                <Star className="w-3 h-3" /> Shortlisted
              </span>
            )}
          </div>
          <div className="flex items-center gap-4 mt-1 text-sm text-gray-500 flex-wrap">
            <span>{result.candidate_email}</span>
            {result.candidate_location && (
              <span className="flex items-center gap-1">
                <MapPin className="w-3 h-3" />
                {result.candidate_location}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {result.total_exp_years} yrs experience
            </span>
          </div>
        </div>

        {/* Score */}
        <div className="flex-shrink-0 text-center">
          <div
            className={cn(
              "text-3xl font-bold",
              getScoreColor(result.fit_score)
            )}
          >
            {result.fit_score}
          </div>
          <div className="text-xs text-gray-400">Fit Score</div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <Button
            size="sm"
            variant="ghost"
            onClick={async () => {
              try {
                const blob = await resumesApi.getResumeFile(result.resume_id);
                const url = URL.createObjectURL(blob);
                window.open(url, "_blank");
              } catch {
                toast.error("Failed to load resume file");
              }
            }}
            title="Preview resume"
          >
            <Eye className="w-3 h-3" />
            Preview
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={async (e) => {
              e.stopPropagation();
              try {
                toast.loading("Generating report...", { id: "pdf-gen" });
                const blob = await jobsApi.downloadCandidateReport(result.result_id);
                const url = URL.createObjectURL(blob);
                window.open(url, "_blank");
                toast.success("Report ready!", { id: "pdf-gen" });
              } catch {
                toast.error("Failed to generate report", { id: "pdf-gen" });
              }
            }}
            title="Preview PDF Report"
          >
            <FileText className="w-3 h-3" />
            Report
          </Button>
          {!result.is_shortlisted && (
            <Button size="sm" variant="outline" onClick={handleShortlist}>
              <Star className="w-3 h-3" />
              Shortlist
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="mt-5 pt-5 border-t border-gray-100 space-y-5">
          {/* Score Breakdown */}
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-3">
              Score Breakdown
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <ScoreBar
                label="Skills Match"
                score={result.category_scores.skills_match}
                weight={45}
              />
              <ScoreBar
                label="Experience Relevance"
                score={result.category_scores.experience_relevance}
                weight={30}
              />
              <ScoreBar
                label="Career Progression"
                score={result.category_scores.career_progression}
                weight={15}
              />
              <ScoreBar
                label="Achievements"
                score={result.category_scores.measurable_achievements}
                weight={10}
              />
            </div>
          </div>

          {/* Match Explanation */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">
              AI Analysis
            </h4>
            <p className="text-sm text-gray-600">{result.match_explanation}</p>
          </div>

          {/* Strengths & Weaknesses */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
                <CheckCircle className="w-4 h-4 text-green-500" /> Strengths
              </h4>
              <ul className="space-y-1.5">
                {result.strengths.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                    <span className="text-green-500 mt-0.5">✓</span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
                <XCircle className="w-4 h-4 text-red-400" /> Gaps
              </h4>
              <ul className="space-y-1.5">
                {result.weaknesses.map((w, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                    <span className="text-red-400 mt-0.5">✗</span>
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Knockout Failures (if any) */}
          {!result.passed_knockouts && result.knockout_failures.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-red-700 mb-2 flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4" /> Knockout Filter Failures
              </h4>
              <ul className="space-y-1">
                {result.knockout_failures.map((f, i) => (
                  <li key={i} className="text-sm text-red-600">
                    <span className="font-medium">{f.rule}:</span> {f.reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Skills */}
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">
              Skills Analysis
            </h4>
            <div className="flex flex-wrap gap-2">
              {result.skills_matched.map((s) => (
                <span
                  key={s.required_skill}
                  className="inline-flex items-center gap-1 text-xs bg-green-100 text-green-700 px-2.5 py-1 rounded-full"
                >
                  <CheckCircle className="w-3 h-3" />
                  {s.candidate_skill}
                  <span className="text-green-500 font-medium">
                    {Math.round(s.match_confidence * 100)}%
                  </span>
                </span>
              ))}
              {result.skills_missing.map((s) => (
                <span
                  key={s.required_skill}
                  className="inline-flex items-center gap-1 text-xs bg-red-100 text-red-600 px-2.5 py-1 rounded-full"
                >
                  <XCircle className="w-3 h-3" />
                  {s.required_skill}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
