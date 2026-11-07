from tortoise.exceptions import DoesNotExist
from tortoise.expressions import Q

from core.settings import ADMIN_GRADES, ADMIN_ID, USER_STATUSES
from core.loader import admin_list
from users.models import UserModel


async def appoint_superuser():
    try:
        superuser = await UserModel.get(vk_id=ADMIN_ID)
    except DoesNotExist:
        pass
    else:
        if superuser.status != 'Основатель':
            superuser.status = 'Основатель'
            await superuser.save(update_fields=['status'])


async def save_admin_list():
    for user in await UserModel.filter(~Q(status='Пользователь')):
        admin_list.set(user.vk_id, user.status)


# Название статуса -> уровень, который админ указывает в /setstatus (0-4)
STATUS_LEVELS = {name: lvl for lvl, name in USER_STATUSES.items()}


def get_status_lvl(status: str) -> int:
    """Вес статуса для сравнения прав (у обычного пользователя - 0)."""
    grade = ADMIN_GRADES.get(status)
    return grade['lvl'] if grade else 0
