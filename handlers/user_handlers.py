from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.markdown import hbold
from database.sqlite import Database
from keyboards.reply import get_main_keyboard, get_settings_keyboard, get_admin_keyboard, get_subscription_keyboard
from utils.test_utils import start_testing_process
from config import load_config
from datetime import datetime, timedelta
from utils.subscription import format_subscription_type

router = Router()

class UserAuth(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()
    waiting_for_test_url = State()
    waiting_for_payment_screenshot = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: Database):
    config = load_config()
    is_admin = message.from_user.id in config.tg_bot.admin_ids
    
    if is_admin:
        await message.answer(
            "👋 Добро пожаловать в панель администратора!\n"
            "Выберите действие:",
            reply_markup=get_admin_keyboard()
        )
        return

    # Получаем информацию о подписке
    subscription = db.get_subscription_details(message.from_user.id)
    credentials = db.get_user_credentials(message.from_user.id)
    
    if not subscription["active"]:
        # Даем демо-доступ на 30 минут
        db.add_subscription(message.from_user.id, 0.0208333, "demo")
        subscription = db.get_subscription_details(message.from_user.id)
    
    # Форматируем оставшееся время
    time_left = subscription["time_left"]
    if time_left:
        if time_left.days > 0:
            time_str = f"{time_left.days} {'день' if time_left.days == 1 else 'дней'}"
        else:
            hours = time_left.seconds // 3600
            minutes = (time_left.seconds % 3600) // 60
            time_str = f"{hours}ч {minutes}м"
    else:
        time_str = "истекла"

    # Формируем сообщение
    message_text = (
        f"👋 Приветствую, {message.from_user.first_name}!\n\n"
        f"💫 Ваша подписка:\n"
        f"Тип: {format_subscription_type(subscription['type']) if subscription['type'] else 'Отсутствует'}\n"
        f"Истекает через: {time_str}\n"
        f"Данные от FMZA: {'✅' if credentials else '❌'}\n"
    )
    
    if not credentials:
        message_text += "\n⚠️ Для начала работы необходимо сохранить данные вашего аккаунта."
    
    await message.answer(
        message_text,
        reply_markup=get_main_keyboard()
    )
    
    if not credentials:
        await message.answer(
            "Введите ваш логин от сайта selftest-mpe.medtech.ru:"
        )
        await state.set_state(UserAuth.waiting_for_login)

@router.message(UserAuth.waiting_for_login)
async def process_login(message: Message, state: FSMContext):
    await state.update_data(login=message.text)
    await message.answer("Теперь введите пароль:")
    await state.set_state(UserAuth.waiting_for_password)

@router.message(UserAuth.waiting_for_password)
async def process_password(message: Message, state: FSMContext, db: Database):
    await message.delete()  # Удаляем сообщение с паролем
    data = await state.get_data()
    login = data.get("login")
    password = message.text
    
    # Сохраняем данные
    db.save_user_credentials(message.from_user.id, login, password)
    
    await message.answer(
        "✅ Данные успешно сохранены!\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )
    await state.clear()

@router.callback_query(F.data == "start_test")
async def start_test(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🔗 Пожалуйста, отправьте ссылку на начатый тест:"
    )
    await state.set_state(UserAuth.waiting_for_test_url)

@router.message(UserAuth.waiting_for_test_url)
async def process_test_url(message: Message, state: FSMContext, db: Database):
    await state.clear()
    await message.answer(
        "🔄 Начинаю процесс тестирования...\n"
        "Пожалуйста, подождите"
    )
    
    result = await start_testing_process(
        user_id=message.from_user.id,
        db=db,
        bot=message.bot,
        test_url=message.text
    )
    
    if "error" in result:
        await message.answer(
            f"❌ {result['error']}",
            reply_markup=get_main_keyboard()
        )
        return
    
    await message.answer(
        f"📊 Результат тестирования:\n"
        f"Правильных ответов: {result['correct']}/{result['total']}\n"
        f"Процент: {result['percentage']}%",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "show_stats")
async def show_statistics(callback: CallbackQuery, db: Database):
    stats = db.get_user_statistics(callback.from_user.id)
    
    text = (
        f"📊 {hbold('Ваша статистика:')}\n\n"
        f"Всего тестов: {stats['total_tests']}\n"
        f"Средний балл: {stats['average_score']}%\n"
        f"Лучший результат: {stats['best_score']}%\n"
        f"Последний тест: {stats['last_test_date']}"
    )
    
    await callback.message.edit_text(text, reply_markup=get_main_keyboard())

@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚙️ Настройки:\n"
        "- Изменить учетные данные\n"
        "- Удалить аккаунт",
        reply_markup=get_settings_keyboard()
    )

