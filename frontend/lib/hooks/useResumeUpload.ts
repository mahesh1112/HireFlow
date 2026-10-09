"use client";
import { useCallback, useEffect, useRef } from "react";
import { resumesApi } from "@/lib/api/resumes";
import { useUploadStore } from "@/store";

const POLL_INTERVAL_MS = 2000;
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
const ALLOWED_TYPES = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"];

export function useResumeUpload() {
  const {
    batch,
    files,
    uploadProgress,
    isUploading,
    setBatch,
    setFiles,
    setUploadProgress,
    setIsUploading,
    reset,
  } = useUploadStore();

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const validateFiles = (fileList: File[]): { valid: File[]; errors: string[] } => {
    const valid: File[] = [];
    const errors: string[] = [];

    for (const file of fileList) {
      if (file.size > MAX_FILE_SIZE) {
        errors.push(`${file.name}: File too large (max 10MB)`);
      } else if (!ALLOWED_TYPES.includes(file.type)) {
        errors.push(`${file.name}: Invalid file type (only PDF/DOCX allowed)`);
      } else {
        valid.push(file);
      }
    }
    return { valid, errors };
  };

  const addFiles = useCallback((newFiles: File[]) => {
    const { valid } = validateFiles(newFiles);
    setFiles([...files, ...valid]);
  }, [files, setFiles]);

  const removeFile = useCallback((index: number) => {
    const updated = files.filter((_, i) => i !== index);
    setFiles(updated);
  }, [files, setFiles]);

  const startUpload = useCallback(async (unitId: string, jobPositionId: string) => {
    if (!files.length || isUploading) return;
    setIsUploading(true);
    setUploadProgress(0);

    try {
      const uploadedBatch = await resumesApi.bulkUpload(files, unitId, jobPositionId, setUploadProgress);
      setBatch(uploadedBatch);
    } catch (err) {
      setIsUploading(false);
      throw err;
    }
  }, [files, isUploading, setBatch, setIsUploading, setUploadProgress]);

  // Poll batch status until done
  useEffect(() => {
    if (!batch || batch.status === "completed" || batch.status === "failed") {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      if (batch?.status === "completed" || batch?.status === "failed") {
        setIsUploading(false);
      }
      return;
    }

    pollRef.current = setInterval(async () => {
      try {
        const updated = await resumesApi.getBatchStatus(batch.batch_id);
        setBatch(updated);
      } catch {
        // ignore poll errors
      }
    }, POLL_INTERVAL_MS);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [batch, setBatch, setIsUploading]);

  return {
    files,
    batch,
    uploadProgress,
    isUploading,
    validateFiles,
    addFiles,
    removeFile,
    startUpload,
    reset,
  };
}
