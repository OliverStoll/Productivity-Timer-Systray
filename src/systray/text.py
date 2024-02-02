import textwrap
import string

MAX_MAIL_LINE_LEN = 100


def split_text_into_lines(text):
    # keep the newlines while using textwrap to split the text into lines
    lines = []
    for line in text.splitlines():
        lines.extend(textwrap.wrap(line, width=MAX_MAIL_LINE_LEN))
    return lines


def unicode_style(text, style: str = "italic"):
    unicode_tuples = {"bold_serif": (0x1D400, 0x1D433), "italic_serif": (0x1D434, 0x1D467), "bold_italic_serif": (0x1D468, 0x1D467),
                      "script": (0x1D49C, 0x1D4CF), "bold_script": (0x1D4D0, 0x1D4E9), "fraktur": (0x1D504, 0x1D537),
                      "bold_fraktur": (0x1D56C, 0x1D59F), "double_struck": (0x1D538, 0x1D56B),
                      "normal": (0x1D5A0, 0x1D5D3), "bold": (0x1D5D4, 0x1D607),
                      "italic": (0x1D608, 0x1D63B), "bold_italic": (0x1D63C, 0x1D66F),
                      "monospace": (0x1D670, 0x1D6A3)}
    mat_b_letters = ''.join([chr(x) for x in range(unicode_tuples[style][0], unicode_tuples[style][1] + 1)])
    ascii_letters = string.ascii_uppercase + string.ascii_lowercase
    translation_table = ascii_letters.maketrans(ascii_letters, mat_b_letters)
    return text.translate(translation_table)