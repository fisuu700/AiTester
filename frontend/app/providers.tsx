"use client";

import Navbar from "@/components/Navbar";
import { AuthProvider } from "@/lib/auth";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <div className="min-h-full flex flex-col">
        <Navbar />
        <div className="flex-1">{children}</div>
      </div>
    </AuthProvider>
  );
}
