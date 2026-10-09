"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Header } from "@/components/layouts/Header";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { jobsApi } from "@/lib/api/jobs";
import { unitsApi, usersApi } from "@/lib/api/units";
import type { BusinessUnit, UserSummary } from "@/lib/types";
import { ArrowLeft, Save, Minus, Plus } from "lucide-react";
import toast from "react-hot-toast";

const EMPLOYEE_TYPE_OPTIONS = ["Full-time", "Contract", "Internship"];
const LOCATION_OFFICE_OPTIONS = ["Kothrud", "Baner", "Hinjewadi"];

function parseExperience(exp: string): { min: number; max: number } {
  if (!exp) return { min: 0, max: 0 };
  const rangeMatch = exp.match(/^(\d+)\s*-\s*(\d+)/);
  if (rangeMatch) return { min: parseInt(rangeMatch[1]), max: parseInt(rangeMatch[2]) };
  const plusMatch = exp.match(/^(\d+)\+/);
  if (plusMatch) return { min: parseInt(plusMatch[1]), max: parseInt(plusMatch[1]) + 5 };
  const singleMatch = exp.match(/^(\d+)/);
  if (singleMatch) return { min: parseInt(singleMatch[1]), max: parseInt(singleMatch[1]) };
  return { min: 0, max: 0 };
}

