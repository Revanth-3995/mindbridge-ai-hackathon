"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import apiClient from "@/lib/apiClient";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await apiClient.post("/api/auth/login", { email, password });
      const token = data?.access_token;
      if (!token) throw new Error("Invalid login response");
      localStorage.setItem("access_token", token);
      router.push("/dashboard");
    } catch (e: any) {
      const msg = e?.response?.data?.error || e?.message || "Login failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-6 shadow-sm">
        <h1 className="text-xl font-semibold mb-4">Login</h1>
        {error && (
          <div className="mb-3 text-sm text-red-600" role="alert">{error}</div>
        )}
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium mb-1">Email</label>
            <input
              id="email"
              type="email"
              className="w-full rounded-md border border-neutral-300 dark:border-neutral-700 bg-transparent p-2 text-sm"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium mb-1">Password</label>
            <input
              id="password"
              type="password"
              className="w-full rounded-md border border-neutral-300 dark:border-neutral-700 bg-transparent p-2 text-sm"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full inline-flex items-center justify-center rounded-md px-3 py-2 text-sm bg-neutral-900 text-white hover:bg-neutral-800 disabled:opacity-60"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}


