"use client";

import React, { useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://web-talker-2.onrender.com";

export default function Home() {
  const [url, setUrl] = useState("");
  const [collection, setCollection] = useState<string>("");
  const [processing, setProcessing] = useState(false);
  const [chunks, setChunks] = useState<number | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [k, setK] = useState<number>(5);
  const [answer, setAnswer] = useState<string | null>(null);
  const [queryLoading, setQueryLoading] = useState(false);

  const [collections, setCollections] = useState<string[] | null>(null);
  const [collectionsLoading, setCollectionsLoading] = useState(false);

  async function submitUrl(e: React.FormEvent) {
    e.preventDefault();
    setProcessing(true);
    setStatusMsg(null);
    setChunks(null);

    try {
      const res = await fetch(`${API_BASE}/rag/url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, collection_name: collection }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));

      setStatusMsg("URL processed successfully");
      setChunks(data.chunks ?? null);
    } catch (err: unknown) {
      setStatusMsg(`Error: ${err instanceof Error ? err : "error"}`);
    } finally {
      setProcessing(false);
    }
  }

  async function runQuery(e: React.FormEvent) {
    e.preventDefault();
    setAnswer(null);
    setQueryLoading(true);

    try {
      const res = await fetch(`${API_BASE}/rag/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, collection_name: collection, k }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
      setAnswer(data.answer ?? "(no answer)");
    } catch (err: unknown) {
      setAnswer(`Error: ${err instanceof Error ? err : "error"}`);
    } finally {
      setQueryLoading(false);
    }
  }

  async function loadCollections() {
    setCollectionsLoading(true);
    setCollections(null);
    try {
      const res = await fetch(`${API_BASE}/rag/collections`);
      const data = await res.json();
      if (!res.ok) throw new Error(JSON.stringify(data));
      setCollections(data.collections || []);
    } catch (err: unknown) {
      setCollections([
        `Error: ${err instanceof Error ? "NO collection" : "error"}`,
      ]);
    } finally {
      setCollectionsLoading(false);
    }
  }

  async function deleteCollection(name: string) {
    if (!confirm(`Are you sure you want to delete collection "${name}"?`))
      return;
    try {
      const res = await fetch(
        `${API_BASE}/rag/collections/${encodeURIComponent(name)}`,
        {
          method: "DELETE",
        }
      );

      console.log(res);
      const data = await res.json();
      console.log(data);
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
      alert(data.message || `Collection "${name}" deleted`);
      // Refresh collections list
      loadCollections();
    } catch (err: unknown) {
      alert(`Error deleting: ${err instanceof Error ? err : "error"}`);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-4xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-semibold">Web Talker</h1>
          <p className="text-sm text-slate-600 mt-1">
            Talk to Your WebURl — ingest URLs, run queries, manage collections.
          </p>
        </header>

        <section className="grid gap-6 md:grid-cols-2">
          <form
            onSubmit={submitUrl}
            className="p-4 bg-white rounded-2xl shadow-sm"
          >
            <h2 className="font-medium mb-3">Ingest URL</h2>
            <label className="block text-sm text-slate-600">URL</label>
            <input
              className="w-full mt-1 p-2 rounded-md border"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/article"
              required
            />

            <label className="block text-sm text-slate-600 mt-3">
              Collection name
            </label>
            <input
              className="w-full mt-1 p-2 rounded-md border"
              value={collection}
              onChange={(e) => setCollection(e.target.value)}
            />

            <div className="flex items-center gap-3 mt-4">
              <button
                className={`px-4 py-2 rounded-xl shadow-sm text-white ${
                  processing
                    ? "bg-slate-400"
                    : "bg-indigo-600 hover:bg-indigo-700"
                }`}
                type="submit"
                disabled={processing}
              >
                {processing ? "Processing..." : "Ingest URL"}
              </button>

              {chunks !== null && (
                <span className="text-sm text-slate-600">Chunks: {chunks}</span>
              )}
            </div>

            {statusMsg && <p className="mt-3 text-sm">{statusMsg}</p>}
          </form>

          <div className="p-4 bg-white rounded-2xl shadow-sm">
            <h2 className="font-medium mb-3">Collections</h2>
            <div className="flex gap-2">
              <button
                onClick={loadCollections}
                className={`px-3 py-2 rounded-md ${
                  collectionsLoading
                    ? "bg-slate-300"
                    : "bg-emerald-500 hover:bg-emerald-600"
                } text-white`}
                disabled={collectionsLoading}
              >
                {collectionsLoading ? "Loading..." : "Refresh"}
              </button>
            </div>

            <div className="mt-4">
              {collections === null ? (
                <p className="text-sm text-slate-500">
                  No data yet. Click Refresh to load collections.
                </p>
              ) : (
                <ul className="space-y-2 text-sm">
                  {collections.map((c, i) => (
                    <li
                      key={i}
                      className="rounded-md p-2 border flex justify-between items-center"
                    >
                      <span>{c}</span>
                      <button
                        onClick={() => deleteCollection(c)}
                        className="px-2 py-1 rounded bg-red-500 text-white hover:bg-red-600 text-xs"
                      >
                        Delete
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </section>

        <section className="mt-8 grid gap-6 md:grid-cols-2">
          <form
            onSubmit={runQuery}
            className="p-4 bg-white rounded-2xl shadow-sm"
          >
            <h2 className="font-medium mb-3">Ask the RAG</h2>

            <label className="block text-sm text-slate-600">Collection</label>
            <input
              className="w-full mt-1 p-2 rounded-md border"
              value={collection}
              onChange={(e) => setCollection(e.target.value)}
            />

            <label className="block text-sm text-slate-600 mt-3">Query</label>
            <textarea
              className="w-full mt-1 p-2 rounded-md border"
              rows={4}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask something based only on the ingested URL(s)."
              required
            />

            <div className="flex items-center gap-3 mt-3">
              <label className="text-sm">k</label>
              <input
                type="number"
                min={1}
                max={20}
                value={k}
                onChange={(e) => setK(Number(e.target.value))}
                className="w-20 p-2 rounded-md border"
              />

              <button
                type="submit"
                disabled={queryLoading}
                className={`ml-auto px-4 py-2 rounded-xl text-white ${
                  queryLoading
                    ? "bg-slate-400"
                    : "bg-indigo-600 hover:bg-indigo-700"
                }`}
              >
                {queryLoading ? "Thinking..." : "Run Query"}
              </button>
            </div>
          </form>

          <div className="p-4 bg-white rounded-2xl shadow-sm">
            <h2 className="font-medium mb-3">Answer</h2>
            <div className="min-h-[120px] p-3 rounded-md border bg-slate-50">
              {answer === null ? (
                <p className="text-sm text-slate-500">
                  No answer yet — run a query to see the RAG response.
                </p>
              ) : (
                <pre className="whitespace-pre-wrap text-sm">{answer}</pre>
              )}
            </div>
            <div className="mt-4 text-xs text-slate-500">
              Note: Backend uses Gemini/OpenAI client to generate the final
              answer from retrieved context.
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
