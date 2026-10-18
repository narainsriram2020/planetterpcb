-- TerpGuide saved chats (run once in the Supabase SQL Editor).
-- Users can read, rename, and delete their own chats; only the backend (secret
-- key) writes messages, so saved answers are exactly what TerpGuide said.

create table public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.messages (
  id bigint generated always as identity primary key,
  conversation_id uuid not null references public.conversations (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  role text not null check (role in ('user', 'bot')),
  text text not null,
  steps jsonb not null default '[]'::jsonb,
  cards jsonb not null default '[]'::jsonb,
  status text not null default 'done' check (status in ('done', 'error')),
  created_at timestamptz not null default now()
);

create index conversations_user_updated_idx on public.conversations (user_id, updated_at desc);
create index messages_conversation_idx on public.messages (conversation_id, id);

alter table public.conversations enable row level security;
alter table public.messages enable row level security;

create policy "read own conversations" on public.conversations
  for select to authenticated using ((select auth.uid()) = user_id);
create policy "rename own conversations" on public.conversations
  for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "delete own conversations" on public.conversations
  for delete to authenticated using ((select auth.uid()) = user_id);
create policy "read own messages" on public.messages
  for select to authenticated using ((select auth.uid()) = user_id);

grant select, delete on public.conversations to authenticated;
grant update (title) on public.conversations to authenticated;
grant select on public.messages to authenticated;
grant select, insert, update, delete on public.conversations, public.messages to service_role;
grant usage, select on all sequences in schema public to service_role;

-- Keep a conversation's updated_at current so the sidebar sorts by latest activity.
create function public.touch_conversation() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  update public.conversations set updated_at = now() where id = new.conversation_id;
  return new;
end $$;

create trigger messages_touch_conversation
  after insert on public.messages
  for each row execute function public.touch_conversation();
