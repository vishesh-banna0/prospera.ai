import { api } from "@/api/client";
import type { AuthTokenView, UserView } from "@/api/types";

/** The three auth endpoints. Register and login both return a token + the user. */
export const authApi = {
  register: (username: string, password: string) =>
    api.post<AuthTokenView>("/api/v1/auth/register", { username, password }),

  login: (username: string, password: string) =>
    api.post<AuthTokenView>("/api/v1/auth/login", { username, password }),

  me: () => api.get<UserView>("/api/v1/auth/me"),
};
