import { cn } from "@/lib/cn";

/**
 * A small generic data table. Columns declare their own cell renderer, so each
 * screen keeps its formatting explicit (readable) while sharing the chrome:
 * a scroll container, mono tabular body, hairline row rules. Numbers are
 * right-aligned by convention so decimal points line up down a column.
 */
export interface Column<T> {
  header: string;
  align?: "left" | "right";
  cell: (row: T) => React.ReactNode;
  /** Optional fixed width utility class, e.g. "w-32". */
  width?: string;
}

export function DataTable<T>({
  columns,
  rows,
  getRowKey,
  minWidth = "36rem",
  empty,
}: {
  columns: Column<T>[];
  rows: T[];
  getRowKey: (row: T, index: number) => string;
  minWidth?: string;
  empty?: React.ReactNode;
}) {
  if (rows.length === 0 && empty) return <>{empty}</>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-xs" style={{ minWidth }}>
        <thead>
          <tr className="border-b border-line">
            {columns.map((col, i) => (
              <th
                key={i}
                className={cn(
                  "px-3 py-2 font-mono text-[0.625rem] font-normal uppercase tracking-wider text-fg-mute",
                  col.align === "right" ? "text-right" : "text-left",
                  col.width,
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="font-mono tnum">
          {rows.map((row, r) => (
            <tr key={getRowKey(row, r)} className="border-b border-line last:border-0 hover:bg-panel-2/40">
              {columns.map((col, c) => (
                <td
                  key={c}
                  className={cn(
                    "px-3 py-2 text-fg",
                    col.align === "right" ? "text-right" : "text-left",
                  )}
                >
                  {col.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
