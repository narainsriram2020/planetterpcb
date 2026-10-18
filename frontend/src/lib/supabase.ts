import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

let client: SupabaseClient | null = null;

/** Whether accounts are enabled (both public Supabase settings are present). */
export const accountsEnabled = Boolean(SUPABASE_URL && SUPABASE_KEY);

/** Browser Supabase client, or null when accounts aren't configured (local dev). */
export function getSupabase(): SupabaseClient | null {
  if (!accountsEnabled) return null;
  if (!client) {
    client = createClient(SUPABASE_URL!, SUPABASE_KEY!, {
      // PKCE keeps tokens out of the redirect URL; the ?code= is exchanged on load.
      auth: { flowType: "pkce", persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
    });
  }
  return client;
}
