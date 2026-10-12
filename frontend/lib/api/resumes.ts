import apiClient from "./client";
import type { Resume, UploadBatch, BulkUploadResult, PaginatedResponse } from "@/lib/types";

export const resumesApi = {
  bulkUpload: async (
    files: File[],
    unitId: string,
    jobPositionId: string,
    onProgress?: (progress: number) => void
  ): Promise<BulkUploadResult> => {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    if (unitId) formData.append("unit_id", unitId);
    formData.append("job_position_id", jobPositionId);

    const { data } = await apiClient.post<BulkUploadResult>(
      "/resumes/bulk-upload",
      formData,
      {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (event) => {
          if (event.total && onProgress) {
            onProgress(Math.round((event.loaded * 100) / event.total));
          }
        },
      }
    );
    return data;
  },

  getResumeFile: async (resumeId: string): Promise<Blob> => {
    const { data } = await apiClient.get(`/resumes/${resumeId}/file`, {
      responseType: "blob",
    });
    return data;
  },

  getBatchStatus: async (batchId: string): Promise<UploadBatch> => {
    const { data } = await apiClient.get<UploadBatch>(
      `/resumes/batch/${batchId}`
    );
    return data;
  },

  listResumes: async (
    page = 1,
    pageSize = 20,
    filters?: {
      parse_status?: string;
      unit_id?: string;
      job_position_id?: string;
      is_indexed?: boolean;
      search?: string;
    }
  ): Promise<PaginatedResponse<Resume>> => {
    const params: Record<string, string | number | boolean> = {
      page,
      page_size: pageSize,
    };
    if (filters?.parse_status) params.parse_status = filters.parse_status;
    if (filters?.unit_id) params.unit_id = filters.unit_id;
    if (filters?.job_position_id) params.job_position_id = filters.job_position_id;
    if (filters?.is_indexed !== undefined) params.is_indexed = filters.is_indexed;
    if (filters?.search) params.search = filters.search;

    const { data } = await apiClient.get<PaginatedResponse<Resume>>(
      "/resumes",
      { params }
    );
    return data;
  },

  getResume: async (resumeId: string): Promise<Resume> => {
    const { data } = await apiClient.get<Resume>(`/resumes/${resumeId}`);
    return data;
  },

  deleteResume: async (resumeId: string): Promise<void> => {
    await apiClient.delete(`/resumes/${resumeId}`);
  },

  reparse: async (resumeId: string): Promise<Resume> => {
    const { data } = await apiClient.post<Resume>(
      `/resumes/${resumeId}/parse`
    );
    return data;
  },

  reparseAll: async (): Promise<{ message: string; total: number }> => {
    const { data } = await apiClient.post<{ message: string; total: number }>(
      "/resumes/reparse-all"
    );
    return data;
  },

  bulkDelete: async (resumeIds: string[]): Promise<{ deleted: number }> => {
    const { data } = await apiClient.post<{ deleted: number }>(
      "/resumes/bulk-delete",
      { resume_ids: resumeIds }
    );
    return data;
  },

  bulkReparse: async (
    resumeIds: string[]
  ): Promise<{ message: string; total: number }> => {
    const { data } = await apiClient.post<{ message: string; total: number }>(
      "/resumes/bulk-reparse",
      { resume_ids: resumeIds }
    );
    return data;
  },
};
