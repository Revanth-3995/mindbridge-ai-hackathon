"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    if (!token) {
      // Smooth redirect animation: small delay for UX
      const id = setTimeout(() => router.replace("/login"), 200);
      return () => clearTimeout(id);
    }
    setChecking(false);
  }, [router]);

  if (checking) {
    return (
      <div className="flex items-center justify-center py-16" aria-busy>
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-900" aria-label="Loading" />
      </div>
    );
  }

  return <>{children}</>;
}


