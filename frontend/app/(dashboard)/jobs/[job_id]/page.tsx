"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  Eye,
  MapPin,
  Clock,
  Users,
  ArrowLeft,
  Search,
  Upload,
  Pencil,
  Save,
  X,
} from "lucide-react";
import { Header } from "@/components/layouts/Header";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { jobsApi } from "@/lib/api/jobs";
import { unitsApi } from "@/lib/api/units";
import type { JobDescription, UnitResume, JobStatus } from "@/lib/types";
import toast from "react-hot-toast";

function MetaRow({
  label,
  value,
}: {
  label: string;
  value?: string | null;
}) {
  return (
    <div>
      <p className="text-xs text-gray-500 font-medium">{label}</p>
      <p className="text-sm text-gray-700 mt-0.5">{value ?? "—"}</p>
    </div>
  );
}

function JobStatusBadge({ status }: { status: JobStatus }) {
  const config: Record<JobStatus, { label: string; cls: string }> = {
    active: {
      label: "Active",
      cls: "bg-green-100 text-green-800 border-green-200",
    },
    expired: {
      label: "Expired",
      cls: "bg-red-100 text-red-800 border-red-200",
    },
    filled: {
      label: "Filled",
      cls: "bg-gray-100 text-gray-600 border-gray-200",
    },
    paused: {
      label: "Paused",
      cls: "bg-yellow-100 text-yellow-800 border-yellow-200",
    },
  };
  const { label, cls } = config[status] ?? config.active;
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${cls}`}
    >
      {label}
    </span>
  );
}

function computeStatus(job: JobDescription): JobStatus {
  if (job.status === "active" && job.valid_till) {
    if (new Date(job.valid_till) < new Date()) return "expired";
  }
  return (job.status as JobStatus) ?? "active";
}

export default function JobPositionPage() {
  const params = useParams();
  const jobId = params.job_id as string;

  const [job, setJob] = useState<JobDescription | null>(null);
  const [unitResumes, setUnitResumes] = useState<UnitResume[]>([]);
  const [loading, setLoading] = useState(true);

  // JD text editing
  const [editingJd, setEditingJd] = useState(false);
  const [jdDraft, setJdDraft] = useState("");
  const [savingJd, setSavingJd] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    Promise.all([jobsApi.getJob(jobId), unitsApi.getUnitResumesForJob(jobId)])
      .then(([j, resumes]) => {
        setJob(j);
        setUnitResumes(resumes);
      })
      .finally(() => setLoading(false));
  }, [jobId]);

  const handlePreview = (resumeId: string) => {
    window.open(
      `${process.env.NEXT_PUBLIC_API_URL}/resumes/${resumeId}/file`,
      "_blank"
    );
  };

  if (loading) {
    return (
      <div className="flex flex-col min-h-screen">
        <Header title="Job Position" subtitle="Loading…" />
        <div className="flex-1 flex items-center justify-center">
          <div className="spinner w-8 h-8" />
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="flex flex-col min-h-screen">
        <Header title="Job Not Found" subtitle="" />
        <div className="flex-1 flex items-center justify-center text-gray-500">
          Job not found or you don't have access.
        </div>
      </div>
    );
  }

  const status = computeStatus(job);

  return (
    <div className="flex flex-col min-h-screen">
      <Header
        title={job.job_title}
        subtitle={`Job ID: ${job.job_id}`}
      />

      <div className="flex-1 p-8 max-w-7xl mx-auto w-full">
        <Link
          href="/jobs"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Jobs
        </Link>

        <div className="flex gap-6">
          {/* LEFT 70% — Full JD + Unit Resumes */}
          <div className="flex-[7] min-w-0 space-y-6">
            {/* Job Description Card */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>{job.job_title}</CardTitle>
                    <CardDescription>
                      {[job.company, job.location].filter(Boolean).join(" · ")}
                      {job.experience
                        ? ` · ${job.experience} experience`
                        : job.required_min_exp_years > 0
                        ? ` · ${job.required_min_exp_years}+ yrs experience`
                        : ""}
                    </CardDescription>
                  </div>
                  <JobStatusBadge status={status} />
                </div>
              </CardHeader>
              <CardContent>
                {job.required_skills.length > 0 ? (
                  <div className="space-y-3 mb-6">
                    {(() => {
                      const niceSet = new Set((job.nice_to_have_skills || []).map(s => s.toLowerCase()));
                      const required = job.required_skills.filter(s => !niceSet.has(s.skill.toLowerCase()));
                      // Collect all nice-to-have: from required_skills that overlap + standalone nice_to_have_skills
                      const niceFromRequired = job.required_skills.filter(s => niceSet.has(s.skill.toLowerCase())).map(s => s.skill);
                      const niceStandalone = (job.nice_to_have_skills || []).filter(s => !job.required_skills.some(rs => rs.skill.toLowerCase() === s.toLowerCase()));
                      const allNice = [...niceFromRequired, ...niceStandalone];
                      return (
                        <>
                          {required.length > 0 && (
                            <div>
                              <p className="text-xs text-gray-500 font-medium mb-1.5">Required Skills</p>
                              <div className="flex flex-wrap gap-2">
                                {required.map((s) => (
                                  <span
                                    key={s.skill}
                                    className="text-xs bg-blue-100 text-blue-700 px-2.5 py-1 rounded-full font-medium"
                                  >
                                    {s.skill}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                          {allNice.length > 0 && (
                            <div>
                              <p className="text-xs text-gray-500 font-medium mb-1.5">Nice to Have</p>
                              <div className="flex flex-wrap gap-2">
                                {allNice.map((s) => (
                                  <span
                                    key={s}
                                    className="text-xs bg-gray-100 text-gray-600 px-2.5 py-1 rounded-full font-medium"
                                  >
                                    {s}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </>
                      );
                    })()}
                    <button
                      className="text-xs text-blue-600 hover:text-blue-800 font-medium underline"
                      onClick={async () => {
                        try {
                          const updated = await jobsApi.reparseJob(job.job_id);
                          setJob(updated);
                          toast.success(`Re-parsed: ${updated.required_skills.length} required, ${(updated.nice_to_have_skills || []).length} nice-to-have`);
                        } catch (err: unknown) {
                          const msg = err instanceof Error ? err.message : "Re-parse failed";
                          toast.error(msg);
                        }
                      }}
                    >
                      Re-parse JD
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-3 mb-6 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <span className="text-sm text-amber-700">
                      No skills extracted from this JD yet.
                    </span>
                    <button
                      className="text-sm text-blue-600 hover:text-blue-800 font-medium underline"
                      onClick={async () => {
                        try {
                          const updated = await jobsApi.reparseJob(job.job_id);
                          setJob(updated);
                          toast.success(`Re-parsed: ${updated.required_skills.length} required, ${(updated.nice_to_have_skills || []).length} nice-to-have`);
                        } catch (err: unknown) {
                          const msg = err instanceof Error ? err.message : "Re-parse failed";
                          toast.error(msg);
                        }
                      }}
                    >
                      Re-parse JD
                    </button>
                  </div>
                )}
                {/* JD Text with inline edit */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-gray-500 font-medium">Job Description</p>
                    {!editingJd ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setJdDraft(job.job_description_full || "");
                          setEditingJd(true);
                        }}
                      >
                        <Pencil className="w-3 h-3" />
                        Edit
                      </Button>
                    ) : (
                      <div className="flex items-center gap-1.5">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={savingJd}
                          onClick={() => {
                            setEditingJd(false);
                            setJdDraft("");
                          }}
                        >
                          <X className="w-3 h-3" />
                          Cancel
                        </Button>
                        <Button
                          size="sm"
                          disabled={savingJd || jdDraft.trim() === job.job_description_full?.trim()}
                          isLoading={savingJd}
                          onClick={async () => {
                            if (!jdDraft.trim()) {
                              toast.error("Job description cannot be empty");
                              return;
                            }
                            setSavingJd(true);
                            try {
                              const updated = await jobsApi.updateJob(job.job_id, {
                                job_description_text: jdDraft.trim(),
                              });
                              setJob(updated);
                              setEditingJd(false);
                              setJdDraft("");
                              toast.success(
                                `JD updated & re-parsed: ${updated.required_skills.length} required, ${(updated.nice_to_have_skills || []).length} nice-to-have`
                              );
                            } catch (err: unknown) {
                              const msg = err instanceof Error ? err.message : "Failed to update JD";
                              toast.error(msg);
                            } finally {
                              setSavingJd(false);
                            }
                          }}
                        >
                          <Save className="w-3 h-3" />
                          Save & Re-parse
                        </Button>
                      </div>
                    )}
                  </div>
                  {editingJd ? (
                    <textarea
                      className="w-full min-h-[400px] p-3 text-sm text-gray-700 leading-relaxed border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y font-sans"
                      value={jdDraft}
                      onChange={(e) => setJdDraft(e.target.value)}
                      disabled={savingJd}
                    />
                  ) : (
                    <pre className="whitespace-pre-wrap font-sans text-sm text-gray-700 leading-relaxed">
                      {job.job_description_full}
                    </pre>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Unit Resumes Table */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="w-5 h-5 text-blue-500" />
                  Unit Resumes for {job.job_title}
                </CardTitle>
                <CardDescription>
                  Resumes uploaded by recruiters in your business unit(s) for
                  this position.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {unitResumes.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <Users className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                    <p className="font-medium">No resumes yet</p>
                    <p className="text-sm mt-1">
                      Upload resumes for this position from the Upload page.
                    </p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="text-left pb-3 pr-4 text-gray-500 font-medium">
                            Candidate
                          </th>
                          <th className="text-left pb-3 pr-4 text-gray-500 font-medium">
                            Email
                          </th>
                          <th className="text-left pb-3 pr-4 text-gray-500 font-medium">
                            Location
                          </th>
                          <th className="text-left pb-3 pr-4 text-gray-500 font-medium">
                            Experience
                          </th>
                          <th className="text-left pb-3 pr-4 text-gray-500 font-medium">
                            Status
                          </th>
                          <th className="text-left pb-3 text-gray-500 font-medium">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {unitResumes.map((r) => (
                          <tr
                            key={r.id}
                            className="hover:bg-gray-50 transition-colors"
                          >
                            <td className="py-3 pr-4">
                              <span className="font-medium text-gray-900">
                                {r.candidate_name ?? r.filename}
                              </span>
                            </td>
                            <td className="py-3 pr-4 text-gray-600">
                              {r.candidate_email ?? "—"}
                            </td>
                            <td className="py-3 pr-4 text-gray-600">
                              {r.candidate_location ? (
                                <span className="flex items-center gap-1">
                                  <MapPin className="w-3 h-3" />
                                  {r.candidate_location}
                                </span>
                              ) : (
                                "—"
                              )}
                            </td>
                            <td className="py-3 pr-4 text-gray-600">
                              {r.total_exp_years != null ? (
                                <span className="flex items-center gap-1">
                                  <Clock className="w-3 h-3" />
                                  {r.total_exp_years} yrs
                                </span>
                              ) : (
                                "—"
                              )}
                            </td>
                            <td className="py-3 pr-4">
                              <span
                                className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                                  r.parse_status === "completed"
                                    ? "bg-green-100 text-green-700"
                                    : r.parse_status === "failed"
                                    ? "bg-red-100 text-red-700"
                                    : "bg-yellow-100 text-yellow-700"
                                }`}
                              >
                                {r.parse_status}
                              </span>
                            </td>
                            <td className="py-3">
                              <button
                                onClick={() => handlePreview(r.id)}
                                className="inline-flex items-center gap-1.5 text-blue-600 hover:text-blue-800 text-xs font-medium transition-colors"
                              >
                                <Eye className="w-3 h-3" />
                                Preview
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* RIGHT 30% — Metadata Sidebar */}
          <div className="flex-[3] min-w-0 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Job Info</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <MetaRow label="Company" value={job.company} />
                <MetaRow label="Unit" value={job.unit_name} />
                <MetaRow label="Experience" value={job.experience} />
                <MetaRow label="Type" value={job.employee_type} />
                <MetaRow label="Office" value={job.location_office} />
                <MetaRow
                  label="Remote"
                  value={job.remote_job ? "Yes" : "No"}
                />
                <MetaRow label="Recruiter" value={job.recruiter_name} />

                {job.hiring_lead_names && job.hiring_lead_names.length > 0 && (
                  <div>
                    <p className="text-xs text-gray-500 font-medium mb-1">
                      Hiring Leads
                    </p>
                    {job.hiring_lead_names.map((hl) => (
                      <p key={hl.id} className="text-sm text-gray-700">
                        {hl.name}
                      </p>
                    ))}
                  </div>
                )}

                <MetaRow
                  label="Uploaded"
                  value={new Date(job.created_at).toLocaleDateString()}
                />
                <MetaRow
                  label="Valid Till"
                  value={
                    job.valid_till
                      ? new Date(job.valid_till).toLocaleDateString()
                      : "—"
                  }
                />

                <div className="pt-2 border-t border-gray-100">
                  <p className="text-xs text-gray-500 font-medium mb-1">
                    Unit Resumes
                  </p>
                  <p className="text-2xl font-bold text-gray-900">
                    {unitResumes.length}
                  </p>
                  <p className="text-xs text-gray-500">from your unit(s)</p>
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardContent className="pt-6 space-y-2">
                <Link href={`/screen`} className="block">
                  <Button className="w-full">
                    <Search className="w-4 h-4" />
                    Screen Candidates
                  </Button>
                </Link>
                <Link href={`/upload`} className="block">
                  <Button variant="outline" className="w-full">
                    <Upload className="w-4 h-4" />
                    Upload Resumes
                  </Button>
                </Link>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
