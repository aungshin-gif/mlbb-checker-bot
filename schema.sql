create table if not exists users (
  telegram_id bigint primary key,
  username text,
  first_name text,
  balance_mmk bigint not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists wallet_transactions (
  id bigserial primary key,
  telegram_id bigint not null references users(telegram_id),
  transaction_type text not null check (transaction_type in ('recharge', 'order_debit', 'refund', 'adjustment')),
  amount_mmk bigint not null,
  balance_after_mmk bigint not null,
  reference_id text,
  note text,
  created_at timestamptz not null default now()
);

create table if not exists recharge_requests (
  id uuid primary key default gen_random_uuid(),
  telegram_id bigint not null references users(telegram_id),
  amount_mmk bigint not null check (amount_mmk >= 1000),
  receipt_file_id text,
  status text not null default 'PENDING' check (status in ('PENDING', 'APPROVED', 'REJECTED')),
  reviewed_by bigint,
  created_at timestamptz not null default now(),
  reviewed_at timestamptz
);

create table if not exists orders (
  id bigserial primary key,
  telegram_id bigint not null references users(telegram_id),
  g2bulk_order_id text,
  game_code text not null,
  game_name text not null,
  catalogue_name text not null,
  player_id text not null,
  supplier_price_usd numeric(12,4),
  usd_to_mmk_rate numeric(12,2) not null,
  markup_percent numeric(6,2) not null,
  customer_price_mmk bigint not null,
  status text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_recharge_status on recharge_requests(status);
create index if not exists idx_orders_telegram_id on orders(telegram_id);
create index if not exists idx_transactions_telegram_id on wallet_transactions(telegram_id);
