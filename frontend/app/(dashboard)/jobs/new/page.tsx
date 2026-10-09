"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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
import { ArrowLeft, Briefcase, Minus, Plus } from "lucide-react";
import toast from "react-hot-toast";

const EMPLOYEE_TYPE_OPTIONS = ["Full-time", "Contract", "Internship"];
const LOCATION_OFFICE_OPTIONS = ["Kothrud", "Baner", "Hinjewadi"];

export default function NewJobPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [units, setUnits] = useState<BusinessUnit[]>([]);
  const [users, setUsers] = useState<UserSummary[]>([]);

  // Form state
  const [jdText, setJdText] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [company, setCompany] = useState("Harbinger");
  const [businessUnitId, setBusinessUnitId] = useState("");
  const [minExperience, setMinExperience] = useState(0);
  const [maxExperience, setMaxExperience] = useState(0);
  const [employeeType, setEmployeeType] = useState("");
  const [locationOffice, setLocationOffice] = useState("");
  const [remoteJob, setRemoteJob] = useState(false);
  const [recruiterId, setRecruiterId] = useState("");
  const [selectedLeads, setSelectedLeads] = useState<string[]>([]);
  const [validTill, setValidTill] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 30);
    return d.toISOString().split("T")[0];
  });

  useEffect(() => {
    Promise.all([unitsApi.listUnits(), usersApi.listUsers()]).then(
      ([u, us]) => {
        setUnits(u);
        setUsers(us);
      }
    );
  }, []);

  const toggleLead = (userId: string) => {
    setSelectedLeads((prev) =>
      prev.includes(userId)
        ? prev.filter((id) => id !== userId)
        : [...prev, userId]
    );
  };

  const handleSubmit = async () => {
    if (!jobTitle.trim()) {
      toast.error("Job title is required");
      return;
    }
    if (!company.trim()) {
      toast.error("Company name is required");
      return;
    }
    if (!businessUnitId) {
      toast.error("Business unit is required");
      return;
    }
    if (maxExperience < minExperience) {
      toast.error("Maximum experience must be >= minimum experience");
      return;
    }
    if (!employeeType) {
      toast.error("Employee type is required");
      return;
    }
    if (!remoteJob && !locationOffice) {
      toast.error("Office location is required for non-remote jobs");
      return;
    }
    if (!recruiterId) {
      toast.error("Recruiter is required");
      return;
    }
    if (!validTill) {
      toast.error("Posting end date is required");
      return;
    }
    if (selectedLeads.length === 0) {
      toast.error("At least one hiring lead is required");
      return;
    }
    if (!jdText.trim()) {
      toast.error("Job description text is required");
      return;
    }

    setSubmitting(true);
    const experienceStr = `${minExperience}-${maxExperience} yrs`;
    try {
      await jobsApi.createJob({
        job_description_text: jdText,
        job_title: jobTitle,
        company: company,
        business_unit_id: businessUnitId,
        experience: experienceStr,
        employee_type: employeeType,
        location_office: remoteJob ? undefined : locationOffice,
        remote_job: remoteJob,
        hiring_leads: selectedLeads,
        recruiter_id: recruiterId,
        valid_till: validTill ? new Date(validTill).toISOString() : undefined,
      });
      toast.success("Job posting created successfully!");
      router.push("/jobs");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create job");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Header
        title="New Job Posting"
        subtitle="Create a new active job posting with full metadata"
      />
      <div className="flex-1 p-8 max-w-3xl mx-auto w-full space-y-6">
        <Link
          href="/jobs"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Jobs
        </Link>

        {/* Job Details Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Briefcase className="w-5 h-5 text-blue-500" />
              Job Details
            </CardTitle>
            <CardDescription>
              Fill in the job metadata. The JD text will be parsed by AI to
              extract skills and requirements. All fields marked with <span className="text-red-500">*</span> are required.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              label="Job Title"
              placeholder="e.g. Senior Backend Engineer"
              value={jobTitle}
              onChange={(e) => setJobTitle(e.target.value)}
              disabled={submitting}
              required
            />

            <Input
              label="Company Name"
              placeholder="e.g. Harbinger"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              disabled={submitting}
              required
            />

            {/* Business Unit */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-gray-700">
                Business Unit <span className="text-red-500">*</span>
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
                  Minimum Experience <span className="text-red-500">*</span>
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
                  Maximum Experience <span className="text-red-500">*</span>
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
                    onClick={() => setMaxExperience(Math.min(50, maxExperience + 1))}
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
                Employee Type <span className="text-red-500">*</span>
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
                  Office Location {!remoteJob && <span className="text-red-500">*</span>}
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
                Recruiter <span className="text-red-500">*</span>
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
                Posting End Date <span className="text-red-500">*</span>
              </label>
              <input
                type="date"
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
                value={validTill}
                onChange={(e) => setValidTill(e.target.value)}
                disabled={submitting}
              />
              <p className="text-xs text-gray-400">
                Job posting will expire after this date. Defaults to 30 days from today.
              </p>
            </div>

            {/* Hiring Leads */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-gray-700">
                Hiring Leads <span className="text-red-500">*</span>
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
                  {selectedLeads.length} lead{selectedLeads.length > 1 ? "s" : ""} selected
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* JD Text Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Job Description Text <span className="text-red-500">*</span>
            </CardTitle>
            <CardDescription>
              Paste the full job description. AI will parse skills, experience
              requirements, and more.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-1.5">
              <textarea
                className="w-full h-64 px-3 py-2 text-sm rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y disabled:bg-gray-50 disabled:text-gray-500"
                placeholder="Paste your full job description here…"
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                disabled={submitting}
              />
              <p className="text-xs text-gray-400">
                {jdText.length} characters ·{" "}
                {jdText.split(/\s+/).filter(Boolean).length} words
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Link href="/jobs">
            <Button variant="outline" disabled={submitting}>
              Cancel
            </Button>
          </Link>
          <Button
            onClick={handleSubmit}
            disabled={submitting}
            isLoading={submitting}
          >
            Create Job Posting
          </Button>
        </div>
      </div>
    </div>
  );
}
