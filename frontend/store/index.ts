import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  User,
  Resume,
  JobDescription,
  ScreeningResult,
  DashboardStats,
  UploadBatch,
} from "@/lib/types";

// ─── Auth Store ───────────────────────────────────────────

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      logout: () => set({ user: null, isAuthenticated: false }),
    }),
    { name: "auth-store" }
  )
);

// ─── Resume Upload Store ──────────────────────────────────

interface UploadState {
  batch: UploadBatch | null;
  files: File[];
  uploadProgress: number;
  isUploading: boolean;
  setBatch: (batch: UploadBatch | null) => void;
  setFiles: (files: File[]) => void;
  setUploadProgress: (progress: number) => void;
  setIsUploading: (isUploading: boolean) => void;
  reset: () => void;
}

export const useUploadStore = create<UploadState>((set) => ({
  batch: null,
  files: [],
  uploadProgress: 0,
  isUploading: false,
  setBatch: (batch) => set({ batch }),
  setFiles: (files) => set({ files }),
  setUploadProgress: (uploadProgress) => set({ uploadProgress }),
  setIsUploading: (isUploading) => set({ isUploading }),
  reset: () =>
    set({ batch: null, files: [], uploadProgress: 0, isUploading: false }),
}));

// ─── Screening Store ──────────────────────────────────────

interface ScreeningState {
  currentJob: JobDescription | null;
  results: ScreeningResult[];
  selectedResults: Set<string>;
  isScreening: boolean;
  screeningProgress: number;
  setCurrentJob: (job: JobDescription | null) => void;
  setResults: (results: ScreeningResult[]) => void;
  toggleSelected: (resultId: string) => void;
  selectAll: () => void;
  clearSelection: () => void;
  setIsScreening: (isScreening: boolean) => void;
  setScreeningProgress: (progress: number) => void;
  reset: () => void;
}

export const useScreeningStore = create<ScreeningState>((set, get) => ({
  currentJob: null,
  results: [],
  selectedResults: new Set(),
  isScreening: false,
  screeningProgress: 0,
  setCurrentJob: (currentJob) => set({ currentJob }),
  setResults: (results) => set({ results }),
  toggleSelected: (resultId) => {
    const selected = new Set(get().selectedResults);
    if (selected.has(resultId)) {
      selected.delete(resultId);
    } else {
      selected.add(resultId);
    }
    set({ selectedResults: selected });
  },
  selectAll: () => {
    const all = new Set(get().results.map((r) => r.result_id));
    set({ selectedResults: all });
  },
  clearSelection: () => set({ selectedResults: new Set() }),
  setIsScreening: (isScreening) => set({ isScreening }),
  setScreeningProgress: (screeningProgress) => set({ screeningProgress }),
  reset: () =>
    set({
      currentJob: null,
      results: [],
      selectedResults: new Set(),
      isScreening: false,
      screeningProgress: 0,
    }),
}));

// ─── Dashboard Store ──────────────────────────────────────

interface DashboardState {
  stats: DashboardStats | null;
  resumes: Resume[];
  jobs: JobDescription[];
  setStats: (stats: DashboardStats) => void;
  setResumes: (resumes: Resume[]) => void;
  setJobs: (jobs: JobDescription[]) => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  stats: null,
  resumes: [],
  jobs: [],
  setStats: (stats) => set({ stats }),
  setResumes: (resumes) => set({ resumes }),
  setJobs: (jobs) => set({ jobs }),
}));
