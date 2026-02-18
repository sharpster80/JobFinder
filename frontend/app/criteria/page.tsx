import { getCriteria } from "@/lib/api";
import CriteriaForm from "./CriteriaForm";

export default async function CriteriaPage() {
  const criteria = await getCriteria();
  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Search Criteria</h1>
      <CriteriaForm existing={criteria} />
    </main>
  );
}
