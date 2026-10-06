"use client";

import { createContext, useContext, useMemo, useState } from "react";

import { type ConsoleSessionInfo, connectConsole, setWrites } from "@/lib/console";

type Ctx = {
  session: ConsoleSessionInfo | null;
  busy: boolean;
  error: string | null;
  connect: (kind: string, host: string) => Promise<void>;
  disconnect: () => void;
  allowWrites: (on: boolean) => Promise<void>;
};

const ConsoleCtx = createContext<Ctx | null>(null);

export function ConsoleProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<ConsoleSessionInfo | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const value = useMemo<Ctx>(
    () => ({
      session,
      busy,
      error,
      connect: async (kind, host) => {
        setBusy(true);
        setError(null);
        try {
          setSession(await connectConsole(kind, host));
        } catch (e) {
          setError(e instanceof Error ? e.message : "Connection failed.");
        } finally {
          setBusy(false);
        }
      },
      disconnect: () => setSession(null),
      allowWrites: async (on) => {
        if (!session) return;
        const r = await setWrites(session.session, on);
        setSession({ ...session, write_enabled: r.write_enabled });
      },
    }),
    [session, busy, error],
  );
  return <ConsoleCtx.Provider value={value}>{children}</ConsoleCtx.Provider>;
}

export function useConsole(): Ctx {
  const c = useContext(ConsoleCtx);
  if (!c) throw new Error("useConsole outside ConsoleProvider");
  return c;
}
