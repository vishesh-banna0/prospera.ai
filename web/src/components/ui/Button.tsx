import { forwardRef } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

/**
 * Chrome carries no data color, so the primary action is high-contrast (light on
 * ink), not a colored brand button. `buy`/`sell` variants are the ONE exception —
 * a trade action legitimately speaks in the market's direction colors.
 */
const button = cva(
  "inline-flex items-center justify-center gap-2 rounded border font-medium transition-colors disabled:pointer-events-none disabled:opacity-45",
  {
    variants: {
      variant: {
        primary: "border-fg bg-fg text-ink hover:bg-fg/90",
        secondary: "border-line-2 bg-panel-2 text-fg hover:border-fg-mute",
        ghost: "border-transparent bg-transparent text-fg-dim hover:bg-panel-2 hover:text-fg",
        buy: "border-up/50 bg-up/10 text-up hover:bg-up/20",
        sell: "border-down/50 bg-down/10 text-down hover:bg-down/20",
      },
      size: {
        sm: "h-7 px-2.5 text-2xs",
        md: "h-9 px-3.5 text-xs",
        lg: "h-11 px-5 text-sm",
      },
    },
    defaultVariants: { variant: "secondary", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof button> {
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, disabled, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(button({ variant, size }), className)}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        {...props}
      >
        {loading && <Spinner />}
        {children}
      </button>
    );
  },
);
Button.displayName = "Button";

function Spinner() {
  return (
    <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.25" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}
