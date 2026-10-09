import apiClient from "./client";
import type { DashboardStats } from "@/lib/types";

export const adminApi = {
  getStats: async (): Promise<DashboardStats> => {
    const { data } = await apiClient.get<DashboardStats>("/admin/stats");
    return data;
  },

  getLogs: async (page = 1, pageSize = 50) => {
    const { data } = await apiClient.get("/admin/logs", {
      params: { page, page_size: pageSize },
    });
    return data;
  },

  reprocessResumes: async () => {
    const { data } = await apiClient.post("/admin/reprocess");
    return data;
  },
};
