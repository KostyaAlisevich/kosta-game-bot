from datetime import timedelta

from tortoise.exceptions import IntegrityError

from .catalog import Job
from .engine import seconds_left, utcnow
from .models import JobCooldown


async def get_remaining_cooldowns(user_pk: int) -> dict[str, int]:
    """{ключ работы: сколько секунд осталось до следующей смены}, только для работ на перерыве."""
    now = utcnow()
    remaining = {}
    for cooldown in await JobCooldown.filter(user_id=user_pk):
        left = seconds_left(cooldown.available_at, now)
        if left > 0:
            remaining[cooldown.job_key] = left
    return remaining


async def claim_shift(user_pk: int, job: Job) -> int:
    """Пытается начать смену. Возвращает 0, если смена начата, иначе - сколько секунд ждать.

    Перерыв занимается одним атомарным UPDATE ... WHERE available_at <= now,
    поэтому быстрые повторные нажатия не принесут двойную оплату.
    """
    now = utcnow()
    next_available = now + timedelta(seconds=job.cooldown)

    claimed = await JobCooldown.filter(
        user_id=user_pk,
        job_key=job.key,
        available_at__lte=now,
    ).update(available_at=next_available)
    if claimed:
        return 0

    cooldown = await JobCooldown.get_or_none(user_id=user_pk, job_key=job.key)
    if cooldown is None:
        # Пользователь ещё ни разу не работал в этой профессии
        try:
            await JobCooldown.create(user_id=user_pk, job_key=job.key, available_at=next_available)
        except IntegrityError:
            # Параллельный запрос успел создать запись раньше нас
            cooldown = await JobCooldown.get_or_none(user_id=user_pk, job_key=job.key)
        else:
            return 0

    if cooldown is None:
        return 1
    return max(1, seconds_left(cooldown.available_at, now))
