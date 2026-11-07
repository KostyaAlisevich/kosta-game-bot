from datetime import date

from tortoise.exceptions import DoesNotExist
from tortoise.expressions import F
from vkbottle.bot import Message
from vkbottle.framework.labeler import BotLabeler

from income.models import DailyBonus
from users.models import UserModel

bl = BotLabeler()


@bl.private_message(payload={'income_menu': 'bonus'})
async def get_daily_bonus(message: Message):
    user = await UserModel.get(vk_id=message.from_id)
    try:
        bonus = await DailyBonus.get(user__vk_id=message.from_id)
        if (bonus.receiving_date - date.today()).days == 0:
            return await message.answer('❗ Сегодня вы уже получили бонус, возвращайтесь завтра!')
    except DoesNotExist:
        await DailyBonus.create(user=user, receiving_date=date.today(), amount=1)
    else:
        bonus.amount = F('amount') + 1
        bonus.receiving_date = date.today()
        await bonus.save(update_fields=['receiving_date', 'amount'])
    user.balance = F('balance') + 250
    await user.save(update_fields=['balance'])
    await message.answer('✔ Получен ежедневный бонус в размере $250!')
