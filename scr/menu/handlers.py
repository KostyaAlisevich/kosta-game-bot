from tortoise.expressions import Q
from vkbottle.bot import Message
from vkbottle.framework.labeler import BotLabeler
from vkbottle.modules import json

from core.loader import bot
from games.keyboards import games_menu_keyboard
from core.utils import convert_image_to_bytes, upload_image
from users.images import create_profile_image
from users.models import UserModel, BackgroundColorModel
from users.utils import get_user_name
from admin.models import QuestionModel
from core.utils import run_func_in_process
from .images import create_color_choice_image
from .keyboards import (
    main_menu_keyboard,
    shop_menu_keyboard,
    income_menu_keyboard,
    settings_menu_keyboard,
    back_to_settings_keyboard,
    back_to_menu_keyboard,
)
from .states import ContactSupportState, SettingsState
from .utils import generate_choice_keyboard_with_pagination, get_main_menu_keyboard

bl = BotLabeler()


@bl.private_message(payload={'menu': 'back'})
async def back_to_menu(message: Message):
    await message.answer("🎈 Главное меню", keyboard=get_main_menu_keyboard(message.from_id))


@bl.private_message(payload={'menu': 'profile'})
async def show_profile(
        message: Message,
        text='👤 Ваш профиль',
        keyboard=None
):
    user = await UserModel.get(vk_id=message.from_id)
    user = await user.convert_to_dataclass()

    vk_user_name = await get_user_name(message.from_id)

    image = await run_func_in_process(create_profile_image, user, vk_user_name)
    image = await upload_image(convert_image_to_bytes(image))

    if keyboard is None:
        keyboard = get_main_menu_keyboard(message.from_id)

    await message.answer(
        message=text,
        attachment=image,
        keyboard=keyboard
    )


@bl.private_message(payload={'menu': 'shop'})
async def show_shop_menu(message: Message):
    await message.answer(
        '✏ Кастомизация персонажа\n'
        'Изменение внешнего вида персонажа\n\n'
        '📼 Видеокарты\n'
        'Видеокарты каждый час приносят прибыль.'
        'Чем дороже модель видеокарты, тем выше доход',
        keyboard=shop_menu_keyboard
    )


@bl.private_message(payload={'menu': 'income'})
async def show_income_menu(message: Message):
    await message.answer(
        'Как заработать 💵?\n\n'
        '💸 Ежедневный бонус\n'
        'Раз в сутки получайте денежный бонус!\n\n\n'
        '🔨 Работа\n'
        'Более 20 профессий: от раздатчика листовок до космонавта. '
        'Чем выше оплата, тем дольше перерыв между сменами!\n\n\n'
        '🖥 Майнинг - фермы:\n'
        'Покупайте видеокарты, которые каждый час приносят прибыль!',
        keyboard=income_menu_keyboard
    )


@bl.private_message(payload={'menu': 'games'})
async def games(message: Message):
    await message.answer('🕹 Список игр', keyboard=games_menu_keyboard)


@bl.private_message(payload={'menu': 'help'})
async def contact_support(message: Message):
    await message.answer('✏ Напишите свой вопрос', keyboard=back_to_menu_keyboard)
    await bot.state_dispenser.set(message.peer_id, ContactSupportState.QUESTION)


@bl.private_message(state=ContactSupportState.QUESTION, text='<text>')
async def submit_question(message: Message, text=None):
    if text == '◀ В главное меню':
        await bot.state_dispenser.delete(message.peer_id)
        await back_to_menu(message)
    elif len(text) > 512:
        await message.answer(
            '❗ Длина вопроса не должна превышать 512 символов!',
            keyboard=back_to_menu_keyboard
        )
    else:
        user = await UserModel.get(vk_id=message.from_id)
        await QuestionModel.create(text=text, from_user=user)
        await message.answer(
            '💬 Ваш вопрос успешно отправлен!',
            keyboard=get_main_menu_keyboard(message.from_id)
        )
        await bot.state_dispenser.delete(message.peer_id)


@bl.private_message(payload={'menu': 'settings'})
async def show_settings_menu(message: Message):
    await message.answer(
        'В настройках вы можете изменить имя и фон',
        keyboard=settings_menu_keyboard
    )


@bl.private_message(payload={'settings': 'change_name'})
async def change_name(message: Message):
    await message.answer('🧐 Напишите новое имя', keyboard=back_to_settings_keyboard)
    await bot.state_dispenser.set(message.peer_id, SettingsState.NAME)


@bl.private_message(state=SettingsState.NAME, text='<text>')
async def set_new_name(message: Message, text=None):
    if text == '◀⚙ В настройки':
        await message.answer('⚙ Настройки', keyboard=settings_menu_keyboard)
        await bot.state_dispenser.delete(message.from_id)
    elif len(text) > 16:
        await message.answer('❗ Длина имя не может превышать 16 символов')
    else:
        await UserModel.filter(vk_id=message.from_id).update(nickname=text)
        await show_profile(
            message, text=f'Имя изменено на «{text}»', keyboard=main_menu_keyboard)
        await bot.state_dispenser.delete(message.from_id)


@bl.private_message(payload={'settings': 'change_background'})
async def show_change_background_page(message: Message, page_number: int = 1):
    colors = await BackgroundColorModel.filter(
        Q(pk__gte=page_number * 3 - 2) & Q(pk__lte=page_number * 3 + 1)
    )

    choice_numbers = [color.pk for color in colors[:3]]

    keyboard = generate_choice_keyboard_with_pagination(
        numbers=choice_numbers,
        prev_page=(page_number > 1),
        next_page=(len(colors) == 4),
        back_label='◀⚙ В настройки'
    )

    image = create_color_choice_image(
        colors=[color.hex for color in colors[:3]],
        choice_numbers=choice_numbers)
    image = await upload_image(convert_image_to_bytes(image))

    await message.answer(
        '🎨 Выберите новый цвет фона' if page_number == 1 else '',
        attachment=image,
        keyboard=keyboard
    )
    await bot.state_dispenser.set(
        message.from_id,
        SettingsState.BACKGROUND,
        current_page=page_number,
        keyboard=keyboard
    )


@bl.private_message(state=SettingsState.BACKGROUND)
async def set_new_background(message: Message):
    state_payload = message.state_peer.payload
    if not message.payload:
        return await message.answer(
            message='❗ Некорректный ввод!',
            keyboard=state_payload['keyboard']
        )

    choice = json.loads(message.payload)['choice']
    if choice == 'back':
        await bot.state_dispenser.delete(message.from_id)
        await show_settings_menu(message)
    elif choice == 'prev_page':
        await show_change_background_page(message, state_payload['current_page'] - 1)
    elif choice == 'next_page':
        await show_change_background_page(message, state_payload['current_page'] + 1)
    else:
        await UserModel.filter(vk_id=message.from_id).update(background_color_id=choice)
        await bot.state_dispenser.delete(message.peer_id)
        await show_profile(message, text='🎨 Вы изменили цвет фона')
