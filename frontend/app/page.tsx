import { getJobs, getCriteria, triggerScrape } from "@/lib/api";
import JobTable from "./components/JobTable";
import { Button } from "@/components/ui/button";

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; min_score?: string; criteria_id?: string }>;
}) {
  const params = await searchParams;
  const jobs = await getJobs({
    status: params.status,
    min_score: params.min_score ? Number(params.min_score) : undefined,
    criteria_id: params.criteria_id,
  });

  return (
    <main className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Job Matches</h1>
        <form action={async () => { "use server"; await triggerScrape(); }}>
          <Button type="submit">Refresh Now</Button>
        </form>
      </div>

      <div className="flex gap-3 mb-4 flex-wrap">
        {["new", "saved", "applied", "rejected"].map(s => (
          <a key={s} href={`?status=${s}`}
            className="px-3 py-1 rounded-full text-sm border hover:bg-gray-100 capitalize">
            {s}
          </a>
        ))}
        <a href="/" className="px-3 py-1 rounded-full text-sm border hover:bg-gray-100">All</a>
      </div>

      <div className="bg-white rounded-lg border shadow-sm">
        <JobTable initialJobs={jobs} />
      </div>
    </main>
  );
}
