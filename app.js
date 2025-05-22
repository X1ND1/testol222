const canvas = document.getElementById('canvas');
const colorsContainer = document.getElementById('colors');
const cooldownText = document.getElementById('cooldown');
const SIZE = 50;
const COOLDOWN = 5; // секунд

const COLORS = [
  '#FFFFFF',
  '#FF0000',
  '#00FF00',
  '#0000FF',
  '#FFFF00',
  '#FFA500',
  '#800080',
  '#000000'
];

let selectedColor = COLORS[1];
let lastClickTime = 0;

// Подключаемся к серверу через WebSocket
const socket = new WebSocket("ws://localhost:8000/ws");

socket.onmessage = function(event) {
  const data = JSON.parse(event.data);
  const { canvas: updatedCanvas, size } = data;
  createCanvas(size, updatedCanvas);
};

// Создаем кнопки выбора цвета
for (let color of COLORS) {
  const btn = document.createElement('div');
  btn.className = 'color-btn';
  btn.style.backgroundColor = color;
  if (color === selectedColor) btn.classList.add('selected');
  btn.addEventListener('click', () => {
    selectedColor = color;
    document.querySelectorAll('.color-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
  });
  colorsContainer.appendChild(btn);
}

// Создаем сетку пикселей
function createCanvas(size, updatedCanvas) {
  canvas.innerHTML = ''; // Очищаем старую сетку

  for (let i = 0; i < size * size; i++) {
    const pixel = document.createElement('div');
    pixel.className = 'pixel';
    pixel.dataset.index = i;
    pixel.style.backgroundColor = updatedCanvas[i] || COLORS[0];

    pixel.addEventListener('click', () => {
      const now = Date.now();
      if (now - lastClickTime < COOLDOWN * 1000) {
        const secondsLeft = ((COOLDOWN * 1000 - (now - lastClickTime)) / 1000).toFixed(1);
        cooldownText.textContent = `Подожди еще ${secondsLeft} секунд перед следующим пикселем ⏳`;
        return;
      }
      cooldownText.textContent = '';
      pixel.style.backgroundColor = selectedColor;
      lastClickTime = now;

      // Отправляем данные на сервер через WebSocket
      socket.send(JSON.stringify({ x: i % size, y: Math.floor(i / size), color: selectedColor }));
    });

    canvas.appendChild(pixel);
  }
}

// Загружаем состояние холста при подключении
socket.addEventListener('open', () => {
  socket.send('get_canvas');
});
