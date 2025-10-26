## Телеграм-бот для генерации изображения

Генерирует изображение на основе шаблона `bot.jpeg`, подставляя сумму и время.

### Стек
- Python 3.10+
- aiogram 3.x
- Pillow

### Файлы
- `main.py` — код бота
- `config.json` — координаты/шрифт/цвета и формат времени
- `requirements.txt` — зависимости
- `bot.jpeg` — базовый шаблон (положите в корень рядом с `main.py`)
- (опционально) `fonts/Roboto-Regular.ttf` — шрифт

### Настройка
1. Поместите файл шаблона `bot.jpeg` в корень проекта `C:\Users\ARM-814\Documents\bot`.
2. При необходимости измените `config.json`:
   - `base_image_path` — путь к шаблону
   - `time_format` — формат парсинга и отображения времени (по умолчанию `%Y/%m/%d %H:%M:%S`)
   - `text.sum` и `text.time` — координаты `x/y`, `font_path`, `font_size`, `fill` (цвет), `anchor`
3. (Опционально) Скопируйте TTF‑шрифт в `fonts/Roboto-Regular.ttf` и укажите его путь в `config.json`. Если шрифт не найден, будет использован дефолтный шрифт Pillow.

### Получение токена бота
1. В Telegram найдите `@BotFather`.
2. Команда `/start`, затем `/newbot` и следуйте инструкциям.
3. Скопируйте токен вида `1234567890:AA...`.

### Установка и запуск (Windows PowerShell)
```powershell
cd C:\Users\ARM-814\Documents\bot
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:BOT_TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER"
python .\main.py
```

### Автозапуск на Windows (один раз и навсегда)
1) Создайте файл токена (одна строка):
```powershell
cd C:\Users\ARM-814\Documents\bot
"1234567890:AA...." | Out-File -Encoding ascii -NoNewline .\BOT_TOKEN.txt
```
2) Установите задачу автозапуска (нужны права администратора):
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
./install_bot_task.ps1 -RunNow
```
После этого бот будет автоматически стартовать при загрузке Windows как служба (через Планировщик заданий). Логи пишутся в файл `bot.log` в корне проекта. Для остановки/удаления автозапуска:
```powershell
./uninstall_bot_task.ps1
```

Альтернативный ручной запуск без PowerShell-окна:
```cmd
run_bot.bat
```

### Деплой на сервер (Linux) — независим от Windows

Вариант A — Docker (рекомендуется)
1) Подготовка:
```bash
cd /путь/к/проекту
cp .env.example .env   # создайте .env и укажите BOT_TOKEN
```
2) Запуск в фоне:
```bash
docker compose up -d --build
```
3) Логи:
```bash
docker logs -f telegram-image-bot
```

Вариант B — systemd (Ubuntu/Debian)
1) Скопируйте проект на сервер, например в `/opt/telegram-image-bot`, создайте там `BOT_TOKEN.txt` (одна строка токена) или экспортируйте переменную окружения `BOT_TOKEN`.
2) Установите зависимости:
```bash
sudo apt update && sudo apt install -y python3-venv
cd /opt/telegram-image-bot
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```
3) Установите сервис:
```bash
sudo cp systemd/telegram-image-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now telegram-image-bot
```
4) Проверка статуса/логов:
```bash
systemctl status telegram-image-bot
journalctl -u telegram-image-bot -f
```

### Использование
- `/start` — помощь
- `/generate` — бот запросит:
  1) сумму (например `320` или `320.50`)
  2) время (строго в формате из `config.json`, по умолчанию `2025/10/16 16:42:14`)
- В ответ бот пришлёт фото с подставленными значениями.

### Валидация и ошибки
- **Сумма**: только число (разделитель `.` или `,`), до 2 знаков после запятой. При ошибке — сообщение: «Введите сумму числом».
- **Время**: проверяется по формату `time_format`. При ошибке — сообщение с ожидаемым форматом и примером.
- Если не найден `bot.jpeg` — бот сообщит об ошибке генерации.

### Кастомизация координат
Поля `text.sum` и `text.time` в `config.json`:
- `x`, `y` — позиция текста на изображении
- `font_path` — путь до TTF (например, `fonts/Roboto-Regular.ttf`)
- `font_size` — размер шрифта
- `fill` — цвет текста в HEX (например, `#000000`)
- `anchor` — якорь выравнивания Pillow (например, `la`, `mm`)

### Примечания
- Выходной формат — `JPEG`. Можно заменить через `output_format` в `config.json`.
- Временный файл удаляется после отправки фотографии пользователю.


