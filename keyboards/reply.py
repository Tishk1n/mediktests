from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="📝 Начать тест", callback_data="start_test"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")
        ],
        [
            InlineKeyboardButton(text="💳 Купить подписку", callback_data="buy_subscription"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_settings_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="🔄 Изменить данные", callback_data="change_credentials"),
            InlineKeyboardButton(text="❌ Удалить аккаунт", callback_data="delete_account")
        ],
        [
            InlineKeyboardButton(text="« Назад", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="📝 Начать тест", callback_data="start_test"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")
        ],
        [
            InlineKeyboardButton(text="💳 Реквизиты", callback_data="requisites"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_subscription_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="1 День - 100₽", callback_data="buy_1_day"),
            InlineKeyboardButton(text="7 Дней - 500₽", callback_data="buy_7_days")
        ],
        [
            InlineKeyboardButton(text="1 Месяц - 1000₽", callback_data="buy_30_days")
        ],
        [
            InlineKeyboardButton(text="« Назад", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_payment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data="confirm_payment")]
    ])

def get_admin_payment_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_payment_{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_payment_{user_id}")
        ]
    ])

def get_requisites_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="🔄 Изменить реквизиты", callback_data="change_requisites")
        ],
        [
            InlineKeyboardButton(text="« Назад", callback_data="back_to_admin_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
