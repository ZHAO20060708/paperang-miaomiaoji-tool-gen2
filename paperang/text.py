"""Text-to-bitmap conversion for Paperang 2 printing."""

import os
from PIL import Image, ImageDraw, ImageFont

from paperang.image import ImageConverter


class TextConverter:
    """Converts text into bitmap data suitable for the Paperang 2 printer."""

    @staticmethod
    def text2bmp(text, font_size=24):
        """Render text to a 576px-wide bitmap and convert to printer data.

        Args:
            text: The text string to print (supports \\n for newlines).
            font_size: Font size in points (8-72 recommended).

        Returns:
            Binary print data.
        """
        # Look for bundled font, fall back to PIL default
        font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
        mono_font_candidates = [
            os.path.join(font_dir, "MapleMono-NF-CN-Light.ttf"),
            "MapleMono-NF-CN-Light.ttf",  # fallback: cwd
        ]

        font = ImageFont.load_default()
        for font_file in mono_font_candidates:
            try:
                font = ImageFont.truetype(font_file, font_size)
                font.set_variation_by_name("WIDTH")
                break
            except Exception:
                continue

        # Word-wrap text into lines fitting 576px
        lines = []
        for paragraph in text.split('\n'):
            line = ''
            for char in paragraph:
                test_line = line + char
                bbox = font.getbbox(test_line)
                if bbox[2] <= 576:
                    line = test_line
                else:
                    lines.append(line)
                    line = char
            if line:
                lines.append(line)

        line_height = font.getbbox('A')[3]

        img = Image.new('L', (576, line_height * len(lines) + 10), 255)
        draw = ImageDraw.Draw(img)

        y_text = 0
        for line in lines:
            draw.text((0, y_text), line, font=font, fill=0)
            y_text += line_height

        return ImageConverter.im2bmp(img)
