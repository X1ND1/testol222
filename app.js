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

// Загружаем сохранённые пиксели из localStorage
let savedPixels = JSON.parse(localStorage.getItem('pixels')) || {};
console.log(savedPixels); // Отладочный вывод

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
for (let i = 0; i < SIZE * SIZE; i++) {
  const pixel = document.createElement('div');
  pixel.className = 'pixel';
  pixel.dataset.index = i;
  pixel.style.backgroundColor = savedPixels[i] || COLORS[0];

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
    savedPixels[i] = selectedColor;
    localStorage.setItem('pixels', JSON.stringify(savedPixels)); // Сохраняем изменения в localStorage
  });

  canvas.appendChild(pixel);
}
