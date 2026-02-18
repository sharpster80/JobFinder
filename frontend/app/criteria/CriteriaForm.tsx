"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// Client-side component always uses localhost for browser API calls
const API_URL = "http://localhost:8000";

type Criteria = {
  id?: string; name: string; titles: string[]; tech_stack: string[];
  min_salary: number; exclude_keywords: string[]; company_blacklist: string[];
  company_whitelist: string[]; is_active: boolean;
};

const empty: Criteria = {
  name: "", titles: [], tech_stack: [], min_salary: 125000,
  exclude_keywords: [], company_blacklist: [], company_whitelist: [], is_active: true,
};

function TagInput({ label, value, onChange }: { label: string; value: string[]; onChange: (v: string[]) => void }) {
  const [input, setInput] = useState("");
  return (
    <div>
      <label className="text-sm font-medium text-gray-700">{label}</label>
      <div className="flex gap-2 mt-1">
        <Input value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && input.trim()) { onChange([...value, input.trim()]); setInput(""); e.preventDefault(); }}}
          placeholder="Type and press Enter" />
      </div>
      <div className="flex flex-wrap gap-1 mt-2">
        {value.map(v => (
          <span key={v} className="bg-gray-100 px-2 py-0.5 rounded text-sm flex items-center gap-1">
            {v}
            <button onClick={() => onChange(value.filter(x => x !== v))} className="text-gray-400 hover:text-red-500">×</button>
          </span>
        ))}
      </div>
    </div>
  );
}

export default function CriteriaForm({ existing }: { existing: Criteria[] }) {
  const [list, setList] = useState<Criteria[]>(existing);
  const [editing, setEditing] = useState<Criteria | null>(null);

  async function save(c: Criteria) {
    try {
      const method = c.id ? "PUT" : "POST";
      const url = c.id ? `${API_URL}/api/criteria/${c.id}` : `${API_URL}/api/criteria`;
      const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(c) });
      if (!res.ok) {
        throw new Error(`Failed to save: ${res.status} ${res.statusText}`);
      }
      const saved = await res.json();
      if (c.id) setList(list.map(x => x.id === c.id ? saved : x));
      else setList([...list, saved]);
      setEditing(null);
    } catch (error) {
      console.error('Error saving criteria:', error);
      alert(`Error saving criteria: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async function remove(id: string) {
    await fetch(`${API_URL}/api/criteria/${id}`, { method: "DELETE" });
    setList(list.filter(x => x.id !== id));
  }

  const form = editing || empty;

  return (
    <div className="grid grid-cols-2 gap-8">
      <div>
        <h2 className="font-semibold mb-3">Active Criteria Sets</h2>
        {list.map(c => (
          <div key={c.id} className="border rounded p-3 mb-2 flex justify-between items-start">
            <div>
              <div className="font-medium">{c.name}</div>
              <div className="text-sm text-gray-500">{c.titles.join(", ")} · ${c.min_salary.toLocaleString()}+</div>
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => setEditing(c)}>Edit</Button>
              <Button size="sm" variant="ghost" onClick={() => c.id && remove(c.id)}>Delete</Button>
            </div>
          </div>
        ))}
        <Button onClick={() => setEditing({...empty})} className="mt-2">+ New Criteria Set</Button>
      </div>

      {editing && (
        <div className="border rounded p-4">
          <h2 className="font-semibold mb-4">{editing.id ? "Edit" : "New"} Criteria Set</h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Name</label>
              <Input value={form.name} onChange={e => setEditing({...form, name: e.target.value})} className="mt-1" />
            </div>
            <TagInput label="Target Titles" value={form.titles} onChange={v => setEditing({...form, titles: v})} />
            <TagInput label="Tech Stack" value={form.tech_stack} onChange={v => setEditing({...form, tech_stack: v})} />
            <div>
              <label className="text-sm font-medium">Min Salary ($)</label>
              <Input type="number" value={form.min_salary} onChange={e => setEditing({...form, min_salary: Number(e.target.value)})} className="mt-1" />
            </div>
            <TagInput label="Exclude Keywords" value={form.exclude_keywords} onChange={v => setEditing({...form, exclude_keywords: v})} />
            <TagInput label="Company Blacklist" value={form.company_blacklist} onChange={v => setEditing({...form, company_blacklist: v})} />
            <TagInput label="Company Whitelist" value={form.company_whitelist} onChange={v => setEditing({...form, company_whitelist: v})} />
            <div className="flex gap-2 pt-2">
              <Button onClick={() => save(form)}>Save</Button>
              <Button variant="outline" onClick={() => setEditing(null)}>Cancel</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
