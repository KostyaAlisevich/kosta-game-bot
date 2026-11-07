import os

from dotenv import load_dotenv

# Env
load_dotenv()
TOKEN = os.getenv('TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')


BASE_DIR = os.path.join(os.getcwd(), 'scr')


# Assets
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
FONTS_DIR = os.path.join(ASSETS_DIR, 'fonts')
IMG_DIR = os.path.join(ASSETS_DIR, 'img')

MAIN_FONT_PATH = os.path.join(FONTS_DIR, 'Fifaks10Dev1.ttf')


# Database
DB_DIR = os.path.join(BASE_DIR, 'database')
DSN = f'sqlite://{DB_DIR}/db.sqlite3?journal_mode=delete'

MODELS = [
    'users.models',
    'mining.models',
    'income.models',
    'admin.models',
    'jobs.models',
    'aerich.models',
]

DB_CONFIG = {
    'connections': {
        'default': DSN,
    },
    'apps': {
        'models': {
            'models': MODELS,
            'default_connection': 'default',
        },
    },
}


USER_STATUSES = {
    0: 'Пользователь',
    1: 'Хелпер',
    2: 'Администратор',
    3: 'Гл.Администратор',
    4: 'Основатель'
}

ADMIN_GRADES = {
    'Хелпер': {
        'lvl': 1,
        'emoji': '🦺',
        'commands': []
    },
    'Администратор': {
        'lvl': 2,
        'emoji': '👔',
        'commands': [
            '/setstatus <пользователь> <lvl> - изменить статус (0 - пользователь, 1 - хелпер, 2 - админ, 3 - гл.админ). '
            'Пользователь: ID, @имя или ссылка, например /setstatus @a.chelovech 2',
        ]
    },
    'Гл.Администратор': {
        'lvl': 3,
        'emoji': '🎩',
        'commands': [
            '/givemoney <пользователь> <money> - пополнить баланс пользователя',
            '/setmoney <пользователь> <money> - изменить баланс пользователя',
        ]
    },
    'Основатель': {
        'lvl': 5,
        'emoji': '👑',
        'commands': [
            '/del <пользователь> - удаление аккаунта пользователя',
        ]
    }
}
