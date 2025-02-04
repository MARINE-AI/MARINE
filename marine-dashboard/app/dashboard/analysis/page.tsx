// page.tsx
"use client"

import React, { useEffect, useState } from 'react';

interface AnalysisResult {
  video_id: string;
  match_score: number;
  active_matches: Array<{ crawled_video_id?: string; uploaded_video_id?: string; similarity: number }>;
  uploaded_frames: number;
  reference_frames: number;
}

export default function AnalysisResultPage() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchResult() {
      try {
        const formData = new FormData();
        formData.append("video_id", "your_video_id_here"); // Replace with actual video ID
        formData.append("total_chunks", "your_total_chunks_here"); // Replace with actual total chunk count

        const res = await fetch("http://localhost:8080/analyze", {
          method: "POST",
          body: formData,
        });
        if (!res.ok) throw new Error("Failed to fetch analysis result");
        const data = await res.json();
        setResult(data);
      } catch (error) {
        console.error("Error fetching analysis result:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchResult();
  }, []);

  if (loading) return <div>Loading analysis result...</div>;
  if (!result) return <div>No analysis result found.</div>;

  return (
    <div style={{ padding: "20px" }}>
      <h1>Analysis Result for Video: {result.video_id}</h1>
      <p>Match Score: {result.match_score}</p>
      <h3>Active Matches:</h3>
      <ul>
        {result.active_matches.map((match, index) => (
          <li key={index}>
            {match.crawled_video_id || match.uploaded_video_id}: Similarity {match.similarity}
          </li>
        ))}
      </ul>
      <p>Uploaded Frames: {result.uploaded_frames}</p>
      <p>Reference Frames: {result.reference_frames}</p>
    </div>
  );
}
