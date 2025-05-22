import time
import threading
from collections import defaultdict
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
import json

BOT_TOKEN = "7666419947:AAGWZCnOENQnGmu0mqo2BsoMeLlI28mkpGQ"
WEBAPP_URL = "https://testol222.vercel.app/"
CANVAS_SIZE = 20
COOLDOWN_SECONDS = 5

canvas = defaultdict(lambda: "#FFFFFF")
user_last_action = {}
connected_clients = []

# Загрузка и сохранение состояния холста в файл
def load_canvas():
    try:
        with open('canvas_state.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return defaultdict(lambda: "#FFFFFF")

def save_canvas():
    with open('canvas_state.json', 'w') as f:
        json.dump(canvas, f)

canvas = load_canvas()  # Загружаем состояние холста при запуске сервера

# --- Telegram handlers ---

def render_canvas_text():
    text = "\n".join([ 
        "".join(["⬛" if canvas[f"{x}_{y}"] != "#FFFFFF" else "⬜" for x in range(CANVAS_SIZE)]) 
        for y in range(CANVAS_SIZE)
    ])
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        KeyboardButton(
            "🚀 Открыть Pixel Canvas",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Привет! Нажми кнопку, чтобы открыть веб-приложение с холстом.",
        reply_markup=reply_markup
    )
    await update.message.reply_text(render_canvas_text())

async def handle_pixel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    now = time.time()

    if user_id in user_last_action and now - user_last_action[user_id] < COOLDOWN_SECONDS:
        remaining = int(COOLDOWN_SECONDS - (now - user_last_action[user_id]))
        await update.message.reply_text(f"Подожди {remaining} сек перед следующим пикселем ⏳")
        return

    try:
        parts = text.split()
        x, y = int(parts[0]), int(parts[1])
        color = parts[2].upper()
        if not (0 <= x < CANVAS_SIZE and 0 <= y < CANVAS_SIZE):
            raise ValueError("Координаты вне холста")
        if not color.startswith("#") or len(color) != 7:
            raise ValueError("Неверный формат цвета")
        canvas[f"{x}_{y}"] = color
        user_last_action[user_id] = now
        save_canvas()  # Сохраняем обновленное состояние холста
        await update.message.reply_text("✅ Пиксель установлен")
        await update.message.reply_text(render_canvas_text())
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")

# --- FastAPI app ---

app = FastAPI()

@app.get("/canvas")
async def get_canvas():
    return {"canvas": dict(canvas), "size": CANVAS_SIZE}

@app.post("/place")
async def place_pixel(data: dict):
    x = data.get("x")
    y = data.get("y")
    color = data.get("color", "#FFFFFF").upper()
    if not (0 <= x < CANVAS_SIZE and 0 <= y < CANVAS_SIZE):
        raise HTTPException(status_code=400, detail="Координаты вне холста")
    if not color.startswith("#") or len(color) != 7:
        raise HTTPException(status_code=400, detail="Неверный формат цвета")
    canvas[f"{x}_{y}"] = color
    save_canvas()  # Сохраняем обновленное состояние холста
    # Отправляем обновления всем подключенным клиентам
    for client in connected_clients:
        await client.send_json({"canvas": dict(canvas), "size": CANVAS_SIZE})
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Присоединяем нового клиента
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        # Отправляем начальное состояние холста при подключении
        await websocket.send_json({"canvas": dict(canvas), "size": CANVAS_SIZE})

        # Ожидаем сообщений от клиента (например, когда он рисует)
        while True:
            data = await websocket.receive_json()
            x, y, color = data["x"], data["y"], data["color"]
            # Обновляем холст
            if 0 <= x < CANVAS_SIZE and 0 <= y < CANVAS_SIZE:
                canvas[f"{x}_{y}"] = color
                save_canvas()
                # Отправляем обновления всем клиентам
                for client in connected_clients:
                    await client.send_json({"canvas": dict(canvas), "size": CANVAS_SIZE})

    except WebSocketDisconnect:
        # Убираем клиента из списка при отключении
        connected_clients.remove(websocket)

@app.get("/", response_class=HTMLResponse)
async def main_page():
    return """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>Pixel Canvas</title>
<style>
  body {
    background-color: #222;
    display: flex;
    flex-direction: column;
    align-items: center;
    font-family: Arial, sans-serif;
    color: white;
  }
  #canvas {
    margin-top: 20px;
    display: grid;
    grid-gap: 1px;
    background: #444;
  }
  .pixel {
    width: 20px;
    height: 20px;
    border-radius: 2px;
    cursor: pointer;
  }
  #colorPicker {
    margin-top: 15px;
    width: 120px;
    height: 35px;
    border: none;
    cursor: pointer;
  }
  #status {
    margin-top: 10px;
    height: 20px;
  }
</style>
</head>
<body>
<h1>Pixel Canvas</h1>
<input type="color" id="colorPicker" value="#FF0000" />
<div id="status"></div>
<div id="canvas"></div>

<script>
  const canvasDiv = document.getElementById('canvas');
  const colorPicker = document.getElementById('colorPicker');
  const status = document.getElementById('status');
  const COOLDOWN = 5000; // 5 секунд
  let lastClickTime = 0;
  let canvasSize = 20;

  const socket = new WebSocket("ws://localhost:8000/ws");

  socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    const { canvas, size } = data;
    canvasSize = size;
    createCanvas(canvasSize, canvas);
  };

  function createCanvas(size, canvas) {
    canvasDiv.style.gridTemplateColumns = `repeat(${size}, 20px)`;
    canvasDiv.style.gridTemplateRows = `repeat(${size}, 20px)`;
    canvasDiv.innerHTML = '';
    for(let y=0; y<size; y++) {
      for(let x=0; x<size; x++) {
        const div = document.createElement('div');
        div.className = 'pixel';
        div.dataset.x = x;
        div.dataset.y = y;
        div.style.backgroundColor = canvas[`${x}_${y}`] || '#FFFFFF';
        div.addEventListener('click', onPixelClick);
        canvasDiv.appendChild(div);
      }
    }
  }

  async function onPixelClick(e) {
    const now = Date.now();
    if(now - lastClickTime < COOLDOWN) {
      const wait = ((COOLDOWN - (now - lastClickTime))/1000).toFixed(1);
      status.textContent = `Подожди ещё ${wait} секунд`;
      return;
    }
    status.textContent = '';
    const pixel = e.target;
    const x = parseInt(pixel.dataset.x);
    const y = parseInt(pixel.dataset.y);
    const color = colorPicker.value.toUpperCase();
    
    // Отправляем данные через WebSocket
    socket.send(JSON.stringify({ x, y, color }));
    lastClickTime = now;
    status.textContent = 'Пиксель установлен!';
  }
</script>
</body>
</html>
    """

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000)

def main():
    threading.Thread(target=run_fastapi, daemon=True).start()

    telegram_app = Application.builder().token(BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_pixel))

    print("Бот запущен...")
    telegram_app.run_polling()

if __name__ == "__main__":
    main()
