import { getSupabase } from "./supabase";

/** Start Google sign-in; the browser leaves for Google and returns to /chat. */
export async function signInWithGoogle(): Promise<string | null> {
  const supabase = getSupabase();
  if (!supabase) return "Sign-in isn't configured.";
  const { error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: `${window.location.origin}/chat`, queryParams: { prompt: "select_account" } },
  });
  return error ? error.message : null;
}
