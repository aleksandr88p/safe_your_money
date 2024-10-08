# utils.py

import json
from datetime import datetime
from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from ai_api.models.models import Purchase, Transaction, User
from sqlalchemy.orm import Session
from ai_api.config import config  # Подключаем конфигурацию

api_key_header = APIKeyHeader(name="Authorization")

def check_bearer_token(api_key_header: str = Security(api_key_header)):
    """
    Проверяет токен API на соответствие.
    """
    if api_key_header != f"Bearer {config.API_HEADER_TOKEN}":
        raise HTTPException(status_code=403, detail="Could not validate credentials")
    return api_key_header

def save_to_db(db: Session, user_id: int, analyzed_data: dict, timestamp=None):
    """
    Сохраняет проанализированные данные о покупках и транзакциях в базу данных.
    """
    # Проверка, существует ли пользователь
    user = db.query(User).filter(User.telegram_id == str(user_id)).first()
    if not user:
        # Если пользователя нет, создаем его
        user = User(telegram_id=str(user_id))
        db.add(user)
        db.commit()
        db.refresh(user)

    # Сохраняем покупки в таблицу purchases
    total_price = 0.0
    currency = ""
    for category, items in analyzed_data.items():
        if category == "total_price":
            total_price = float(items.split()[0])
            currency = items.split()[1]
        elif isinstance(items, list):
            for item in items:
                # Если данных нет, используем значение по умолчанию
                item_name = item.get('name', 'Unknown')
                quantity = item.get('quantity', None)
                price_str = item.get('price', None)
                price_value = None
                item_currency = None

                if price_str and price_str != "None":
                    price_parts = price_str.split()
                    if len(price_parts) == 2:
                        price_value = float(price_parts[0])
                        item_currency = price_parts[1]
                    else:
                        price_value = float(price_parts[0])

                purchase = Purchase(
                    user_id=user.id,
                    category=category,
                    item_name=item_name,
                    quantity=quantity,
                    price=price_value,
                    currency=item_currency,
                    timestamp=datetime.fromisoformat(timestamp)
                )
                db.add(purchase)
        else:
            # Если items не является списком, обрабатываем его как единичный элемент
            item_name = items.get('name', 'Unknown')
            quantity = items.get('quantity', None)
            price_str = items.get('price', None)
            price_value = None
            item_currency = None

            if price_str and price_str != "None":
                price_parts = price_str.split()
                if len(price_parts) == 2:
                    price_value = float(price_parts[0])
                    item_currency = price_parts[1]
                else:
                    price_value = float(price_parts[0])

            purchase = Purchase(
                user_id=user.id,
                category=category,
                item_name=item_name,
                quantity=quantity,
                price=price_value,
                currency=item_currency,
                timestamp=datetime.fromisoformat(timestamp)
            )
            db.add(purchase)

    # Сохраняем транзакцию
    if total_price > 0.0:
        transaction = Transaction(
            user_id=user.id,
            total_price=total_price,
            currency=currency,
            timestamp=datetime.fromisoformat(timestamp)
        )
        db.add(transaction)

    db.commit()


def write_temp_data(user_id: int, text: str):
    """
    Записывает временные данные после распознавания аудио.
    """
    try:
        with open(config.TEMP_DATA_FILE, "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    timestamp = datetime.now().isoformat()

    data[user_id] = {
        "text": text,
        "timestamp": timestamp
    }

    with open(config.TEMP_DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)


def read_temp_data(user_id: int):
    """
    Читает временные данные для пользователя.
    """
    try:
        with open(config.TEMP_DATA_FILE, "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    return data.get(str(user_id), None)


def delete_temp_data(user_id: int):
    """
    Удаляет временные данные после подтверждения или отклонения.
    """
    try:
        with open(config.TEMP_DATA_FILE, "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return

    if str(user_id) in data:
        del data[str(user_id)]

    with open(config.TEMP_DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)
