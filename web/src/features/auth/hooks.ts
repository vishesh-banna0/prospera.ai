"use client";

import { useMutation } from "@tanstack/react-query";
import { authApi } from "./api";
import { useAuth } from "./AuthProvider";

interface Credentials {
  username: string;
  password: string;
}

/** Log in, then record the token + username so the app unlocks. */
export function useLogin() {
  const { signIn } = useAuth();
  return useMutation({
    mutationFn: (vars: Credentials) => authApi.login(vars.username, vars.password),
    onSuccess: (data) => signIn(data.token, data.user.username),
  });
}

/** Create an account, then sign in with the returned token. */
export function useRegister() {
  const { signIn } = useAuth();
  return useMutation({
    mutationFn: (vars: Credentials) => authApi.register(vars.username, vars.password),
    onSuccess: (data) => signIn(data.token, data.user.username),
  });
}
