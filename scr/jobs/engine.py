"""Логика работ без зависимостей от ВК и базы данных (поэтому легко тестируется)."""
import math
import random
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from .catalog import Job

# Сколько работ показывается на одной странице
PAGE_SIZE = 6

# Шанс получить премию после успешной смены и во сколько раз она увеличивает оплату
BONUS_CHANCE = 0.07
BONUS_MULTIPLIER = 1.5

# Значения payload, которые заняты навигацией и не могут быть ключами работ
RESERVED_CHOICES = frozenset({'back', 'prev_page', 'next_page', 'refresh'})

DEFAULT_FAIL_TEXT = 'Смена не задалась, и платить вам не стали.'


@dataclass(frozen=True)
class ShiftResult:
    kind: str  # 'success' | 'bonus' | 'fail'
    amount: int  # > 0 - заработок, < 0 - штраф, 0 - ничего
    text: str


def roll_shift(job: Job, rng=random) -> ShiftResult:
    """Разыгрывает результат одной смены. rng - модуль random или random.Random (для тестов)."""
    if job.fail_chance and rng.random() < job.fail_chance:
        fine = rng.randint(*job.fine) if job.fine[1] > 0 else 0
        text = rng.choice(job.fail_texts) if job.fail_texts else DEFAULT_FAIL_TEXT
        return ShiftResult('fail', -fine, text)

    pay = rng.randint(job.min_pay, job.max_pay)
    text = rng.choice(job.success_texts)
    if rng.random() < BONUS_CHANCE:
        return ShiftResult('bonus', int(pay * BONUS_MULTIPLIER), text)
    return ShiftResult('success', pay, text)


def cap_fine(result: ShiftResult, balance: int) -> ShiftResult:
    """Штраф не может увести баланс в минус."""
    if result.amount >= 0:
        return result
    return replace(result, amount=-min(-result.amount, max(balance, 0)))


# --- Время и перерывы ---

def utcnow() -> datetime:
    """Текущее время UTC без tzinfo (так время хранится в базе)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def seconds_left(available_at: datetime, now: datetime) -> int:
    """Сколько секунд осталось до available_at (округление вверх, не меньше 0)."""
    available_at = available_at.replace(tzinfo=None)
    return max(0, math.ceil((available_at - now).total_seconds()))


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f'{seconds} сек'
    if seconds < 3600:
        minutes, sec = divmod(seconds, 60)
        return f'{minutes} мин {sec} сек' if sec else f'{minutes} мин'
    hours, rest = divmod(seconds, 3600)
    minutes = rest // 60
    return f'{hours} ч {minutes} мин' if minutes else f'{hours} ч'


def format_money(amount: int) -> str:
    return f'${amount:,}'.replace(',', ' ')


# --- Страницы ---

def paginate(
        jobs: Sequence[Job],
        page: int,
        page_size: int = PAGE_SIZE
) -> tuple[Sequence[Job], int, int]:
    """Возвращает (работы страницы, номер страницы с поправкой на границы, всего страниц)."""
    total_pages = max(1, math.ceil(len(jobs) / page_size))
    page = min(max(page, 0), total_pages - 1)
    start = page * page_size
    return jobs[start:start + page_size], page, total_pages


# --- Тексты сообщений ---

def format_jobs_page(
        page_jobs: Sequence[Job],
        remaining: dict[str, int],
        page: int,
        total_pages: int
) -> str:
    lines = [
        f'🔨 Работа | Страница {page + 1} из {total_pages}',
        'Чем выше оплата, тем дольше перерыв между сменами.',
        '',
    ]
    for job in page_jobs:
        left = remaining.get(job.key, 0)
        status = f'⏳ через {format_duration(left)}' if left > 0 else '✅ можно работать'
        risk = ' · ⚠ риск' if job.fail_chance else ''
        lines.append(f'{job.emoji} {job.title} - {job.description}')
        lines.append(
            f'💵 {format_money(job.min_pay)}-{format_money(job.max_pay)} · '
            f'⏱ {format_duration(job.cooldown)}{risk}'
        )
        lines.append(status)
        lines.append('')
    lines.append('Выберите работу с помощью кнопок 👇')
    return '\n'.join(lines)


def format_shift_message(job: Job, result: ShiftResult, balance: int) -> str:
    lines = [f'{job.emoji} {job.title} - смена завершена!', '', result.text]
    if result.kind == 'bonus':
        lines.append('🎉 Вам повезло - начальник выписал премию!')
    lines.append('')

    if result.amount > 0:
        lines.append(f'💵 Заработано: {format_money(result.amount)}')
    elif result.amount < 0:
        lines.append(f'💸 Потеряно: {format_money(-result.amount)}')
    else:
        lines.append('😕 За эту смену ничего не заработано')

    lines.append(f'💳 Баланс: {format_money(balance)}')
    lines.append(f'⏳ Следующая смена через {format_duration(job.cooldown)}')
    return '\n'.join(lines)
