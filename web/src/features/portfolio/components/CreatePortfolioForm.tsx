"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/api/client";
import { useCreateEnvironment } from "../hooks";
import type { PortfolioRef } from "../registry";

/** Create a new paper-trading portfolio. On success the caller records it in the
 *  local registry and selects it. */
export function CreatePortfolioForm({
  onCreated,
  autoFocus,
}: {
  onCreated: (ref: PortfolioRef) => void;
  autoFocus?: boolean;
}) {
  const [name, setName] = useState("");
  const create = useCreateEnvironment();

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    create.mutate(trimmed, {
      onSuccess: (env) => {
        onCreated({ id: env.environment_id, name: env.name });
        setName("");
      },
    });
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <Input
          autoFocus={autoFocus}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Long-term bets"
          aria-label="New portfolio name"
          className="h-9 w-56"
        />
        <Button type="submit" variant="primary" size="md" loading={create.isPending} disabled={!name.trim()}>
          Create portfolio
        </Button>
      </div>
      {create.isError && (
        <p className="font-mono text-2xs text-down">{(create.error as ApiError).message}</p>
      )}
    </form>
  );
}
