"use client";

import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/States";
import { IconGaugeEmpty } from "@/components/ui/icons";
import { useAnalyze } from "../useAnalyze";
import { StageCard } from "./StageCard";
import { CompanyScoreContent } from "./CompanyScoreContent";
import { PredictionContent } from "./PredictionContent";
import { SignalContent } from "./SignalContent";
import { ReasoningContent } from "./ReasoningContent";

/**
 * The signature. Pressing Analyze runs the four-stage pipeline as one
 * choreographed reveal — each stage lands as it resolves and visibly feeds the
 * next. It's the only place the app spends real motion.
 */
export function AnalyzeChain({ symbol }: { symbol: string }) {
  const { state, running, started, run } = useAnalyze(symbol);

  if (!started) {
    return (
      <EmptyState
        icon={<IconGaugeEmpty />}
        title="Not analyzed yet"
        action={
          <Button variant="primary" size="lg" onClick={run}>
            Analyze {symbol}
          </Button>
        }
      >
        The machine hasn&rsquo;t formed an opinion on {symbol}. Running Analyze
        computes four stages in order — company score, price prediction, a fused
        Buy/Hold/Sell, and a written rationale — each feeding the next.
      </EmptyState>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <p className="eyebrow">Reasoning chain</p>
        <Button variant="secondary" size="sm" onClick={run} loading={running}>
          {running ? "Analyzing" : "Re-analyze"}
        </Button>
      </div>

      <div>
        <StageCard
          index="01"
          title="Company score"
          feeds="prediction"
          status={state.company.status}
          error={state.company.error}
        >
          {state.company.data && <CompanyScoreContent data={state.company.data} />}
        </StageCard>

        <StageCard
          index="02"
          title="Prediction"
          feeds="signal"
          status={state.prediction.status}
          error={state.prediction.error}
        >
          {state.prediction.data && <PredictionContent data={state.prediction.data} />}
        </StageCard>

        <StageCard
          index="03"
          title="Fused signal"
          feeds="reasoning"
          status={state.signal.status}
          error={state.signal.error}
        >
          {state.signal.data && <SignalContent data={state.signal.data} />}
        </StageCard>

        <StageCard
          index="04"
          title="Reasoning"
          status={state.reasoning.status}
          error={state.reasoning.error}
          isLast
        >
          {state.reasoning.data && <ReasoningContent data={state.reasoning.data} />}
        </StageCard>
      </div>
    </div>
  );
}
