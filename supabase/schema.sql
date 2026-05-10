-- TravelInDex — Supabase Schema
-- Run this in your Supabase SQL editor

create table if not exists places (
  id          bigint generated always as identity primary key,
  trip_id     text        not null,
  name        text        not null,
  city        text        default '',
  country     text        default '',
  type        text        default 'attraction',
  source_url  text        default '',
  device_id   text        not null,
  created_at  timestamptz default now()
);

-- Index for fast lookups by device + trip
create index if not exists idx_places_device_trip
  on places (device_id, trip_id);

-- Index for browsing all saves for a device
create index if not exists idx_places_device
  on places (device_id, created_at desc);

-- Future: when you add auth, you'll migrate device_id → user_id
-- alter table places add column user_id uuid references auth.users(id);
