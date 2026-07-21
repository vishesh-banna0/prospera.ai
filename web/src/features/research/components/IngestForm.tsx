"use client";

import { useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input, Field } from "@/components/ui/Input";
import { ApiError } from "@/api/client";
import { useIngest } from "../hooks";

/** Add a document to the research index. It's parsed, chunked, embedded, and
 *  stored so it can be searched — all offline. */
export function IngestForm() {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [docType, setDocType] = useState("note");
  const [symbols, setSymbols] = useState("");
  const [done, setDone] = useState<string | null>(null);
  const ingest = useIngest();

  const valid = title.trim() !== "" && content.trim() !== "";

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!valid) return;
    setDone(null);
    ingest.mutate(
      {
        title: title.trim(),
        content: content.trim(),
        document_type: docType.trim() || "note",
        symbols: symbols
          .split(",")
          .map((s) => s.trim().toUpperCase())
          .filter(Boolean),
      },
      {
        onSuccess: (res) => {
          setDone(`Ingested “${res.title}” — ${res.chunk_count} chunks indexed.`);
          setTitle("");
          setContent("");
          setSymbols("");
        },
      },
    );
  }

  return (
    <Panel label="Add a document">
      <form onSubmit={submit} className="flex flex-col gap-3">
        <Field label="Title" htmlFor="ig-title">
          <Input id="ig-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Q3 earnings notes" />
        </Field>
        <Field label="Content" htmlFor="ig-content">
          <textarea
            id="ig-content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Paste the text to index…"
            className="min-h-[8rem] w-full rounded border border-line-2 bg-panel-2 px-2.5 py-2 text-xs leading-relaxed text-fg placeholder:text-fg-mute focus:border-fg-mute focus:outline-none"
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Type" htmlFor="ig-type" hint="e.g. note, filing, report">
            <Input id="ig-type" value={docType} onChange={(e) => setDocType(e.target.value)} />
          </Field>
          <Field label="Symbols" htmlFor="ig-symbols" hint="comma-separated">
            <Input
              id="ig-symbols"
              value={symbols}
              onChange={(e) => setSymbols(e.target.value.toUpperCase())}
              placeholder="AAPL, MSFT"
              className="font-mono uppercase"
            />
          </Field>
        </div>
        <Button type="submit" variant="primary" size="sm" loading={ingest.isPending} disabled={!valid}>
          Ingest document
        </Button>
      </form>

      {ingest.isError && (
        <p className="mt-2 break-words font-mono text-2xs text-down">{(ingest.error as ApiError).message}</p>
      )}
      {done && !ingest.isError && <p className="mt-2 font-mono text-2xs text-up">{done}</p>}
    </Panel>
  );
}
