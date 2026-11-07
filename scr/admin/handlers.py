import json
import random
from datetime import datetime

from vkbottle import Keyboard, VKAPIError
from vkbottle.bot import Message
from vkbottle.framework.labeler import BotLabeler

from core.settings import ADMIN_GRADES, USER_STATUSES
from core.loader import admin_list, bot
from menu.utils import generate_choice_keyboard_with_pagination, get_main_menu_keyboard
from users.handlers import start
from users.models import UserModel
from users.utils import get_clickable_user_name
from .identifiers import resolve_vk_id, split_target_and_value
from .models import QuestionModel
from .keyboards import (
    admin_menu_keyboard,
    support_menu_keyboard,
    back_to_support_menu_keyboard,
    back_to_questions_list,
)
from .states import UnansweredQuestionsState, AnsweredQuestionsState
from .utils import STATUS_LEVELS, get_status_lvl

bl = BotLabeler()


@bl.private_message(payload={'menu': 'admin'})
async def open_admin_menu(message: Message):
    await message.answer('🗝 Открываю админ панель', keyboard=admin_menu_keyboard)


@bl.private_message(payload={'admin': 'admin_list'})
async def show_admin_list(message: Message):
    text = '📑 Список администраторов\n\n'
    for vk_id, status in admin_list.storage.items():
        text += f'{ADMIN_GRADES[status]["emoji"]} {status} - {await get_clickable_user_name(vk_id)}\n'
    await message.answer(text, keyboard=admin_menu_keyboard)


@bl.private_message(payload={'admin': 'support'})
async def show_support_menu(message: Message):
    await message.answer('☎ Открываю меню технической поддержки', keyboard=support_menu_keyboard)


@bl.private_message(payload={'support': 'unanswered'})
async def show_unanswered_questions(message: Message, questions: list = None, page_number: int = 0):
    text = f'📃 Список открытых обращений | Страница {page_number + 1}'

    if not questions:
        questions = await QuestionModel.filter(answer=None)
    number_of_questions = len(questions)

    if not number_of_questions:
        return await message.answer(
            '😕 Список обращений пуст',
            keyboard=support_menu_keyboard
        )

    questions_ids = []
    for q in questions[page_number * 3:page_number * 3 + 3]:
        questions_ids.append(q.pk)
        text += f'\n\n🔹№{q.pk}' \
                f'💬 {q.text}\n' \
                f'👤 Отправитель: {await get_clickable_user_name((await q.from_user).vk_id)}'

    kb = generate_choice_keyboard_with_pagination(
        numbers=questions_ids,
        prev_page=(page_number > 0),
        next_page=True if number_of_questions - (page_number * 3 + 3) > 0 else False,
        back_label='◀⁉ Обращения'
    )
    await message.answer(text, keyboard=kb)
    await bot.state_dispenser.set(
        message.from_id,
        UnansweredQuestionsState.SHOW_UNANSWERED_QUESTIONS,
        questions=questions,
        number_of_questions=number_of_questions,
        current_page=page_number,
        keyboard=kb
    )


@bl.private_message(state=UnansweredQuestionsState.SHOW_UNANSWERED_QUESTIONS)
async def choose_question_to_answer(message: Message):
    state_payload = message.state_peer.payload
    if not message.payload:
        return await message.answer(
            message='❗ Некорректный ввод!',
            keyboard=state_payload['keyboard']
        )

    choice = json.loads(message.payload)['choice']
    if choice == 'back':
        await bot.state_dispenser.delete(message.from_id)
        await show_support_menu(message)
    elif choice == 'prev_page':
        await show_unanswered_questions(
            message,
            questions=state_payload['questions'],
            page_number=state_payload['current_page'] - 1
        )
    elif choice == 'next_page':
        await show_unanswered_questions(
            message,
            questions=state_payload['questions'],
            page_number=state_payload['current_page'] + 1
        )
    else:
        await bot.state_dispenser.set(
            message.from_id,
            UnansweredQuestionsState.ANSWER_QUESTION,
            question_id=choice
        )
        await message.answer(
            f'📞 Для ответа выбран вопрос №{choice}\n\n'
            f'❗ Напишите ответ на вопрос или воспользуйтесь кнопкой, чтобы вернуться в меню тех.поддержки',
            keyboard=back_to_support_menu_keyboard
        )


