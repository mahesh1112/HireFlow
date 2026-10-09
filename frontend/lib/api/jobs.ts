import apiClient from "./client";
import type {
  JobDescription,
  ScreeningResult,
  ScreeningJob,
  PaginatedResponse,
} from "@/lib/types";

export interface CreateJobPayload {
  job_description_text: string;
  job_title?: string;
  company?: string;
  business_unit_id?: string;
  experience?: string;
  employee_type?: string;
  location_office?: string;
  remote_job?: boolean;
  hiring_leads?: string[];
  recruiter_id?: string;
  valid_till?: string;
}

export interface UpdateJobPayload {
  job_title?: string;
  company?: string;
  business_unit_id?: string;
  experience?: string;
  employee_type?: string;
  location_office?: string;
  remote_job?: boolean;
  hiring_leads?: string[];
  recruiter_id?: string;
  valid_till?: string;
  job_description_text?: string;
}

export interface ScreenJobPayload {
  job_id: string;
  max_candidates?: number;
}

export const jobsApi = {
  createJob: async (payload: CreateJobPayload): Promise<JobDescription> => {
    const { data } = await apiClient.post<JobDescription>(
      "/jobs/create",
      payload
    );
    return data;
  },

  getJob: async (jobId: string): Promise<JobDescription> => {
    const { data } = await apiClient.get<JobDescription>(`/jobs/${jobId}`);
    return data;
  },

  listJobs: async (
    page = 1,
    pageSize = 20
  ): Promise<PaginatedResponse<JobDescription>> => {
    const { data } = await apiClient.get<PaginatedResponse<JobDescription>>(
      "/jobs",
      { params: { page, page_size: pageSize } }
    );
    return data;
  },

  screenCandidates: async (
    jobId: string,
    maxCandidates = 20
  ): Promise<ScreeningJob> => {
    const { data } = await apiClient.post<ScreeningJob>(
      `/jobs/${jobId}/screen`,
      { max_candidates: maxCandidates }
    );
    return data;
  },

  getScreeningResults: async (
    jobId: string
  ): Promise<ScreeningResult[]> => {
    const { data } = await apiClient.get<ScreeningResult[]>(
      `/jobs/${jobId}/screening-results`
    );
    return data;
  },

  deleteJob: async (jobId: string): Promise<void> => {
    await apiClient.delete(`/jobs/${jobId}`);
  },

  shortlistCandidate: async (resultId: string): Promise<void> => {
    await apiClient.post(`/screening-results/${resultId}/actions`, {
      action: "shortlist",
    });
  },

  exportResults: async (
    jobId: string,
    format: "csv" | "pdf" = "csv"
  ): Promise<Blob> => {
    const { data } = await apiClient.post(
      "/screening-results/export",
      { job_id: jobId, format },
      { responseType: "blob" }
    );
    return data;
  },

  getScreeningStatus: async (jobId: string): Promise<ScreeningJob> => {
    const { data } = await apiClient.get<ScreeningJob>(
      `/jobs/${jobId}/screening-status`
    );
    return data;
  },

  updateJob: async (
    jobId: string,
    payload: UpdateJobPayload
  ): Promise<JobDescription> => {
    const { data } = await apiClient.patch<JobDescription>(
      `/jobs/${jobId}`,
      payload
    );
    return data;
  },

  updateJobStatus: async (
    jobId: string,
    payload: { action: "activate" | "pause" | "fill"; valid_till?: string }
  ): Promise<JobDescription> => {
    const { data } = await apiClient.patch<JobDescription>(
      `/jobs/${jobId}/status`,
      payload
    );
    return data;
  },

  reparseJob: async (jobId: string): Promise<JobDescription> => {
    const { data } = await apiClient.post<JobDescription>(
      `/jobs/${jobId}/reparse`
    );
    return data;
  },

  downloadCandidateReport: async (resultId: string): Promise<Blob> => {
    const { data } = await apiClient.get(
      `/screening-results/${resultId}/pdf`,
      { responseType: "blob", timeout: 60000 }
    );
    return data;
  },

  clearScreeningResults: async (
    jobId: string
  ): Promise<{ job_id: string; deleted: number }> => {
    const { data } = await apiClient.post<{
      job_id: string;
      deleted: number;
    }>(`/jobs/${jobId}/clear-screening`);
    return data;
  },
};
