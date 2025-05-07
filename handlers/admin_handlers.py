from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold
from database.sqlite import Database
from keyboards.reply import get_admin_keyboard, get_requisites_keyboard
from utils.subscription import format_subscription_type

router = Router()

class RequisitesStates(StatesGroup):
    waiting_for_card = State()
    waiting_for_sbp = State()
    waiting_for_bank = State()
    waiting_for_holder = State()

@router.callback_query(F.data == "requisites")
async def show_requisites(callback: CallbackQuery, db: Database):
    card_number, sbp, bank, holder = db.get_requisites()
    text = (
        f"{hbold('💳 Текущие реквизиты:')}\n\n"
        f"Номер карты: {card_number or 'Не указан'}\n"
        f"СБП: {sbp or 'Не указан'}\n"
        f"Банк: {bank or 'Не указан'}\n"
        f"Получатель: {holder or 'Не указан'}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_requisites_keyboard()
    )

@router.callback_query(F.data == "change_requisites")
async def change_requisites_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите номер карты:",
        reply_markup=None
    )
    await state.set_state(RequisitesStates.waiting_for_card)

@router.message(RequisitesStates.waiting_for_card)
async def process_card(message: Message, state: FSMContext):
    await state.update_data(card=message.text)
    await message.answer("Введите номер СБП:")
    await state.set_state(RequisitesStates.waiting_for_sbp)

@router.message(RequisitesStates.waiting_for_sbp)
async def process_sbp(message: Message, state: FSMContext):
    await state.update_data(sbp=message.text)
    await message.answer("Введите название банка:")
    await state.set_state(RequisitesStates.waiting_for_bank)

@router.message(RequisitesStates.waiting_for_bank)
async def process_bank(message: Message, state: FSMContext):
    await state.update_data(bank=message.text)
    await message.answer("Введите ФИО получателя:")
    await state.set_state(RequisitesStates.waiting_for_holder)

@router.message(RequisitesStates.waiting_for_holder)
async def process_holder(message: Message, state: FSMContext, db: Database):
    data = await state.get_data()
    db.save_requisites(
        card_number=data['card'],
        sbp=data['sbp'],
        bank=data['bank'],
        holder_name=message.text
    )
    await state.clear()
    await message.answer(
        "✅ Реквизиты успешно обновлены!",
        reply_markup=get_admin_keyboard()
    )

@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: CallbackQuery, db: Database):
    try:
        # Получаем данные из callback_data
        full_data = callback.data.replace("approve_", "")
        user_id, duration = full_data.split("_", 1)  # Разделяем только один раз
        user_id = int(user_id)
        
        # Исправляем словарь с днями подписки
        days_mapping = {
            "1_day": 1,
            "7_days": 7,
            "30_days": 30
        }
        
        days = days_mapping.get(duration)
        if not days:
            await callback.answer("Ошибка: неверный тип подписки")
            return
        
        # Добавляем подписку
        db.add_subscription(user_id, days, duration)
        
        await callback.bot.send_message(
            user_id,
            "✅ Ваша оплата подтверждена!\n"
            f"Подписка {format_subscription_type(duration)} активирована."
        )
        
        await callback.message.edit_text(
            f"✅ Подписка для пользователя {user_id} активирована"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при подтверждении оплаты: {e}")
        await callback.answer("Произошла ошибка при обработке оплаты")

@router.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    
    # Уведомляем пользователя
    await callback.bot.send_message(
        user_id,
        "❌ Оплата не подтверждена.\n"
        "Пожалуйста, проверьте корректность оплаты и попробуйте снова."
    )
    
    await callback.message.edit_text(
        f"❌ Оплата от пользователя {user_id} отклонена"
    )
