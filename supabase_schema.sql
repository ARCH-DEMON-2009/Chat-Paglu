create extension if not exists pgcrypto;

create table if not exists users (
  user_id text primary key,
  name text,
  nickname text,
  preferences jsonb default '[]'::jsonb,
  interests jsonb default '[]'::jsonb,
  facts jsonb default '[]'::jsonb,
  interaction_count integer default 0,
  last_seen timestamptz default now(),
  relationship text default 'group_member',
  mode text default 'normal'
);

create table if not exists memories (
  id bigserial primary key,
  user_id text not null,
  key text,
  value text,
  created_at timestamptz default now(),
  source text default 'user'
);

create table if not exists group_context (
  id bigserial primary key,
  chat_id text,
  user_id text,
  user_name text,
  text text,
  reply_to text,
  created_at timestamptz default now()
);

create table if not exists messages (
  id bigserial primary key,
  chat_id text,
  user_id text,
  user_name text,
  text text,
  message_type text,
  created_at timestamptz default now()
);

create table if not exists character_state (
  key text primary key,
  value text
);

create table if not exists bot_settings (
  key text primary key,
  value text
);

create index if not exists idx_memories_user_id on memories (user_id);
create index if not exists idx_group_context_chat_id on group_context (chat_id);
create index if not exists idx_messages_chat_id on messages (chat_id);
