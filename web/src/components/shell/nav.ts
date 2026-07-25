/**
 * Left-rail navigation. `ready` flips to a real link as each screen is built
 * (build order in the frontend prompt §6). Until then the item shows "soon"
 * rather than routing to a 404 — honest about what exists.
 */
export interface NavItem {
  label: string;
  href: string;
  ready: boolean;
}

export interface NavSection {
  title: string;
  items: NavItem[];
}

export const NAV: NavSection[] = [
  {
    title: "Dashboard",
    items: [
      { label: "Dashboard", href: "/", ready: true },
      { label: "Portfolio", href: "/portfolio", ready: true },
      { label: "Markets", href: "/markets", ready: true },
    ],
  },
  {
    title: "Machine",
    items: [
      { label: "Intelligence", href: "/intelligence", ready: true },
      { label: "Advisor", href: "/advisor", ready: true },
      { label: "Backtest", href: "/backtest", ready: true },
    ],
  },
  {
    title: "Sources",
    items: [
      { label: "News", href: "/news", ready: true },
      { label: "Research", href: "/research", ready: true },
    ],
  },
  {
    title: "System",
    items: [{ label: "Styleguide", href: "/styleguide", ready: true }],
  },
];
