"use client";
import { useCallback, useEffect, useRef } from "react";
import { jobsApi } from "@/lib/api/jobs";
import { useScreeningStore } from "@/store";
import { downloadCSV } from "@/lib/utils";
import type { ScreeningResult } from "@/lib/types";

const POLL_INTERVAL_MS = 3000;

export function useScreening() {
  const {
    currentJob,
    results,
    selectedResults,
    isScreening,
    screeningProgress,
    setCurrentJob,
    setResults,
    toggleSelected,
    selectAll,
    clearSelection,
    setIsScreening,
    setScreeningProgress,
    reset,
  } = useScreeningStore();

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const screeningJobId = useRef<string | null>(null);

  const submitJD = useCallback(
    async (jdText: string, jobTitle?: string) => {
      setIsScreening(true);
      setScreeningProgress(0);
      setResults([]);

      try {
        // 1. Parse the JD and create the job
        const job = await jobsApi.createJob({
          job_description_text: jdText,
          job_title: jobTitle,
        });
        setCurrentJob(job);

        // 2. Kick off screening
        const screeningJob = await jobsApi.screenCandidates(job.job_id);
        screeningJobId.current = screeningJob.job_id;

        // 3. Poll for results
        pollRef.current = setInterval(async () => {
          try {
            const status = await jobsApi.getScreeningStatus(
              screeningJob.job_id
            );
            if (status.total_resumes > 0) {
              setScreeningProgress(
                Math.round(
                  (status.processed_resumes / status.total_resumes) * 100
                )
              );
            }
            if (status.status === "completed") {
              const finalResults = await jobsApi.getScreeningResults(
                screeningJob.job_id
              );
              setResults(finalResults);
              setIsScreening(false);
              if (pollRef.current) clearInterval(pollRef.current);
            } else if (status.status === "failed") {
              setIsScreening(false);
              if (pollRef.current) clearInterval(pollRef.current);
            }
          } catch {
            // ignore poll errors
          }
        }, POLL_INTERVAL_MS);
      } catch (err) {
        setIsScreening(false);
        throw err;
      }
    },
    [setCurrentJob, setIsScreening, setResults, setScreeningProgress]
  );

  const shortlistSelected = useCallback(async () => {
    const promises = Array.from(selectedResults).map((id) =>
      jobsApi.shortlistCandidate(id)
    );
    await Promise.all(promises);
  }, [selectedResults]);

  const exportToCSV = useCallback(
    (candidates?: ScreeningResult[]) => {
      const data = (candidates ?? results)
        .filter((r) => selectedResults.size === 0 || selectedResults.has(r.result_id))
        .map((r) => ({
          Rank: r.rank,
          Name: r.candidate_name,
          Email: r.candidate_email,
          Location: r.candidate_location ?? "",
          Experience: `${r.total_exp_years} yrs`,
          "Fit Score": r.fit_score,
          Status: r.status,
          "Skills Match": r.category_scores.skills_match,
          "Experience Relevance": r.category_scores.experience_relevance,
          "Career Progression": r.category_scores.career_progression,
          Achievements: r.category_scores.measurable_achievements,
          Strengths: r.strengths.join("; "),
          Weaknesses: r.weaknesses.join("; "),
        }));
      downloadCSV(data, `shortlist-${currentJob?.job_title ?? "results"}.csv`);
    },
    [results, selectedResults, currentJob]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  return {
    currentJob,
    results,
    selectedResults,
    isScreening,
    screeningProgress,
    submitJD,
    toggleSelected,
    selectAll,
    clearSelection,
    shortlistSelected,
    exportToCSV,
    setResults,
    setCurrentJob,
    reset,
  };
}
