"use client";

import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { getSupabase } from "./supabase";

/** The current Supabase session, kept in sync with sign-in, sign-out, and token refreshes. */
export function useSession(): { session: Session | null; loading: boolean } {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) {
      setLoading(false);
      return;
    }
    // getSession waits for the OAuth ?code= exchange when returning from Google.
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
      const url = new URL(window.location.href);
      if (url.searchParams.has("code")) {
        url.searchParams.delete("code");
        window.history.replaceState(null, "", url.pathname + url.search + url.hash);
      }
    });
    const { data } = supabase.auth.onAuthStateChange((_event, next) => setSession(next));
    return () => data.subscription.unsubscribe();
  }, []);

  return { session, loading };
}
