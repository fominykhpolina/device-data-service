from fastapi import FastAPI  # Для создания веб-приложения
from pydantic import BaseModel  # Для проверки входящих данных
from datetime import datetime  # Получаем текущее время
import sqlite3  # Встроенная база данных SQLite
import statistics  # Для расчёта статистик

app = FastAPI()

# Подключение к базе данных SQLite (если файла нет — он создается автоматически)
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

# Создаём таблицу для хранения данных
cursor.execute('''
CREATE TABLE IF NOT EXISTS device_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- автоинкремент для уникальности
    device_id TEXT,                        -- ID устройства
    x REAL,                                -- значение по оси X
    y REAL,                                -- значение по оси Y
    z REAL,                                -- значение по оси Z
    timestamp TEXT                         -- время, когда пришли данные
)
''')
conn.commit()  # сохраняем изменения в базе

# Модель для входящих данных
class DeviceData(BaseModel):
    device_id: str  # ID устройства
    x: float        # значение по оси X
    y: float        # значение по оси Y
    z: float        # значение по оси Z

@app.post("/data/")
def save_data(data: DeviceData):
    # Получаем текущее время
    time_now = datetime.utcnow().isoformat()

    # Сохраняем данные в таблицу базы данных
    cursor.execute('''
        INSERT INTO device_data (device_id, x, y, z, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (data.device_id, data.x, data.y, data.z, time_now))
    conn.commit()  # Подтверждаем сохранение

    # Возвращаем сообщение об успешном сохранении данных
    return {"message": "Данные сохранены", "timestamp": time_now}

@app.get("/analysis/{device_id}")
def analyze(device_id: str):
    # Выбираем (достаем) все записи и сразу считаем сумму
    cursor.execute('''
        SELECT x + y + z FROM device_data
        WHERE device_id = ?
    ''', (device_id,))
    values = [row[0] for row in cursor.fetchall()]  # Получаем список всех сумм

    # Если данных нет — получаем сообщение
    if not values:
        return {"message": "Нет данных"}

    # Если данные есть — считаем нужную статистику и возвращаем
    return {
        "min": min(values),                  # минимальное значение
        "max": max(values),                  # максимальное значение
        "count": len(values),                # количество записей
        "sum": sum(values),                  # сумма всех значений
        "median": statistics.median(values)  # медиана
    }