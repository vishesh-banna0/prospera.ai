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
    title: "Desk",
    items: [
      { label: "Portfolio", href: "/portfolio", ready: true },
      { label: "Markets", href: "/markets", ready: false },
    ],
  },
  {
    title: "Machine",
    items: [
      { label: "Intelligence", href: "/intelligence", ready: false },
      { label: "Backtest", href: "/backtest", ready: false },
    ],
  },
  {
    title: "Sources",
    items: [
      { label: "News", href: "/news", ready: false },
      { label: "Research", href: "/research", ready: false },
    ],
  },
  {
    title: "System",
    items: [{ label: "Styleguide", href: "/styleguide", ready: true }],
  },
];
