create table if not exists public.account_plans (
    user_id uuid primary key references auth.users (id) on delete cascade,
    plan text not null default 'FREE' check (plan in ('FREE', 'PRO', 'ENTERPRISE')),
    billing_email text,
    stripe_customer_id text,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create or replace function public.touch_account_plans_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = timezone('utc', now());
    return new;
end;
$$;

drop trigger if exists trg_account_plans_updated_at on public.account_plans;
create trigger trg_account_plans_updated_at
before update on public.account_plans
for each row execute function public.touch_account_plans_updated_at();

alter table public.account_plans enable row level security;

create policy if not exists "users can read their own plan"
on public.account_plans
for select
using (auth.uid() = user_id);
