"""Разбор того, как админ указывает пользователя ВК в командах.

Поддерживаются:
    12345678                      - числовой ID
    id12345678                    - ID с префиксом
    @a.chelovech, *a.chelovech    - короткое имя
    a.chelovech                   - короткое имя без значка
    https://vk.com/a.chelovech    - ссылка на профиль (vk.com, vk.ru, m.vk.com)
    [id12345678|Имя]              - упоминание
    [a.chelovech|Имя]             - упоминание по короткому имени
"""
import re
from dataclasses import dataclass

# [id123|Имя], [durov|Павел], [club1|Сообщество]
_MENTION_RE = re.compile(r'^\[([^\[\]|\s]+)\|[^\[\]]*\]$')
_URL_RE = re.compile(
    r'^(?:https?://)?(?:(?:www|m)\.)?(?:vk\.com|vk\.ru|vkontakte\.ru)/([^/?#\s]+)',
    re.IGNORECASE,
)
_NUMERIC_ID_RE = re.compile(r'^(?:id)?(\d+)$', re.IGNORECASE)
_COMMUNITY_RE = re.compile(r'^(?:club|public|event)\d+$', re.IGNORECASE)
_SCREEN_NAME_RE = re.compile(r'^[A-Za-z0-9_.]{1,32}$')


@dataclass(frozen=True)
class VkTarget:
    """Результат разбора: либо готовый ID, либо короткое имя, которое надо резолвить через API."""
    vk_id: int | None = None
    screen_name: str | None = None


def parse_vk_target(raw: str | None) -> VkTarget | None:
    """Разбирает строку с пользователем. Возвращает None, если это не похоже на пользователя ВК."""
    if not raw:
        return None

    token = raw.strip()

    mention = _MENTION_RE.match(token)
    if mention:
        token = mention.group(1)
    else:
        url = _URL_RE.match(token)
        if url:
            token = url.group(1)

    token = token.lstrip('@*')

    numeric = _NUMERIC_ID_RE.match(token)
    if numeric:
        vk_id = int(numeric.group(1))
        return VkTarget(vk_id=vk_id) if vk_id > 0 else None

    if _COMMUNITY_RE.match(token):
        return None

    if _SCREEN_NAME_RE.match(token):
        return VkTarget(screen_name=token)

    return None


def split_target_and_value(args: str | None) -> tuple[str, str] | None:
    """Делит «<пользователь> <значение>» по последнему пробелу.

    Так пользователь может быть записан с пробелами, например «[id1|Иван Иванов]».
    """
    if not args:
        return None
    parts = args.strip().rsplit(maxsplit=1)
    if len(parts) != 2:
        return None
    return parts[0], parts[1]


async def resolve_vk_id(raw: str | None, api) -> int | None:
    """Возвращает ID пользователя ВК по ID, короткому имени, ссылке или упоминанию.

    None - если разобрать строку не удалось или такого пользователя нет
    (в том числе если короткое имя принадлежит сообществу).
    """
    from vkbottle import VKAPIError

    target = parse_vk_target(raw)
    if target is None:
        return None
    if target.vk_id is not None:
        return target.vk_id

    try:
        users = await api.users.get(user_ids=[target.screen_name])
    except VKAPIError:
        return None
    return users[0].id if users else None
