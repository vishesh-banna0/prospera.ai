import { forwardRef } from "react";
import { cn } from "@/lib/cn";

/**
 * Text/number input styled to the tokens. Numeric inputs get the mono data face
 * and tabular figures so a typed amount lines up with the figures it becomes.
 */
export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
  mono?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, invalid, mono, type, ...props }, ref) => {
    const numeric = mono ?? type === "number";
    return (
      <input
        ref={ref}
        type={type}
        aria-invalid={invalid || undefined}
        className={cn(
          "h-9 w-full rounded border bg-panel-2 px-2.5 text-fg placeholder:text-fg-mute",
          "focus:border-fg-mute focus:outline-none",
          numeric ? "font-mono text-sm tnum" : "text-xs",
          invalid ? "border-down/60" : "border-line-2",
          className,
        )}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";

/** A field wrapper: label above, optional hint/error below. */
export function Field({
  label,
  hint,
  error,
  htmlFor,
  className,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  htmlFor?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={htmlFor} className="eyebrow">
        {label}
      </label>
      {children}
      {error ? (
        <p className="font-mono text-2xs text-down">{error}</p>
      ) : hint ? (
        <p className="text-2xs text-fg-mute">{hint}</p>
      ) : null}
    </div>
  );
}
