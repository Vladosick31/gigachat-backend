# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from gigachat import GigaChat
from gigachat.models import Chat, Messages
import os
from base64 import b64encode

app = FastAPI()

# === Переменные окружения ===
GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID")
GIGACHAT_CLIENT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET")

if not GIGACHAT_CLIENT_ID or not GIGACHAT_CLIENT_SECRET:
    raise RuntimeError("Не хватает GIGACHAT credentials")

# Кодируем логин:пароль
def encode_credentials(client_id: str, client_secret: str) -> str:
    credentials = f"{client_id}:{client_secret}"
    return b64encode(credentials.encode()).decode()

AUTH_DATA = encode_credentials(GIGACHAT_CLIENT_ID, GIGACHAT_CLIENT_SECRET)

# Клиент GigaChat
gigachat_client = GigaChat(
    credentials=AUTH_DATA,
    scope="GIGACHAT_API_PERS",
    verify_ssl_certs=False,
    timeout=30
)

# Хранение истории (временно в памяти)
user_history = {}

class MessageRequest(BaseModel):
    message: str
    user_id: int

@app.post("/api/chat")
async def chat_endpoint(req: MessageRequest):
    user_id = req.user_id
    user_msg = req.message

    # Получаем историю
    history = user_history.get(user_id, [])
    history.append(Messages(role="user", content=user_msg))
    history = history[-10:]  # ограничиваем

    # Добавляем system prompt
    if not any(m.role == "system" for m in history):
        history.insert(0, Messages(role="system", content="Отвечай кратко и полезно."))

    try:
        chat = Chat(messages=history)
        response = await gigachat_client.achat(chat)
        bot_reply = response.choices[0].message.content

        # Сохраняем ответ
        history.append(Messages(role="assistant", content=bot_reply))
        user_history[user_id] = history

        return {"response": bot_reply}
    except Exception as e:
        return {"response": f"Ошибка: {str(e)}"}