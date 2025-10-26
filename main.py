import asyncio
import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.types.input_file import FSInputFile

from PIL import Image, ImageDraw, ImageFont
import PIL


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"


@dataclass
class RectSpec:
    x: int
    y: int
    w: int
    h: int
    fill: str = "#FFFFFF"


@dataclass
class TextSpec:
    x: int
    y: int
    font_path: Optional[str]
    font_size: int
    fill: str
    anchor: str = "la"
    erase_rect: Optional[RectSpec] = None
    bold: bool = False
    bold_offset: int = 1


@dataclass
class AppConfig:
    base_image_path: Path
    output_format: str
    time_format: str
    sum_text: TextSpec
    time_text: TextSpec


def load_config(path: Path = CONFIG_PATH) -> AppConfig:
    with path.open("r", encoding="utf-8") as f:
        raw: Dict[str, Any] = json.load(f)

    text = raw.get("text", {})
    sum_cfg = text.get("sum", {})
    time_cfg = text.get("time", {})

    return AppConfig(
        base_image_path=(APP_DIR / raw.get("base_image_path", "bot.jpeg")).resolve(),
        output_format=raw.get("output_format", "JPEG"),
        time_format=raw.get("time_format", "%Y/%m/%d %H:%M:%S"),
        sum_text=TextSpec(
            x=int(sum_cfg.get("x", 200)),
            y=int(sum_cfg.get("y", 300)),
            font_path=sum_cfg.get("font_path"),
            font_size=int(sum_cfg.get("font_size", 48)),
            fill=sum_cfg.get("fill", "#000000"),
            anchor=sum_cfg.get("anchor", "la"),
            erase_rect=(
                RectSpec(
                    x=int(sum_cfg["erase_rect"]["x"]),
                    y=int(sum_cfg["erase_rect"]["y"]),
                    w=int(sum_cfg["erase_rect"]["w"]),
                    h=int(sum_cfg["erase_rect"]["h"]),
                    fill=sum_cfg["erase_rect"].get("fill", "#FFFFFF"),
                )
                if isinstance(sum_cfg.get("erase_rect"), dict)
                else None
            ),
            bold=bool(sum_cfg.get("bold", False)),
            bold_offset=int(sum_cfg.get("bold_offset", 1)),
        ),
        time_text=TextSpec(
            x=int(time_cfg.get("x", 200)),
            y=int(time_cfg.get("y", 380)),
            font_path=time_cfg.get("font_path"),
            font_size=int(time_cfg.get("font_size", 36)),
            fill=time_cfg.get("fill", "#333333"),
            anchor=time_cfg.get("anchor", "la"),
            erase_rect=(
                RectSpec(
                    x=int(time_cfg["erase_rect"]["x"]),
                    y=int(time_cfg["erase_rect"]["y"]),
                    w=int(time_cfg["erase_rect"]["w"]),
                    h=int(time_cfg["erase_rect"]["h"]),
                    fill=time_cfg["erase_rect"].get("fill", "#FFFFFF"),
                )
                if isinstance(time_cfg.get("erase_rect"), dict)
                else None
            ),
        ),
    )


class RenderError(Exception):
    pass


class ImageRenderer:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def _load_font(self, font_path: Optional[str], font_size: int) -> ImageFont.FreeTypeFont:
        # 1) Try configured TTF path (relative or absolute)
        if font_path:
            abs_path = (APP_DIR / font_path).resolve() if not Path(font_path).is_absolute() else Path(font_path)
            if abs_path.exists():
                try:
                    return ImageFont.truetype(str(abs_path), font_size)
                except Exception:
                    logging.warning("Failed to load font at %s", abs_path)

        # 2) Try common Windows fonts
        try:
            win_dir = Path(os.environ.get("WINDIR", "C:/Windows"))
            fonts_dir = win_dir / "Fonts"
            candidates: List[str] = [
                "segoeui.ttf",
                "arial.ttf",
                "tahoma.ttf",
                "calibri.ttf",
                "verdana.ttf",
            ]
            for name in candidates:
                cand = fonts_dir / name
                if cand.exists():
                    return ImageFont.truetype(str(cand), font_size)
        except Exception:
            pass

        # 3) Try Pillow-bundled DejaVu
        try:
            dejavu_path = Path(PIL.__file__).resolve().parent / "DejaVuSans.ttf"
            if dejavu_path.exists():
                return ImageFont.truetype(str(dejavu_path), font_size)
        except Exception:
            pass

        # 4) Last resort (bitmap; size may not scale)
        logging.warning("Falling back to ImageFont.load_default(); text size may not scale")
        return ImageFont.load_default()

    def render(self, amount_text: str, time_text: str) -> Path:
        if not self.config.base_image_path.exists():
            raise RenderError(f"Base image not found at: {self.config.base_image_path}")

        with Image.open(self.config.base_image_path).convert("RGB") as base_img:
            draw = ImageDraw.Draw(base_img)

            sum_font = self._load_font(self.config.sum_text.font_path, self.config.sum_text.font_size)
            time_font = self._load_font(self.config.time_text.font_path, self.config.time_text.font_size)

            # Amount
            if self.config.sum_text.erase_rect is not None:
                r = self.config.sum_text.erase_rect
                draw.rectangle([(r.x, r.y), (r.x + r.w, r.y + r.h)], fill=r.fill)
            if self.config.sum_text.bold:
                o = max(1, int(self.config.sum_text.bold_offset))
                x0, y0 = self.config.sum_text.x, self.config.sum_text.y
                for dx, dy in ((-o, 0), (o, 0), (0, -o), (0, o)):
                    draw.text((x0 + dx, y0 + dy), amount_text, font=sum_font, fill=self.config.sum_text.fill, anchor=self.config.sum_text.anchor)
                draw.text((x0, y0), amount_text, font=sum_font, fill=self.config.sum_text.fill, anchor=self.config.sum_text.anchor)
            else:
                draw.text(
                    (self.config.sum_text.x, self.config.sum_text.y),
                    amount_text,
                    font=sum_font,
                    fill=self.config.sum_text.fill,
                    anchor=self.config.sum_text.anchor,
                )

            # Time
            if self.config.time_text.erase_rect is not None:
                r = self.config.time_text.erase_rect
                draw.rectangle([(r.x, r.y), (r.x + r.w, r.y + r.h)], fill=r.fill)
            draw.text(
                (self.config.time_text.x, self.config.time_text.y),
                time_text,
                font=time_font,
                fill=self.config.time_text.fill,
                anchor=self.config.time_text.anchor,
            )

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp_path = Path(tmp.name)
            tmp.close()
            try:
                base_img.save(tmp_path, format=self.config.output_format)
            except Exception as e:
                # Clean up on failure
                try:
                    tmp_path.unlink(missing_ok=True)
                finally:
                    raise RenderError(str(e))

        return tmp_path


