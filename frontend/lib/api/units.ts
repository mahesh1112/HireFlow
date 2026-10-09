import apiClient from "./client";
import type { BusinessUnit, UnitResume, UserSummary } from "@/lib/types";

export const unitsApi = {
  listUnits: async (): Promise<BusinessUnit[]> => {
    const { data } = await apiClient.get<BusinessUnit[]>("/units");
    return data;
  },

  getMyUnits: async (): Promise<BusinessUnit[]> => {
    const { data } = await apiClient.get<BusinessUnit[]>("/users/me/units");
    return data;
  },

  assignMyUnits: async (unitIds: string[]): Promise<void> => {
    await apiClient.post("/users/me/units", { unit_ids: unitIds });
  },

  getUnitResumesForJob: async (jobId: string): Promise<UnitResume[]> => {
    const { data } = await apiClient.get<UnitResume[]>(
      `/jobs/${jobId}/unit-resumes`
    );
    return data;
  },
};

export const usersApi = {
  listUsers: async (): Promise<UserSummary[]> => {
    const { data } = await apiClient.get<UserSummary[]>("/users");
    return data;
  },
};
