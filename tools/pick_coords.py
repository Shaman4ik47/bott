import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk


# Путь к картинке рядом со скриптом (в той же папке)
SCRIPT_DIR = Path(__file__).resolve().parent
IMG_PATH = SCRIPT_DIR / "bot.jpeg"

if not IMG_PATH.exists():
    raise FileNotFoundError(f"Файл не найден: {IMG_PATH}")

img = Image.open(IMG_PATH)
w, h = img.size

root = tk.Tk()
root.title("Кликните по картинке — координаты появятся в консоли")

tk_img = ImageTk.PhotoImage(img)
canvas = tk.Canvas(root, width=w, height=h)
canvas.pack()
canvas.create_image(0, 0, anchor="nw", image=tk_img)

status = tk.Label(root, text="")
status.pack()


def on_move(e):
    status.config(text=f"x={e.x}, y={e.y}")
    root.title(f"{e.x}, {e.y}")


def on_click(e):
    print(f"{e.x}, {e.y}")


canvas.bind("<Motion>", on_move)
canvas.bind("<Button-1>", on_click)

root.mainloop()

