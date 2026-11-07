from tortoise.expressions import F
from vkbottle.bot import Message
from vkbottle.framework.labeler import BotLabeler
from vkbottle.modules import json

from core.loader import bot
from menu.handlers import show_income_menu
from users.models import UserModel
from users.utils import get_user_balance
from .catalog import JOBS, JOBS_BY_KEY, Job
from .engine import (
    cap_fine,
    format_duration,
    format_jobs_page,
    format_shift_message,
    paginate,
    roll_shift,
)
from .keyboards import build_jobs_keyboard
from .service import claim_shift, get_remaining_cooldowns
from .states import JobsState

bl = BotLabeler()


def get_page_keyboard(page: int):
    page_jobs, page, total_pages = paginate(JOBS, page)
    return build_jobs_keyboard(page_jobs, page, total_pages)


async def show_jobs_page(message: Message, page: int = 0):
    user = await UserModel.get(vk_id=message.from_id)
    remaining = await get_remaining_cooldowns(user.pk)

    page_jobs, page, total_pages = paginate(JOBS, page)
    await message.answer(
        format_jobs_page(page_jobs, remaining, page, total_pages),
        keyboard=build_jobs_keyboard(page_jobs, page, total_pages)
    )
    await bot.state_dispenser.set(message.from_id, JobsState.CHOOSE_JOB, page=page)


@bl.private_message(payload={'income_menu': 'work'})
async def open_jobs_menu(message: Message):
    await show_jobs_page(message, page=0)


@bl.private_message(state=JobsState.CHOOSE_JOB)
async def choose_job(message: Message):
    page = message.state_peer.payload['page']

    choice = None
    if message.payload:
        payload = json.loads(message.payload)
        if isinstance(payload, dict):
            choice = payload.get('choice')

    if choice == 'back':
        await bot.state_dispenser.delete(message.from_id)
        return await show_income_menu(message)
    if choice == 'refresh':
        return await show_jobs_page(message, page)
    if choice == 'prev_page':
        return await show_jobs_page(message, page - 1)
    if choice == 'next_page':
        return await show_jobs_page(message, page + 1)

    job = JOBS_BY_KEY.get(choice) if isinstance(choice, str) else None
    if job is None:
        return await message.answer(
            '❗ Некорректный ввод! Выберите работу с помощью кнопок',
            keyboard=get_page_keyboard(page)
        )

    await work_shift(message, job, page)


async def work_shift(message: Message, job: Job, page: int):
    user = await UserModel.get(vk_id=message.from_id)
    keyboard = get_page_keyboard(page)

    seconds_to_wait = await claim_shift(user.pk, job)
    if seconds_to_wait > 0:
        return await message.answer(
            f'⏳ {job.emoji} {job.title}: вы ещё отдыхаете после прошлой смены.\n'
            f'Следующая смена через {format_duration(seconds_to_wait)}.',
            keyboard=keyboard
        )

    result = cap_fine(roll_shift(job), user.balance)
    if result.amount:
        await UserModel.filter(pk=user.pk).update(balance=F('balance') + result.amount)

    balance = await get_user_balance(message.from_id)
    await message.answer(
        format_shift_message(job, result, balance),
        keyboard=keyboard
    )
