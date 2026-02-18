"use client";
import { useState } from "react";
import { updateJobStatus } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type Job = {
  id: string; match_id: string; title: string; company: string;
  source: string; salary_min: number | null; salary_max: number | null;
  match_score: number; status: string; url: string; posted_at: string | null;
  is_remote: boolean;
};

const STATUS_COLORS: Record<string, string> = {
  new: "bg-blue-100 text-blue-800",
  saved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  applied: "bg-purple-100 text-purple-800",
  reviewed: "bg-gray-100 text-gray-800",
};

function formatSalary(min: number | null, max: number | null): string {
  if (!min && !max) return "—";
  if (min && max) return `$${Math.round(min / 1000)}K – $${Math.round(max / 1000)}K`;
  if (min) return `$${Math.round(min / 1000)}K+`;
  return `Up to $${Math.round((max as number) / 1000)}K`;
}

export default function JobTable({ initialJobs }: { initialJobs: Job[] }) {
  const [jobs, setJobs] = useState(initialJobs);

  async function changeStatus(matchId: string, status: string) {
    await updateJobStatus(matchId, status);
    setJobs(jobs.map(j => j.match_id === matchId ? { ...j, status } : j));
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
          <tr>
            <th className="px-4 py-3 text-left">Title</th>
            <th className="px-4 py-3 text-left">Company</th>
            <th className="px-4 py-3 text-left">Source</th>
            <th className="px-4 py-3 text-left">Salary</th>
            <th className="px-4 py-3 text-center">Score</th>
            <th className="px-4 py-3 text-left">Status</th>
            <th className="px-4 py-3 text-left">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {jobs.map(job => (
            <tr key={job.match_id} className="hover:bg-gray-50">
              <td className="px-4 py-3">
                <a href={job.url} target="_blank" className="font-medium text-blue-600 hover:underline">
                  {job.title}
                </a>
              </td>
              <td className="px-4 py-3 text-gray-700">{job.company}</td>
              <td className="px-4 py-3">
                <Badge variant="outline">{job.source}</Badge>
              </td>
              <td className="px-4 py-3 text-gray-700">{formatSalary(job.salary_min, job.salary_max)}</td>
              <td className="px-4 py-3 text-center">
                <span className={`font-bold ${job.match_score >= 80 ? "text-green-600" : job.match_score >= 60 ? "text-yellow-600" : "text-gray-500"}`}>
                  {job.match_score}
                </span>
              </td>
              <td className="px-4 py-3">
                <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_COLORS[job.status] || ""}`}>
                  {job.status}
                </span>
              </td>
              <td className="px-4 py-3 flex gap-1">
                <Button size="sm" variant="outline" onClick={() => changeStatus(job.match_id, "saved")}>Save</Button>
                <Button size="sm" variant="outline" onClick={() => changeStatus(job.match_id, "applied")}>Applied</Button>
                <Button size="sm" variant="ghost" onClick={() => changeStatus(job.match_id, "rejected")}>✕</Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {jobs.length === 0 && (
        <p className="text-center py-12 text-gray-400">No matches yet. Trigger a scrape to get started.</p>
      )}
    </div>
  );
}