export default function EditJobPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.job_id as string;

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [units, setUnits] = useState<BusinessUnit[]>([]);
  const [users, setUsers] = useState<UserSummary[]>([]);

  // Form state
  const [jobTitle, setJobTitle] = useState("");
  const [company, setCompany] = useState("");
  const [businessUnitId, setBusinessUnitId] = useState("");
  const [minExperience, setMinExperience] = useState(0);
  const [maxExperience, setMaxExperience] = useState(0);
  const [employeeType, setEmployeeType] = useState("");
  const [locationOffice, setLocationOffice] = useState("");
  const [remoteJob, setRemoteJob] = useState(false);
  const [recruiterId, setRecruiterId] = useState("");
  const [selectedLeads, setSelectedLeads] = useState<string[]>([]);
  const [validTill, setValidTill] = useState("");

  useEffect(() => {
    Promise.all([
      jobsApi.getJob(jobId),
      unitsApi.listUnits(),
      usersApi.listUsers(),
    ]).then(([job, u, us]) => {
      setUnits(u);
      setUsers(us);
      // Populate form from existing job
      setJobTitle(job.job_title || "");
      setCompany(job.company || "");
      setBusinessUnitId(job.business_unit_id || "");
      const parsed = parseExperience(job.experience || "");
      setMinExperience(parsed.min);
      setMaxExperience(parsed.max);
      setEmployeeType(job.employee_type || "");
      setLocationOffice(job.location_office || "");
      setRemoteJob(job.remote_job || false);
      setRecruiterId(job.recruiter_id || "");
      setSelectedLeads(job.hiring_leads || []);
      if (job.valid_till) {
        setValidTill(new Date(job.valid_till).toISOString().split("T")[0]);
      }
      setLoading(false);
    }).catch(() => {
      toast.error("Failed to load job details");
      setLoading(false);
    });
  }, [jobId]);

  const toggleLead = (userId: string) => {
    setSelectedLeads((prev) =>
      prev.includes(userId)
        ? prev.filter((id) => id !== userId)
        : [...prev, userId]
    );
  };

  const handleSubmit = async () => {
    if (maxExperience < minExperience) {
      toast.error("Maximum experience must be >= minimum experience");
      return;
    }
    setSubmitting(true);
    const experienceStr = `${minExperience}-${maxExperience} yrs`;
    try {
      await jobsApi.updateJob(jobId, {
        job_title: jobTitle,
        company: company,
        business_unit_id: businessUnitId || "",
        experience: experienceStr,
        employee_type: employeeType || "",
        location_office: remoteJob ? "" : locationOffice || "",
        remote_job: remoteJob,
        hiring_leads: selectedLeads,
        recruiter_id: recruiterId || "",
        valid_till: validTill ? new Date(validTill).toISOString() : undefined,
      });
      toast.success("Job posting updated successfully!");
      router.push(`/jobs/${jobId}`);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to update job"
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col min-h-screen">
        <Header title="Edit Job Posting" subtitle="Loading..." />
        <div className="flex-1 flex justify-center items-center">
          <div className="spinner w-8 h-8" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Header
        title="Edit Job Posting"
        subtitle="Update job posting details and metadata"
      />
      <div className="flex-1 p-8 max-w-3xl mx-auto w-full space-y-6">
        <Link
          href={`/jobs/${jobId}`}
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Job Details
        </Link>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Job Details</CardTitle>
            <CardDescription>
              Update the job posting metadata. Changes are saved immediately.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              label="Job Title"
              placeholder="e.g. Senior Backend Engineer"
              value={jobTitle}
              onChange={(e) => setJobTitle(e.target.value)}
              disabled={submitting}
            />

            <Input
              label="Company Name"
              placeholder="e.g. Harbinger"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              disabled={submitting}
            />

            {/* Business Unit */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-gray-700">
                Business Unit
              </label>
              <select
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
                value={businessUnitId}
                onChange={(e) => setBusinessUnitId(e.target.value)}
                disabled={submitting}
              >
                <option value="">Select a unit…</option>
                {units.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.unit_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Min Experience + Max Experience */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="block text-sm font-medium text-gray-700">
                  Minimum Experience
                </label>
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    className="w-8 h-8 flex items-center justify-center rounded-lg border border-gray-300 bg-gray-50 hover:bg-gray-100 text-gray-600 disabled:opacity-40 disabled:cursor-not-allowed"
                    onClick={() => {
                      const newMin = Math.max(0, minExperience - 1);
                      setMinExperience(newMin);
                    }}
                    disabled={submitting || minExperience <= 0}
                  >
                    <Minus className="w-3.5 h-3.5" />
                  </button>
                  <input
                    type="number"
                    className="w-16 text-center px-2 py-1.5 text-sm rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                    value={minExperience}
                    onChange={(e) => {
                      const v = Math.max(0, Math.min(50, parseInt(e.target.value) || 0));
                      setMinExperience(v);
                      if (v > maxExperience) setMaxExperience(v);
                    }}
                    min={0}
                    max={50}
                    disabled={submitting}
                  />
                  <button
                    type="button"
                    className="w-8 h-8 flex items-center justify-center rounded-lg border border-gray-300 bg-gray-50 hover:bg-gray-100 text-gray-600 disabled:opacity-40 disabled:cursor-not-allowed"
                    onClick={() => {
                      const newMin = Math.min(50, minExperience + 1);
                      setMinExperience(newMin);
                      if (newMin > maxExperience) setMaxExperience(newMin);
                    }}
                    disabled={submitting || minExperience >= 50}
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                  <span className="text-sm text-gray-500 ml-1">yrs</span>
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="block text-sm font-medium text-gray-700">
                  Maximum Experience
                </label>
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    className="w-8 h-8 flex items-center justify-center rounded-lg border border-gray-300 bg-gray-50 hover:bg-gray-100 text-gray-600 disabled:opacity-40 disabled:cursor-not-allowed"
                    onClick={() => {
                      const newMax = Math.max(0, maxExperience - 1);
                      setMaxExperience(newMax);
                      if (newMax < minExperience) setMinExperience(newMax);
                    }}
                    disabled={submitting || maxExperience <= 0}
                  >
                    <Minus className="w-3.5 h-3.5" />
                  </button>
                  <input
                    type="number"
                    className="w-16 text-center px-2 py-1.5 text-sm rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                    value={maxExperience}
                    onChange={(e) => {
                      const v = Math.max(0, Math.min(50, parseInt(e.target.value) || 0));
                      setMaxExperience(v);
                      if (v < minExperience) setMinExperience(v);
                    }}
                    min={0}
                    max={50}
                    disabled={submitting}
                  />
                  <button
                    type="button"
                    className="w-8 h-8 flex items-center justify-center rounded-lg border border-gray-300 bg-gray-50 hover:bg-gray-100 text-gray-600 disabled:opacity-40 disabled:cursor-not-allowed"
                    onClick={() => {
                      const newMax = Math.min(50, maxExperience + 1);
                      setMaxExperience(newMax);
                    }}
                    disabled={submitting || maxExperience >= 50}
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                  <span className="text-sm text-gray-500 ml-1">yrs</span>
                </div>
              </div>
            </div>

            {/* Employee Type */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-gray-700">
                Employee Type
              </label>
              <select
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
                value={employeeType}
                onChange={(e) => setEmployeeType(e.target.value)}
                disabled={submitting}
              >
                <option value="">Select…</option>
                {EMPLOYEE_TYPE_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>

            {/* Office Location + Remote */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="block text-sm font-medium text-gray-700">
                  Office Location
                </label>
                <select
                  className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60 disabled:bg-gray-100"
                  value={locationOffice}
                  onChange={(e) => setLocationOffice(e.target.value)}
                  disabled={submitting || remoteJob}
                >
                  <option value="">Select…</option>
                  {LOCATION_OFFICE_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
                {remoteJob && (
                  <p className="text-xs text-gray-400">
                    Disabled for remote positions
                  </p>
                )}
              </div>
              <div className="flex items-center gap-3 pt-6">
                <input
                  type="checkbox"
                  id="remote_job"
                  checked={remoteJob}
                  onChange={(e) => {
                    setRemoteJob(e.target.checked);
                    if (e.target.checked) setLocationOffice("");
                  }}
                  disabled={submitting}
                  className="w-4 h-4 text-blue-600 rounded border-gray-300"
                />
                <label
                  htmlFor="remote_job"
                  className="text-sm font-medium text-gray-700"
                >
                  Remote Job
                </label>
              </div>
            </div>

            {/* Recruiter */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-gray-700">
                Recruiter
              </label>
              <select
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
                value={recruiterId}
                onChange={(e) => setRecruiterId(e.target.value)}
                disabled={submitting}
              >
                <option value="">Select recruiter…</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name} ({u.email})
                  </option>
                ))}
              </select>
            </div>

            {/* Posting End Date */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-gray-700">
                Posting End Date
              </label>
              <input
                type="date"
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
                value={validTill}
                onChange={(e) => setValidTill(e.target.value)}
                disabled={submitting}
              />
            </div>

            {/* Hiring Leads */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-gray-700">
                Hiring Leads
              </label>
              <div className="border border-gray-200 rounded-lg divide-y divide-gray-100 max-h-40 overflow-y-auto">
                {users.length === 0 ? (
                  <p className="px-3 py-2 text-sm text-gray-400">
                    No users available
                  </p>
                ) : (
                  users.map((u) => (
                    <label
                      key={u.id}
                      className="flex items-center gap-3 px-3 py-2 hover:bg-gray-50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedLeads.includes(u.id)}
                        onChange={() => toggleLead(u.id)}
                        disabled={submitting}
                        className="w-4 h-4 text-blue-600 rounded border-gray-300"
                      />
                      <span className="text-sm text-gray-700">{u.name}</span>
                      <span className="text-xs text-gray-400">{u.email}</span>
                    </label>
                  ))
                )}
              </div>
              {selectedLeads.length > 0 && (
                <p className="text-xs text-gray-500">
                  {selectedLeads.length} lead
                  {selectedLeads.length > 1 ? "s" : ""} selected
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Link href={`/jobs/${jobId}`}>
            <Button variant="outline" disabled={submitting}>
              Cancel
            </Button>
          </Link>
          <Button
            onClick={handleSubmit}
            disabled={submitting}
            isLoading={submitting}
          >
            <Save className="w-4 h-4" />
            Save Changes
          </Button>
        </div>
      </div>
    </div>
  );
}
