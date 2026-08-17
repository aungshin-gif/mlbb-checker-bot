import os
from typing import Any
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "")

class Database:
    def __init__(self) -> None:
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is required")
        self.pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5, command_timeout=20)

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()

    async def ensure_user(self, telegram_id: int, username: str | None, first_name: str | None) -> None:
        assert self.pool
        await self.pool.execute(
            """insert into users (telegram_id, username, first_name) values ($1, $2, $3)
            on conflict (telegram_id) do update set username=$2, first_name=$3, updated_at=now()""",
            telegram_id, username, first_name,
        )

    async def balance(self, telegram_id: int) -> int:
        assert self.pool
        value = await self.pool.fetchval("select balance_mmk from users where telegram_id=$1", telegram_id)
        return int(value or 0)

    async def create_recharge(self, telegram_id: int, amount_mmk: int, receipt_file_id: str) -> str:
        assert self.pool
        request_id = await self.pool.fetchval(
            "insert into recharge_requests (telegram_id, amount_mmk, receipt_file_id) values ($1,$2,$3) returning id",
            telegram_id, amount_mmk, receipt_file_id,
        )
        return str(request_id)

    async def approve_recharge(self, request_id: str, reviewer_id: int) -> dict[str, Any] | None:
        assert self.pool
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow("select * from recharge_requests where id=$1 and status='PENDING' for update", request_id)
                if not row:
                    return None
                new_balance = await conn.fetchval("update users set balance_mmk=balance_mmk+$1, updated_at=now() where telegram_id=$2 returning balance_mmk", row["amount_mmk"], row["telegram_id"])
                await conn.execute("update recharge_requests set status='APPROVED', reviewed_by=$1, reviewed_at=now() where id=$2", reviewer_id, request_id)
                await conn.execute("insert into wallet_transactions (telegram_id, transaction_type, amount_mmk, balance_after_mmk, reference_id, note) values ($1,'recharge',$2,$3,$4,'KBZPay recharge approved')", row["telegram_id"], row["amount_mmk"], new_balance, request_id)
                return {"telegram_id": row["telegram_id"], "amount_mmk": row["amount_mmk"], "balance_mmk": new_balance}

    async def reject_recharge(self, request_id: str, reviewer_id: int) -> bool:
        assert self.pool
        result = await self.pool.execute("update recharge_requests set status='REJECTED', reviewed_by=$1, reviewed_at=now() where id=$2 and status='PENDING'", reviewer_id, request_id)
        return result.endswith("1")

    async def debit_for_order(self, telegram_id: int, amount_mmk: int, reference_id: str) -> bool:
        assert self.pool
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                balance = await conn.fetchval("select balance_mmk from users where telegram_id=$1 for update", telegram_id)
                if int(balance or 0) < amount_mmk:
                    return False
                new_balance = int(balance) - amount_mmk
                await conn.execute("update users set balance_mmk=$1, updated_at=now() where telegram_id=$2", new_balance, telegram_id)
                await conn.execute("insert into wallet_transactions (telegram_id, transaction_type, amount_mmk, balance_after_mmk, reference_id, note) values ($1,'order_debit',$2,$3,$4,'G2Bulk order')", telegram_id, -amount_mmk, new_balance, reference_id)
                return True

    async def create_order(self, telegram_id: int, g2bulk_order_id: str, game_code: str, game_name: str, catalogue_name: str, player_id: str, supplier_price_usd: float, rate: float, markup: float, customer_price_mmk: int, status: str) -> None:
        assert self.pool
        await self.pool.execute("insert into orders (telegram_id,g2bulk_order_id,game_code,game_name,catalogue_name,player_id,supplier_price_usd,usd_to_mmk_rate,markup_percent,customer_price_mmk,status) values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)", telegram_id, g2bulk_order_id, game_code, game_name, catalogue_name, player_id, supplier_price_usd, rate, markup, customer_price_mmk, status)