def normalize_amount(text: str) -> Optional[str]:
    # Keep user's decimal separator and digits; allow optional +/- sign
    raw = (text or "").strip().replace(" ", "")
    if not re.fullmatch(r"[+-]?\d+(?:[\.,]\d{1,2})?", raw):
        return None

    sign = ""
    if raw and raw[0] in "+-":
        sign = raw[0]
        num = raw[1:]
    else:
        num = raw

    # Decide if decimal is present and which separator is used
    if "," in num and "." in num:
        return None  # mixed separators not allowed

    if "," in num:
        int_part, frac_part = num.split(",", 1)
        display = int_part + "," + frac_part  # keep as typed
    elif "." in num:
        int_part, frac_part = num.split(".", 1)
        display = int_part + "." + frac_part
    else:
        # Integer input: return as integer without .00
        display = str(int(num))

    return (sign + display) if sign == "-" else display


def parse_time(text: str, time_format: str) -> Optional[datetime]:
    try:
        return datetime.strptime(text.strip(), time_format)
    except Exception:
        return None


def format_amount_display(amount_str: str) -> str:
    # amount_str is normalized like "320.00" or "-15.50"
    if amount_str.startswith("-"):
        return f"- {amount_str.lstrip('-')}"
    return f"+ {amount_str}"


class Form(StatesGroup):
    waiting_for_sum = State()
    waiting_for_time = State()


router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Привет! Я сгенерирую скриншот на основе шаблона.\n"
        "Команды:\n"
        "/generate — запустить генерацию\n"
        "/cancel — отменить"
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Ок, отменено. Нажмите /generate чтобы начать заново.")


@router.message(Command("generate"))
async def cmd_generate(message: Message, state: FSMContext) -> None:
    await state.set_state(Form.waiting_for_sum)
    await message.answer("Введите сумму числом (например: 320 или 320.50)")


@router.message(Form.waiting_for_sum)
async def process_sum(message: Message, state: FSMContext) -> None:
    normalized = normalize_amount(message.text or "")
    if not normalized:
        await message.answer("Введите сумму числом. Пример: 320 или 320.50")
        return

    await state.update_data(amount=normalized)
    await state.set_state(Form.waiting_for_time)

    # Show expected format from config
    cfg = load_config()
    await message.answer(
        "Введите время в формате: " + cfg.time_format + "\n"
        "Например: 2025/10/16 16:42:14"
    )


@router.message(Form.waiting_for_time)
async def process_time(message: Message, state: FSMContext) -> None:
    cfg = load_config()
    dt = parse_time(message.text or "", cfg.time_format)
    if not dt:
        await message.answer(
            "Неверный формат времени. Ожидается: " + cfg.time_format + "\n"
            "Например: 2025/10/16 16:42:14"
        )
        return

    data = await state.get_data()
    amount = data.get("amount")
    if not amount:
        await state.clear()
        await message.answer("Произошла ошибка состояния, начните заново: /generate")
        return

    # Render and send
    renderer = ImageRenderer(cfg)
    try:
        display_amount = format_amount_display(amount)
        result_path = renderer.render(amount_text=display_amount, time_text=dt.strftime(cfg.time_format))
    except RenderError as e:
        logging.exception("Render failed")
        await message.answer(f"Ошибка генерации изображения: {e}")
        await state.clear()
        return

    try:
        photo = FSInputFile(str(result_path))
        await message.answer_photo(photo=photo, caption="Готово")
    finally:
        try:
            result_path.unlink(missing_ok=True)
        except Exception:
            logging.warning("Failed to delete temp file: %s", result_path)

    await state.clear()


def read_token() -> str:
    """Return bot token from env BOT_TOKEN or BOT_TOKEN.txt (first non-empty line)."""
    token_env = os.environ.get("BOT_TOKEN", "").strip()
    if token_env:
        return token_env

    token_file = APP_DIR / "BOT_TOKEN.txt"
    if token_file.exists():
        try:
            with token_file.open("r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception:
            pass
    return ""


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    token = read_token()
    if not token:
        raise RuntimeError("BOT_TOKEN is not set. Set environment variable BOT_TOKEN or create BOT_TOKEN.txt with your bot token.")

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    logging.info("Bot started")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass

