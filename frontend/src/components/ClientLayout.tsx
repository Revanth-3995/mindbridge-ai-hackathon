"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AuthProvider } from "@/context/AuthContext";

function Navbar() {
  const [authed, setAuthed] = useState(false);
  useEffect(() => {
    const update = () => {
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      setAuthed(Boolean(token));
    };
    update();
    window.addEventListener("storage", update);
    return () => window.removeEventListener("storage", update);
  }, []);

  const logout = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      window.location.href = "/login";
    }
  };

  return (
    <nav className="w-full border-b border-neutral-200 dark:border-neutral-800 bg-white/70 dark:bg-neutral-950/70 backdrop-blur">
      <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
        <Link href="/" className="text-sm font-semibold">MindBridge</Link>
        <div className="flex items-center gap-4 text-sm">
          {authed ? (
            <>
              <Link href="/dashboard" className="hover:underline">Dashboard</Link>
              <button onClick={logout} className="text-red-600 hover:underline">Logout</button>
            </>
          ) : (
            <>
              <Link href="/login" className="hover:underline">Login</Link>
              <Link href="/register" className="hover:underline">Register</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <Navbar />
      {children}
    </AuthProvider>
  );
}


