from collections.abc import Sequence

from vkbottle import Keyboard, Text, KeyboardButtonColor

from .catalog import Job


def build_jobs_keyboard(page_jobs: Sequence[Job], page: int, total_pages: int) -> Keyboard:
    keyboard = Keyboard()

    for i, job in enumerate(page_jobs):
        if i and i % 2 == 0:
            keyboard.row()
        keyboard.add(
            Text(f'{job.emoji} {job.title}', payload={'choice': job.key}),
            color=KeyboardButtonColor.PRIMARY
        )

    keyboard.row()
    if page > 0:
        keyboard.add(Text('◀ Пред.стр', payload={'choice': 'prev_page'}))
    keyboard.add(Text('🔄 Обновить', payload={'choice': 'refresh'}), color=KeyboardButtonColor.SECONDARY)
    if page < total_pages - 1:
        keyboard.add(Text('След.стр ▶', payload={'choice': 'next_page'}))

    keyboard.row()
    keyboard.add(Text('◀ В меню заработка', payload={'choice': 'back'}))
    return keyboard
