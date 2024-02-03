from PIL import Image, ImageDraw, ImageFont
import requests

from src._utils.logger import create_logger
from src._utils.common import ROOT_DIR

_log = create_logger("Systray Utils")


HEIGHT_MOD = -4
CIRCLE_SIZE_MOD = 1


def _load_font(relative_path: str, size: int = 100):
    path = ROOT_DIR + relative_path
    return ImageFont.truetype(path, size)


def draw_icon_text(text: str, color: str, font_path: str = r"res/ArialBold.ttf"):
    font = _load_font(font_path)
    width, height = (100, 100)
    image = Image.new("RGB", (width, height), 0)
    image = image.convert("RGBA")
    image.putalpha(0)
    draw = ImageDraw.Draw(image)
    left, top, right, bottom = draw.textbbox(xy=(0, 0), text=text, font=font)
    position = ((width - right) / 2, (height - bottom + HEIGHT_MOD) / 2)
    draw.text(position, text=text, font=font, align="center", fill=color)

    return image


def draw_icon_circle(color: str):
    width, height = (100, 100)
    image = Image.new("RGB", (width, height), 0)
    image = image.convert("RGBA")
    image.putalpha(0)
    draw = ImageDraw.Draw(image)
    draw.ellipse((0, 0, width * CIRCLE_SIZE_MOD, height * CIRCLE_SIZE_MOD), fill=color)

    return image


def trigger_webhook(url: str):
    try:
        requests.post(url)
    except Exception as e:
        _log.warning(f"Error sending webhook {url}: [{e}]")
