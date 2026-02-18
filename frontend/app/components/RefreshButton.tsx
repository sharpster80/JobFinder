"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { triggerScrape } from "@/lib/api";
import { toast } from "sonner";

export default function RefreshButton() {
  const [loading, setLoading] = useState(false);

  async function handleRefresh() {
    setLoading(true);
    try {
      await triggerScrape();
      toast.success("Scrape started! Check Settings to view progress.");
    } catch (error) {
      toast.error("Failed to start scrape. Please try again.");
      console.error("Scrape error:", error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Button onClick={handleRefresh} disabled={loading}>
      {loading ? "Starting..." : "Refresh Now"}
    </Button>
  );
}