@router.callback_query(F.data == "buy_subscription")
async def show_subscription_plans(callback: CallbackQuery):
    await callback.message.edit_text(
        "💫 Выберите длительность подписки:\n\n"
        "• 1 День - 100₽\n"
        "• 7 Дней - 500₽\n"
        "• 1 Месяц - 1000₽\n\n"
        "✨ Подписка дает полный доступ ко всем функциям бота",
        reply_markup=get_subscription_keyboard()
    )

@router.callback_query(F.data.startswith("buy_"))
async def process_subscription_purchase(callback: CallbackQuery, db: Database):
    duration = callback.data.replace("buy_", "")  # Получаем только часть с длительностью
    prices = {"1_day": 100, "7_days": 500, "30_days": 1000}
    days = {"1_day": 1, "7_days": 7, "30_days": 30}
    
    if duration not in prices:
        await callback.answer("Неверный выбор подписки")
        return
    
    # Получаем реквизиты
    requisites = db.get_requisites()
    if not requisites or not any(requisites):
        await callback.message.edit_text(
            "❌ Оплата временно недоступна. Обратитесь к администратору.",
            reply_markup=get_main_keyboard()
        )
        return
    
    card_number, sbp, bank, holder = requisites
    text = (
        f"💳 Оплата подписки на {days[duration]} {'день' if days[duration] == 1 else 'дней'}\n"
        f"Сумма к оплате: {prices[duration]}₽\n\n"
        f"Реквизиты для оплаты:\n"
        f"Номер карты: {card_number}\n"
        f"СБП: {sbp}\n"
        f"Банк: {bank}\n"
        f"Получатель: {holder}\n\n"
        "После оплаты нажмите кнопку «Подтвердить оплату» и отправьте скриншот чека."
    )
    
    # Сохраняем информацию о выбранной подписке
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"confirm_{duration}")],
            [InlineKeyboardButton(text="« Назад", callback_data="buy_subscription")]
        ])
    )

@router.callback_query(F.data.startswith("confirm_"))
async def confirm_payment(callback: CallbackQuery, state: FSMContext):
    duration = callback.data.split("_")[1]
    
    # Убедимся, что duration в правильном формате
    if not duration.endswith("_day") and not duration.endswith("_days"):
        duration = f"{duration}_days" if duration != "1" else "1_day"
    
    await state.update_data(subscription_duration=duration)
    await callback.message.edit_text(
        "📸 Пожалуйста, отправьте скриншот чека об оплате"
    )
    await state.set_state(UserAuth.waiting_for_payment_screenshot)

@router.message(UserAuth.waiting_for_payment_screenshot)
async def process_payment_screenshot(message: Message, state: FSMContext, db: Database):
    if not message.photo:
        await message.answer("Пожалуйста, отправьте скриншот чека в виде фотографии")
        return
    
    data = await state.get_data()
    duration = data.get("subscription_duration")
    await state.clear()
    
    config = load_config()
    admin_id = config.tg_bot.admin_ids[0]
    
    subscription_data = f"{message.from_user.id}_{duration}"  # Создаем строку с данными
    
    await message.bot.send_photo(
        admin_id,
        message.photo[-1].file_id,
        caption=(
            f"💫 Новая оплата подписки\n"
            f"От пользователя: {message.from_user.username or 'Без username'} ({message.from_user.id})\n"
            f"Тип подписки: {duration}"
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=f"approve_{subscription_data}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject_{message.from_user.id}"
                )
            ]
        ])
    )
    
    await message.answer(
        "✅ Скриншот отправлен на проверку администратору.\n"
        "Пожалуйста, ожидайте подтверждения оплаты.",
        reply_markup=get_main_keyboard()
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🔍 Доступные команды:\n"
        "/start - Начать работу\n"
        "/stats - Статистика\n"
        "/settings - Настройки\n"
        "/help - Помощь"
    )