@bl.private_message(state=UnansweredQuestionsState.ANSWER_QUESTION, text='<text>')
async def answer_question(message: Message, text=None):
    if text == '◀☎ Обращения':
        await bot.state_dispenser.delete(message.from_id)
        await show_support_menu(message)
    elif len(text) > 512:
        await message.answer(
            '❗ Длина ответа не должна превышать 512 символов!',
            keyboard=back_to_support_menu_keyboard
        )
    else:
        question = await QuestionModel.get(pk=message.state_peer.payload['question_id'])
        question.answer = text
        question.answered_by = await UserModel.get(vk_id=message.from_id)
        question.answered_at = datetime.now()
        await question.save(update_fields=['answer', 'answered_by_id', 'answered_at'])
        await bot.state_dispenser.delete(message.from_id)
        await message.answer('✔ Ответ успешно отправлен!', keyboard=support_menu_keyboard)

        await bot.api.messages.send(
            user_id=(await question.from_user).vk_id,
            random_id=random.randint(1, 2 ** 32),
            message='✨ Пришел ответ от тех.поддержки на ваш вопрос!\n\n'
                    f'💬 Текст ответа: {text}\n👔 Отправитель: {await get_clickable_user_name(message.from_id)}'
        )


@bl.private_message(payload={'support': 'answered'})
async def show_answered_questions(message: Message, questions: list = None, page_number: int = 0):
    text = f'📃 Список закрытых обращений | Страница {page_number + 1}'

    if not questions:
        questions = await QuestionModel.exclude(answer=None)
    number_of_questions = len(questions)

    if not number_of_questions:
        return await message.answer(
            '😕 Список обращений пуст',
            keyboard=support_menu_keyboard
        )

    questions_ids = []
    for q in questions[page_number * 3:page_number * 3 + 3]:
        questions_ids.append(q.pk)
        text += f'\n\n🔹 Обращение №{q.pk}\n' \
                f'💬 Текст обращения: {q.text}\n' \
                f'👤 Отправил: {await get_clickable_user_name((await q.from_user).vk_id)}\n' \
                f'👔 Ответил: {await get_clickable_user_name((await q.answered_by).vk_id)}'

    kb = generate_choice_keyboard_with_pagination(
        numbers=questions_ids,
        prev_page=(page_number > 0),
        next_page=True if number_of_questions - (page_number * 3 + 3) > 0 else False,
        back_label='◀⁉ Обращения'
    )
    await message.answer(text, keyboard=kb)
    await bot.state_dispenser.set(
        message.from_id,
        AnsweredQuestionsState.SHOW_ANSWERED_QUESTIONS,
        questions=questions,
        number_of_questions=number_of_questions,
        current_page=page_number,
        keyboard=kb
    )


@bl.private_message(state=AnsweredQuestionsState.SHOW_ANSWERED_QUESTIONS)
async def choose_question_to_get_info(message: Message):
    state_payload = message.state_peer.payload
    if not message.payload:
        return await message.answer(
            message='❗ Некорректный ввод!',
            keyboard=state_payload['keyboard']
        )

    choice = json.loads(message.payload)['choice']
    if choice == 'back':
        await bot.state_dispenser.delete(message.from_id)
        await show_support_menu(message)
    elif choice == 'current_page':
        await show_answered_questions(
            message,
            questions=state_payload['questions'],
            page_number=state_payload['current_page']
        )
    elif choice == 'prev_page':
        await show_answered_questions(
            message,
            questions=state_payload['questions'],
            page_number=state_payload['current_page'] - 1
        )
    elif choice == 'next_page':
        await show_answered_questions(
            message,
            questions=state_payload['questions'],
            page_number=state_payload['current_page'] + 1
        )
    else:
        question = await QuestionModel.get(pk=choice)

        await message.answer(
            f'📑 Детальная информация об обращении №{choice}\n\n'
            f'💬 Текст обращения: {question.text}\n'
            f'👤 Отправил: {await get_clickable_user_name((await question.from_user).vk_id)}\n'
            f'🕐 Время отправки: {question.created_at.strftime("%X %x")}\n\n'
            f'💬 Текст ответа: {question.answer}\n'
            f'👔 Ответил: {await get_clickable_user_name((await question.answered_by).vk_id)}\n'
            f'🕗 Время ответа: {question.answered_at.strftime("%X %x")}\n\n'
            '❗ Чтобы вернуться назад воспользуйтесь кнопкой',
            keyboard=back_to_questions_list
        )


@bl.private_message(payload={'support': 'answered_by_me'})
async def show_questions_answered_by_me(message: Message):
    questions = await QuestionModel.filter(
        answer__isnull=False,
        answered_by=await UserModel.get(
            vk_id=message.from_id
        )
    )
    await show_answered_questions(message, questions)


@bl.private_message(payload={'admin': 'stats'})
async def show_admin_stats(message: Message):
    user = await UserModel.get(vk_id=message.from_id)
    questions = await QuestionModel.filter(answered_by=user.pk).count()
    await message.answer(
        f'📉 Статистика {await get_clickable_user_name(message.from_id)}\n\n'
        f'{ADMIN_GRADES[user.status]["emoji"]} Админ-статус: {user.status}\n'
        f'☎ Кол-во ответов на обращения: {questions}\n',
        keyboard=admin_menu_keyboard
    )


