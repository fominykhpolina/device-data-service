from fastapi import FastAPI, Query  # FastAPI для API, Query для параметров в URL
from pydantic import BaseModel  # Для проверки данных, которые приходят в запросах
from datetime import datetime  # Для работы со временем
from typing import Optional, List  # Для необязательных параметров и списков
import sqlite3  # Встроенная база данных
import statistics  # Для расчёта статистик

# Создаём экземпляр приложения FastAPI
app = FastAPI()

# Подключаемся к базе данных SQLite (если файла нет — он создаётся)
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

# Создаём таблицу для хранения данных от устройств
cursor.execute('''
CREATE TABLE IF NOT EXISTS device_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT,
    x REAL,
    y REAL,
    z REAL,
    timestamp TEXT
)
''')

# Создаём таблицу для связи пользователей с устройствами
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    device_id TEXT
)
''')

# Сохраняем изменения в базе
conn.commit()

# Модель данных, которые приходят от устройств
class DeviceData(BaseModel):
    device_id: str
    x: float
    y: float
    z: float

# Эндпоинт: Принимает данные от устройства и сохраняет их в базу данных
@app.post("/data/")
def save_data(data: DeviceData):
    time_now = datetime.utcnow().isoformat()  # Текущее время
    cursor.execute('''
        INSERT INTO device_data (device_id, x, y, z, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (data.device_id, data.x, data.y, data.z, time_now))
    conn.commit()
    return {"message": "Данные сохранены", "timestamp": time_now}

# Эндпоинт: Возвращает аналитику по одному устройству
@app.get("/analysis/{device_id}")
def analyze(
    device_id: str,
    start: Optional[str] = Query(None, description="Дата начала (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="Дата конца (YYYY-MM-DD)")
):
    # Строим SQL-запрос с фильтрацией по дате
    query = "SELECT x + y + z FROM device_data WHERE device_id = ?"
    params = [device_id]

    if start:
        query += " AND timestamp >= ?"
        params.append(start)
    if end:
        query += " AND timestamp <= ?"
        params.append(end)

    cursor.execute(query, tuple(params))
    values = [row[0] for row in cursor.fetchall()]  # Суммируем x + y + z

    if not values:
        return {"message": "Нет данных"}

    # Возвращаем статистику
    return {
        "min": min(values),
        "max": max(values),
        "count": len(values),
        "sum": sum(values),
        "median": statistics.median(values)
    }

# Эндпоинт: Возвращает список всех уникальных устройств в базе
@app.get("/devices")
def get_all_devices():
    cursor.execute("SELECT DISTINCT device_id FROM device_data")
    rows = cursor.fetchall()
    devices = [row[0] for row in rows]
    return devices

# Модель для регистрации пользователя с его устройствами
class UserRegistration(BaseModel):
    user_id: str
    device_ids: List[str]

# Эндпоинт: Регистрирует пользователя и его устройства
@app.post("/users")
def register_user(data: UserRegistration):
    for device_id in data.device_ids:
        cursor.execute('''
            INSERT INTO user_devices (user_id, device_id)
            VALUES (?, ?)
        ''', (data.user_id, device_id))
    conn.commit()
    return {"message": f"Пользователь {data.user_id} добавлен с {len(data.device_ids)} устройствами."}

# Эндпоинт: Возвращает аналитику по всем устройствам, зарегистрированным на пользователя
@app.get("/user-analysis/{user_id}")
def analyze_user(user_id: str):
    # Получаем все устройства пользователя
    cursor.execute("SELECT device_id FROM user_devices WHERE user_id = ?", (user_id,))
    devices = [row[0] for row in cursor.fetchall()]

    if not devices:
        return {"message": "У пользователя нет устройств"}

    results = {}
    for device_id in devices:
        # Для каждого устройства собираем данные и считаем статистику
        cursor.execute("SELECT x + y + z FROM device_data WHERE device_id = ?", (device_id,))
        values = [row[0] for row in cursor.fetchall()]
        if values:
            results[device_id] = {
                "min": min(values),
                "max": max(values),
                "count": len(values),
                "sum": sum(values),
                "median": statistics.median(values)
            }

    if not results:
        return {"message": "Нет данных ни по одному устройству"}

    return results