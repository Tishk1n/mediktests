from datetime import datetime, timedelta
from typing import Dict

SUBSCRIPTION_PRICES = {
    "1_day": 100,
    "7_days": 500,
    "30_days": 1000
}

def get_subscription_info(sub_type: str) -> Dict[str, any]:
    days_map = {"1_day": 1, "7_days": 7, "30_days": 30}
    return {
        "days": days_map.get(sub_type, 0),
        "price": SUBSCRIPTION_PRICES.get(sub_type, 0)
    }

def format_subscription_type(sub_type: str) -> str:
    types_map = {
        "30_days": "1 Месяц",
        "7_days": "7 Дней",
        "1_day": "1 День",
        "demo": "Демо-доступ"
    }
    return types_map.get(sub_type, "Неизвестный тип")

def format_subscription_message(sub_type: str, requisites: tuple) -> str:
    info = get_subscription_info(sub_type)
    card_number, sbp, bank, holder = requisites
    
    return (
        f"💳 Оплата подписки на {info['days']} {'день' if info['days'] == 1 else 'дней'}\n"
        f"Сумма к оплате: {info['price']}₽\n\n"
        f"Реквизиты для оплаты:\n"
        f"Номер карты: {card_number}\n"
        f"СБП: {sbp}\n"
        f"Банк: {bank}\n"
        f"Получатель: {holder}\n\n"
        "После оплаты нажмите кнопку 'Подтвердить оплату' и отправьте скриншот чека."
    )
