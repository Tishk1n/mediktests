from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.markdown import hbold
from database.sqlite import Database
from keyboards.reply import get_main_keyboard, get_settings_keyboard
from utils.test_utils import start_testing_process

router = Router()

class UserAuth(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()
    waiting_for_test_url = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: Database):
    # Проверяем, есть ли уже сохраненные данные
    credentials = db.get_user_credentials(message.from_user.id)
    
    if credentials:
        await message.answer(
            "👋 С возвращением! Ваши данные уже сохранены.\n"
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            "👋 Добро пожаловать!\n"
            "Для начала работы необходимо сохранить данные вашего аккаунта.\n"
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

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🔍 Доступные команды:\n"
        "/start - Начать работу\n"
        "/stats - Статистика\n"
        "/settings - Настройки\n"
        "/help - Помощь"
    )
