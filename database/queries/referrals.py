import asyncpg

# Совпадают со значениями по умолчанию в migrations/002_referrals.sql —
# используются только для отображения промо-текста "Вы получите X, друг получит Y"
REFERRER_BONUS_DEFAULT = 150000
REFERRED_BONUS_DEFAULT = 100000


async def get_referral_stats(pool: asyncpg.Pool, patient_id: int) -> asyncpg.Record:
    return await pool.fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE status = 'rewarded') AS rewarded_count,
            COUNT(*) FILTER (WHERE status = 'pending') AS pending_count,
            COALESCE(SUM(referrer_bonus) FILTER (WHERE status = 'rewarded'), 0) AS total_earned
        FROM referrals
        WHERE referrer_id = $1
        """,
        patient_id,
    )
