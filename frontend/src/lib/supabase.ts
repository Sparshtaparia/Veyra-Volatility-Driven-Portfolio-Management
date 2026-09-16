import { createClient } from "@supabase/supabase-js"

const url = import.meta.env.VITE_SUPABASE_URL
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!url) throw new Error("VITE_SUPABASE_URL is required")
if (!anonKey) throw new Error("VITE_SUPABASE_ANON_KEY is required")

export const isSupabaseConfigured = true
export const supabase = createClient(url, anonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
})
