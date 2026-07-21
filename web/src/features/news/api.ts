import { api } from "@/api/client";
import type {
  EventStatsView,
  EventsView,
  NewsArticlesView,
  NewsWarehouseStatsView,
} from "@/api/types";

/** News warehouse + structured events. Articles are already collected server-side;
 *  events are extracted from those articles on demand (POST /events/extract). */

export interface ArticleFilters {
  category?: string; // global | india | company | sector
  symbol?: string;
  query?: string;
  limit?: number;
}

export const newsApi = {
  warehouseStats: () => api.get<NewsWarehouseStatsView>("/api/v1/news/warehouse/stats"),

  articles: (f: ArticleFilters) => {
    const p = new URLSearchParams();
    if (f.category) p.set("category", f.category);
    if (f.symbol?.trim()) p.set("symbol", f.symbol.trim().toUpperCase());
    if (f.query?.trim()) p.set("query", f.query.trim());
    p.set("limit", String(f.limit ?? 30));
    return api.get<NewsArticlesView>(`/api/v1/news/articles?${p.toString()}`);
  },

  eventStats: () => api.get<EventStatsView>("/api/v1/events/stats"),
  events: (limit = 30) => api.get<EventsView>(`/api/v1/events?limit=${limit}`),
  // Body is required even though every field has a default; process the warehouse.
  extractEvents: () => api.post<unknown>("/api/v1/events/extract", { limit: 200 }),
};
