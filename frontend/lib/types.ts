// ─────────────────────────────────────────────────────────
// Auth Types
// ─────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  name: string;
  company?: string;
  role: "recruiter" | "admin";
  createdAt: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials {
  email: string;
  password: string;
  name: string;
  company?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// ─────────────────────────────────────────────────────────
// Resume Types
// ─────────────────────────────────────────────────────────

export interface Education {
  degree: string;
  institution: string;
  year: number;
}

export interface ExperienceEntry {
  title: string;
  company: string;
  location: string;
  duration_start: string;
  duration_end: string;
  duration_years: number;
  description: string;
  achievements: string[];
  skills_used: string[];
}

export interface EmploymentGap {
  start: string;
  end: string;
  duration_months: number;
  explanation?: string;
}

export interface Certification {
  name: string;
  issuer: string;
  year: number;
}

export interface ParsedResume {
  candidate_id: string;
  candidate_name: string;
  email: string;
  phone?: string;
  location?: string;
  total_exp_years: number;
  recent_skills: string[];
  all_skills: string[];
  education: Education[];
  experience: ExperienceEntry[];
  employment_gaps: EmploymentGap[];
  certifications: Certification[];
}

export interface Resume {
  id: string;
  filename: string;
  file_size: number;
  upload_status: "pending" | "processing" | "completed" | "failed";
  parse_status: "pending" | "processing" | "completed" | "failed";
  parsed_data?: ParsedResume;
  candidate_name?: string;
  candidate_email?: string;
  unit_id?: string;
  unit_name?: string;
  job_position_id?: string;
  job_title?: string;
  file_mimetype?: string;
  is_indexed?: boolean;
  created_at: string;
  updated_at: string;
}

// ─────────────────────────────────────────────────────────
// Business Unit Types
// ─────────────────────────────────────────────────────────

export interface BusinessUnit {
  id: string;
  unit_slug: string;
  unit_name: string;
}

export interface UnitResume {
  id: string;
  filename: string;
  candidate_name: string | null;
  candidate_email: string | null;
  candidate_location: string | null;
  total_exp_years: number | null;
  unit_id: string;
  parse_status: string;
  created_at: string;
}

export interface UserSummary {
  id: string;
  name: string;
  email: string;
}

export type JobStatus = "active" | "expired" | "filled" | "paused";

export interface UploadBatch {
  batch_id: string;
  total_files: number;
  processed_files: number;
  failed_files: number;
  status: "pending" | "processing" | "completed" | "failed";
  created_at: string;
}

export interface BulkUploadResult extends UploadBatch {
  skipped_files?: string[];
  skipped_count?: number;
}

// ─────────────────────────────────────────────────────────
// Job Description Types
// ─────────────────────────────────────────────────────────

export interface RequiredSkill {
  skill: string;
  proficiency: "Beginner" | "Intermediate" | "Advanced" | "Expert";
  years_required: number;
}

export interface JobDescription {
  job_id: string;
  job_title: string;
  company?: string;
  location?: string;
  required_min_exp_years: number;
  preferred_min_exp_years?: number;
  required_skills: RequiredSkill[];
  nice_to_have_skills: string[];
  education_required?: string;
  locations_accepted: string[];
  willingness_to_relocate?: string;
  job_description_full: string;
  created_at: string;
  screening_count: number;
  // Lifecycle fields
  business_unit_id?: string;
  unit_name?: string;
  experience?: string;
  employee_type?: string;
  location_office?: string;
  remote_job?: boolean;
  hiring_leads?: string[];
  hiring_lead_names?: UserSummary[];
  recruiter_id?: string;
  recruiter_name?: string;
  valid_till?: string;
  status?: JobStatus;
}

// ─────────────────────────────────────────────────────────
// Screening Result Types
// ─────────────────────────────────────────────────────────

export type FitStatus = "EXCELLENT" | "GOOD" | "ADEQUATE" | "POOR";

export interface CategoryScores {
  skills_match: number;
  experience_relevance: number;
  career_progression: number;
  measurable_achievements: number;
}

export interface KnockoutFailure {
  rule: string;
  reason: string;
}

export interface SkillMatch {
  required_skill: string;
  candidate_skill: string;
  match_confidence: number;
  years_in_profile: number;
}

export interface SkillMissing {
  required_skill: string;
  candidate_has: boolean;
  importance: "high" | "medium" | "low";
}

export interface ScreeningResult {
  result_id: string;
  resume_id: string;
  job_id: string;
  rank: number;
  fit_score: number;
  status: FitStatus;
  passed_knockouts: boolean;
  knockout_failures: KnockoutFailure[];
  category_scores: CategoryScores;
  strengths: string[];
  weaknesses: string[];
  match_explanation: string;
  skills_matched: SkillMatch[];
  skills_missing: SkillMissing[];
  candidate_name: string;
  candidate_email: string;
  candidate_location?: string;
  total_exp_years: number;
  is_shortlisted: boolean;
  created_at: string;
  screening_time_ms: number;
}

export interface ScreeningJob {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  total_resumes: number;
  processed_resumes: number;
  results?: ScreeningResult[];
  created_at: string;
}

// ─────────────────────────────────────────────────────────
// Dashboard / Stats Types
// ─────────────────────────────────────────────────────────

export interface DashboardStats {
  total_resumes: number;
  total_jobs: number;
  total_screenings: number;
  total_shortlisted: number;
  avg_fit_score: number;
  shortlist_rate: number;
  recent_jobs: JobDescription[];
  top_skills_matched: { skill: string; percentage: number }[];
  top_skills_missing: { skill: string; percentage: number }[];
}

// ─────────────────────────────────────────────────────────
// API Response Types
// ─────────────────────────────────────────────────────────

export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  detail: string;
  status_code: number;
}
