"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ErrorState } from "@/components/ui/States";
import { ApiError } from "@/api/client";
import { useEnvironment, useRenameEnvironment, useDeleteEnvironment } from "../hooks";

const dateFmt = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

/** Title bar for the selected portfolio: name, opened-on, rename, delete. */
export function PortfolioHeader({
  id,
  fallbackName,
  onRenamed,
  onDeleted,
}: {
  id: string;
  fallbackName: string;
  onRenamed: (name: string) => void;
  onDeleted: () => void;
}) {
  const env = useEnvironment(id);
  const rename = useRenameEnvironment(id);
  const del = useDeleteEnvironment();

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(fallbackName);
  const [confirming, setConfirming] = useState(false);

  const name = env.data?.name ?? fallbackName;
  const missing = env.isError && (env.error as ApiError).status === 404;

  function saveName(e: React.FormEvent) {
    e.preventDefault();
    const next = draft.trim();
    if (!next || next === name) return setEditing(false);
    rename.mutate(next, {
      onSuccess: () => {
        onRenamed(next);
        setEditing(false);
      },
    });
  }

  if (missing) {
    return (
      <ErrorState
        detail="This portfolio no longer exists on the server. Remove it from your list."
        onRetry={onDeleted}
      />
    );
  }

  return (
    <div className="flex flex-wrap items-end justify-between gap-3 border-b border-line pb-4">
      <div className="min-w-0">
        <p className="eyebrow">Portfolio</p>
        {editing ? (
          <form onSubmit={saveName} className="mt-1 flex items-center gap-2">
            <Input
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="h-8 w-56"
              aria-label="Portfolio name"
            />
            <Button type="submit" size="sm" variant="primary" loading={rename.isPending}>
              Save
            </Button>
            <Button type="button" size="sm" variant="ghost" onClick={() => setEditing(false)}>
              Cancel
            </Button>
          </form>
        ) : (
          <h1 className="mt-1 truncate font-display text-xl font-bold text-fg">{name}</h1>
        )}
        <p className="mt-1 font-mono text-2xs text-fg-mute tnum">
          {env.data ? `opened ${dateFmt.format(new Date(env.data.created_at))}` : " "}
        </p>
      </div>

      {!editing && (
        <div className="flex items-center gap-2">
          {confirming ? (
            <>
              <span className="font-mono text-2xs text-fg-dim">Delete this portfolio?</span>
              <Button
                size="sm"
                variant="sell"
                loading={del.isPending}
                onClick={() =>
                  del.mutate(id, {
                    onSuccess: onDeleted,
                  })
                }
              >
                Delete
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setConfirming(false)}>
                Keep
              </Button>
            </>
          ) : (
            <>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setDraft(name);
                  setEditing(true);
                }}
              >
                Rename
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setConfirming(true)}>
                Delete
              </Button>
            </>
          )}
        </div>
      )}

      {rename.isError && (
        <p className="w-full font-mono text-2xs text-down">{(rename.error as ApiError).message}</p>
      )}
      {del.isError && (
        <p className="w-full font-mono text-2xs text-down">{(del.error as ApiError).message}</p>
      )}
    </div>
  );
}
