"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { triggerScrape } from "@/lib/api";
import { toast } from "sonner";

export default function RefreshButton() {
  const [loading, setLoading] = useState(false);

  async function handleRefresh() {
    console.log('Refresh button clicked');
    setLoading(true);
    try {
      console.log('Calling triggerScrape...');
      const result = await triggerScrape();
      console.log('Scrape triggered, result:', result);
      toast.success("Scrape started! Check Settings to view progress.");
      console.log('Toast called');
    } catch (error) {
      console.error("Scrape error:", error);
      toast.error("Failed to start scrape. Please try again.");
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