@bl.private_message(payload={'admin': 'commands'})
async def show_admin_commands_list(message: Message):
    admin = await UserModel.get(vk_id=message.from_id)
    admin_lvl = ADMIN_GRADES[admin.status]['lvl']

    text = ''
    for grade in ADMIN_GRADES.values():
        if grade['lvl'] <= admin_lvl:
            for command in grade['commands']:
                text += f'\n{command}'

    await message.answer(
        f'🛠 Список доступных команд\n{text}' if text else '😕 Для вас нет доступных команд',
        keyboard=admin_menu_keyboard
    )


# ---------------------------------------------------------------------------
# Команды администраторов
#
# Пользователя в командах можно указывать по ID, короткому имени (@a.chelovech),
# ссылке на профиль или упоминанию - см. admin/identifiers.py
# ---------------------------------------------------------------------------

MONEY_ADMINS = ('Гл.Администратор', 'Основатель')

SETSTATUS_USAGE = (
    'ℹ Формат команды: /setstatus <пользователь> <lvl>\n\n'
    'Пользователя можно указать по ID, короткому имени или ссылке на профиль:\n'
    '/setstatus 12345678 2\n'
    '/setstatus @a.chelovech 2\n'
    '/setstatus vk.com/a.chelovech 2\n\n'
    'Уровни статусов:\n'
    + '\n'.join(f'{lvl} - {name}' for lvl, name in USER_STATUSES.items())
)
GIVEMONEY_USAGE = (
    'ℹ Формат команды: /givemoney <пользователь> <сумма>\n'
    'Пример: /givemoney @a.chelovech 500'
)
SETMONEY_USAGE = (
    'ℹ Формат команды: /setmoney <пользователь> <сумма>\n'
    'Пример: /setmoney @a.chelovech 500'
)
DEL_USAGE = (
    'ℹ Формат команды: /del <пользователь>\n'
    'Пример: /del @a.chelovech'
)


async def get_admin_or_start(message: Message) -> UserModel | None:
    """Возвращает отправителя, если он админ. Иначе ведёт себя как на любое непонятное сообщение."""
    admin = await UserModel.get_or_none(vk_id=message.from_id)
    if admin is None or admin.status == 'Пользователь':
        await start(message)
        return None
    return admin


async def get_target_user(message: Message, raw_target: str) -> UserModel | None:
    """Находит зарегистрированного в боте пользователя по ID / короткому имени / ссылке.

    Если не нашёл - сам отвечает админу и возвращает None.
    """
    vk_id = await resolve_vk_id(raw_target, bot.api)
    if vk_id is None:
        await message.answer(
            f'❗ Не удалось найти пользователя ВК по запросу «{raw_target}»!\n'
            'Укажите ID, короткое имя (например, @a.chelovech) или ссылку на профиль.',
            keyboard=admin_menu_keyboard
        )
        return None

    user = await UserModel.get_or_none(vk_id=vk_id)
    if user is None:
        await message.answer(
            '❗ Указанный пользователь не зарегистрирован в боте!\n'
            'Пусть он сначала напишет боту «Начать».',
            keyboard=admin_menu_keyboard
        )
    return user


def parse_amount(raw: str) -> int | None:
    """Положительное целое число или None."""
    if raw.isdecimal() and int(raw) > 0:
        return int(raw)
    return None


async def notify_user(vk_id: int, text: str, keyboard: Keyboard | None = None) -> None:
    """Отправляет пользователю уведомление. Если ему нельзя писать - тихо игнорирует."""
    params = {}
    if keyboard is not None:
        params['keyboard'] = keyboard
    try:
        await bot.api.messages.send(
            user_id=vk_id,
            random_id=random.randint(1, 2 ** 32),
            message=text,
            **params
        )
    except VKAPIError:
        pass


