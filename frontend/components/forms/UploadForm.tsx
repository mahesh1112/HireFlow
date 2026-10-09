"use client";
import { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, X, FileText, CheckCircle, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useResumeUpload } from "@/lib/hooks/useResumeUpload";
import { jobsApi } from "@/lib/api/jobs";
import { formatFileSize } from "@/lib/utils";
import type { JobDescription, BulkUploadResult } from "@/lib/types";
import toast from "react-hot-toast";

export function UploadForm() {
  const {
    files,
    batch,
    uploadProgress,
    isUploading,
    addFiles,
    removeFile,
    startUpload,
    reset,
  } = useResumeUpload();

  const [jobs, setJobs] = useState<JobDescription[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [derivedUnitId, setDerivedUnitId] = useState<string>("");

  useEffect(() => {
    jobsApi.listJobs(1, 100).then((resp) => {
      // Only show active jobs for upload
      const active = resp.items.filter((j) => {
        const st = j.status ?? "active";
        const isExpired = j.valid_till && new Date(j.valid_till) < new Date();
        return (st === "active" && !isExpired) || st === "paused";
      });
      setJobs(active);
    });
  }, []);

  const handleJobChange = (jobId: string) => {
    setSelectedJobId(jobId);
    const found = jobs.find((j) => j.job_id === jobId);
    setDerivedUnitId(found?.business_unit_id ?? "");
  };

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      addFiles(acceptedFiles);
    },
    [addFiles]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    },
    maxSize: 10 * 1024 * 1024,
    multiple: true,
    disabled: isUploading,
  });

  const handleUpload = async () => {
    if (!files.length) return;
    if (!selectedJobId) {
      toast.error("Please select a job position");
      return;
    }
    try {
      await startUpload(derivedUnitId, selectedJobId);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    }
  };

  // Show duplicate warning when batch first arrives with skipped files
  const [skippedShown, setSkippedShown] = useState(false);
  useEffect(() => {
    const b = batch as BulkUploadResult | null;
    if (b?.skipped_files?.length && !skippedShown) {
      setSkippedShown(true);
      toast(
        `${b.skipped_files.length} duplicate(s) skipped: ${b.skipped_files.join(", ")}`,
        { icon: "⚠️", duration: 6000 }
      );
    }
  }, [batch, skippedShown]);

  const batchComplete = batch?.status === "completed";
  const batchFailed = batch?.status === "failed";

  return (
    <div className="space-y-6">
      {/* Job Position Selector */}
      <div className="space-y-1.5">
        <label className="block text-sm font-medium text-gray-700">
          Job Position <span className="text-red-500">*</span>
        </label>
        <select
          className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60 disabled:cursor-not-allowed"
          value={selectedJobId}
          onChange={(e) => handleJobChange(e.target.value)}
          disabled={isUploading}
        >
          <option value="">Select a job position…</option>
          {jobs.map((j) => {
            const unitSlug = j.unit_name
              ? j.unit_name.split(" ").map((w) => w[0]).join("").toUpperCase()
              : "";
            return (
              <option key={j.job_id} value={j.job_id}>
                {j.job_title}
                {unitSlug ? ` — ${unitSlug}` : ""}
                {` · ${j.job_id}`}
              </option>
            );
          })}
        </select>
        {jobs.length === 0 && (
          <p className="text-xs text-gray-500">
            No active job positions found. Create a job posting first.
          </p>
        )}
        {selectedJobId && (() => {
          const sel = jobs.find((j) => j.job_id === selectedJobId);
          if (!sel) return null;
          const unitSlug = sel.unit_name
            ? sel.unit_name.split(" ").map((w) => w[0]).join("").toUpperCase()
            : null;
          return (
            <div className="mt-2 bg-gray-50 rounded-lg p-3 text-sm space-y-1">
              <div className="flex items-center gap-4">
                <span className="text-gray-500">Job ID</span>
                <span className="font-mono text-xs text-gray-700 font-semibold">{sel.job_id}</span>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-gray-500">Position</span>
                <span className="font-medium text-gray-900">{sel.job_title}</span>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-gray-500">Unit</span>
                <span className="text-gray-700">{unitSlug ?? "—"}</span>
              </div>
            </div>
          );
        })()}
      </div>

      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={`upload-zone ${isDragActive ? "dragover" : ""} ${isUploading ? "opacity-60 cursor-not-allowed" : ""}`}
      >
        <input {...getInputProps()} />
        <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        {isDragActive ? (
          <p className="text-blue-600 font-medium">Drop the files here…</p>
        ) : (
          <>
            <p className="text-gray-700 font-medium text-lg">
              Drag & drop resumes here
            </p>
            <p className="text-gray-500 text-sm mt-1">
              or <span className="text-blue-600 font-medium cursor-pointer">browse files</span>
            </p>
            <p className="text-gray-400 text-xs mt-3">
              Supports PDF and DOCX · Max 10MB per file · Up to 200 files
            </p>
          </>
        )}
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="border border-gray-200 rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
            <span className="text-sm font-medium text-gray-700">
              {files.length} file{files.length > 1 ? "s" : ""} selected
            </span>
            {!isUploading && (
              <button
                onClick={reset}
                className="text-xs text-red-500 hover:text-red-700 font-medium"
              >
                Clear all
              </button>
            )}
          </div>
          <div className="divide-y divide-gray-100 max-h-64 overflow-y-auto">
            {files.map((file, i) => (
              <div
                key={`${file.name}-${i}`}
                className="flex items-center gap-3 px-4 py-3"
              >
                <FileText className="w-4 h-4 text-blue-500 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900 truncate">{file.name}</p>
                  <p className="text-xs text-gray-400">
                    {formatFileSize(file.size)}
                  </p>
                </div>
                {!isUploading && (
                  <button
                    onClick={() => removeFile(i)}
                    className="text-gray-400 hover:text-red-500"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload Progress */}
      {isUploading && (
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Uploading files…</span>
            <span className="font-medium text-gray-900">{uploadProgress}%</span>
          </div>
          <Progress value={uploadProgress} color="blue" />
        </div>
      )}

      {/* Batch Processing Status */}
      {batch && (
        <div
          className={`rounded-xl p-4 flex items-start gap-3 ${
            batchComplete
              ? "bg-green-50 border border-green-200"
              : batchFailed
              ? "bg-red-50 border border-red-200"
              : "bg-blue-50 border border-blue-200"
          }`}
        >
          {batchComplete ? (
            <CheckCircle className="w-5 h-5 text-green-500 mt-0.5" />
          ) : batchFailed ? (
            <AlertCircle className="w-5 h-5 text-red-500 mt-0.5" />
          ) : (
            <div className="spinner mt-0.5" />
          )}
          <div>
            <p className="text-sm font-medium text-gray-900">
              {batchComplete
                ? "Upload complete!"
                : batchFailed
                ? "Upload failed"
                : "Processing resumes…"}
            </p>
            <p className="text-xs text-gray-600 mt-0.5">
              {batch.processed_files} / {batch.total_files} files processed
              {batch.failed_files > 0 && ` · ${batch.failed_files} failed`}
              {(batch as BulkUploadResult).skipped_count
                ? ` · ${(batch as BulkUploadResult).skipped_count} duplicate(s) skipped`
                : ""}
            </p>
            {!batchComplete && !batchFailed && (
              <Progress
                value={Math.round(
                  (batch.processed_files / batch.total_files) * 100
                )}
                color="blue"
                className="mt-2"
              />
            )}
          </div>
        </div>
      )}

      {/* Upload Button */}
      <div className="flex justify-end gap-3">
        {batchComplete && (
          <Button variant="outline" onClick={() => { reset(); setSkippedShown(false); }}>
            Upload More
          </Button>
        )}
        {!batchComplete && (
          <Button
            onClick={handleUpload}
            disabled={!files.length || isUploading || !selectedJobId}
            isLoading={isUploading}
            className="min-w-32"
          >
            <Upload className="w-4 h-4" />
            {isUploading ? "Uploading…" : `Upload ${files.length || ""} Files`}
          </Button>
        )}
      </div>
    </div>
  );
}