@bl.private_message(text='/setstatus <args>')
async def set_user_status(message: Message, args: str = None):
    appointing_admin = await get_admin_or_start(message)
    if appointing_admin is None:
        return

    parsed = split_target_and_value(args)
    if parsed is None or not parsed[1].isdecimal() or int(parsed[1]) not in USER_STATUSES:
        return await message.answer(SETSTATUS_USAGE, keyboard=admin_menu_keyboard)
    raw_target, lvl = parsed[0], int(parsed[1])

    appointee = await get_target_user(message, raw_target)
    if appointee is None:
        return

    if appointee.vk_id == message.from_id:
        return await message.answer(
            '❗ Некорректный ввод! Вы не можете изменить свой статус!',
            keyboard=admin_menu_keyboard
        )

    appointing_admin_lvl = get_status_lvl(appointing_admin.status)
    appointee_lvl = get_status_lvl(appointee.status)
    if appointee_lvl >= appointing_admin_lvl or appointing_admin_lvl <= lvl:
        return await message.answer('❗ У вас недостаточно прав!', keyboard=admin_menu_keyboard)

    new_status = USER_STATUSES[lvl]
    if appointee.status == new_status:
        return await message.answer(
            '❗ Пользователь уже имеет указанный статус!',
            keyboard=admin_menu_keyboard
        )

    old_status_lvl = STATUS_LEVELS.get(appointee.status, 0)
    appointee.status = new_status
    await appointee.save(update_fields=['status'])

    if new_status == 'Пользователь':
        admin_list.storage.pop(appointee.vk_id, None)
    else:
        admin_list.set(appointee.vk_id, new_status)

    await message.answer(
        f'✔ Вы изменили статус пользователя {await get_clickable_user_name(appointee.vk_id)} '
        f'на «{new_status}»!',
        keyboard=admin_menu_keyboard
    )

    emoji = '⏫' if lvl > old_status_lvl else '⏬'
    await notify_user(
        appointee.vk_id,
        f'{emoji} {appointing_admin.status} {await get_clickable_user_name(message.from_id)} '
        f'изменил ваш статус на «{new_status}»!',
        # Обновляем клавиатуру, чтобы кнопка «Админ панель» появилась/исчезла сразу
        keyboard=get_main_menu_keyboard(appointee.vk_id)
    )


@bl.private_message(text='/givemoney <args>')
async def give_money_to_user(message: Message, args: str = None):
    admin = await get_admin_or_start(message)
    if admin is None:
        return

    parsed = split_target_and_value(args)
    money = parse_amount(parsed[1]) if parsed else None
    if money is None:
        return await message.answer(GIVEMONEY_USAGE, keyboard=admin_menu_keyboard)

    if admin.status not in MONEY_ADMINS:
        return await message.answer(
            '❗ У вас недостаточно прав! Данной командой может воспользоваться только '
            'пользователь со статусом «Гл.Администратор» или «Основатель»!',
            keyboard=admin_menu_keyboard
        )

    recipient = await get_target_user(message, parsed[0])
    if recipient is None:
        return

    recipient.balance += money
    await recipient.save(update_fields=['balance'])

    await message.answer(
        f'✔ Баланс пользователя {await get_clickable_user_name(recipient.vk_id)} успешно пополнен на ${money}!',
        keyboard=admin_menu_keyboard
    )
    await notify_user(
        recipient.vk_id,
        f'💸 {admin.status} {await get_clickable_user_name(message.from_id)} '
        f'пополнил ваш баланс на ${money}!'
    )


@bl.private_message(text='/setmoney <args>')
async def set_money_for_user(message: Message, args: str = None):
    admin = await get_admin_or_start(message)
    if admin is None:
        return

    parsed = split_target_and_value(args)
    money = parse_amount(parsed[1]) if parsed else None
    if money is None:
        return await message.answer(SETMONEY_USAGE, keyboard=admin_menu_keyboard)

    if admin.status not in MONEY_ADMINS:
        return await message.answer(
            '❗ У вас недостаточно прав! Данной командой может воспользоваться только '
            'пользователь со статусом «Гл.Администратор» или «Основатель»!',
            keyboard=admin_menu_keyboard
        )

    recipient = await get_target_user(message, parsed[0])
    if recipient is None:
        return

    recipient.balance = money
    await recipient.save(update_fields=['balance'])

    await message.answer(
        f'✔ Баланс пользователя {await get_clickable_user_name(recipient.vk_id)} успешно изменен на ${money}!',
        keyboard=admin_menu_keyboard
    )
    await notify_user(
        recipient.vk_id,
        f'💵 {admin.status} {await get_clickable_user_name(message.from_id)} '
        f'изменил ваш баланс на ${money}!'
    )


@bl.private_message(text='/del <args>')
async def del_user_account(message: Message, args: str = None):
    admin = await get_admin_or_start(message)
    if admin is None:
        return

    if not args or not args.strip():
        return await message.answer(DEL_USAGE, keyboard=admin_menu_keyboard)

    if admin.status != 'Основатель':
        return await message.answer(
            '❗ У вас недостаточно прав! Данной командой может воспользоваться только '
            'пользователь со статусом «Основатель»!',
            keyboard=admin_menu_keyboard
        )

    user = await get_target_user(message, args.strip())
    if user is None:
        return

    await user.delete()
    admin_list.storage.pop(user.vk_id, None)

    await message.answer(
        f'✔ Аккаунт пользователя {await get_clickable_user_name(user.vk_id)} удалён!',
        keyboard=admin_menu_keyboard
    )
    await notify_user(
        user.vk_id,
        f'❗❌ {admin.status} {await get_clickable_user_name(message.from_id)} удалил ваш аккаунт!',
        keyboard=Keyboard()
    )
