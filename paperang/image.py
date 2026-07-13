"""Image processing: dithering, thresholding, QR code generation for Paperang 2."""

from PIL import Image
import numpy as np
import qrcode


class ImageConverter:
    """Converts images into bitmap data suitable for the Paperang 2 printer."""

    current_mode = "auto"

    @staticmethod
    def pre_process(im):
        fixed_width = 576
        if im.mode != 'L':
            gray = im.convert('L')
        else:
            gray = im
        ratio = float(fixed_width) / gray.width
        new_height = int(gray.height * ratio)
        new_im = gray.resize((fixed_width, new_height), Image.LANCZOS)
        return new_im

    @staticmethod
    def frombits(bitmap):
        data = b''
        for b in range(0, len(bitmap), 8):
            data += bytes([int(''.join([str(bitmap[i]) for i in range(b, b + 8)]), 2)])
        return data

    @staticmethod
    def im2bmp(im):
        im_binary = im.point(lambda x: 0 if x < 128 else 255, mode='1')
        img_array = np.array(im_binary)
        height, width = img_array.shape

        ret = b''
        byte_data = 0

        for y in range(height):
            for x in range(width):
                byte_data <<= 1
                byte_data |= 0 if img_array[y, x] else 1
                if (y * width + x + 1) % 8 == 0:
                    ret += bytes([byte_data])
                    byte_data = 0

        return ret

    @staticmethod
    def floyd_steinberg_dithering(im):
        """Apply Floyd-Steinberg error-diffusion dithering to a grayscale image."""
        img_array = np.array(im, dtype=np.float32)
        height, width = img_array.shape

        for y in range(height):
            for x in range(width):
                old_pixel = img_array[y, x]
                new_pixel = 255 if old_pixel > 128 else 0
                img_array[y, x] = new_pixel
                quant_error = old_pixel - new_pixel

                if x + 1 < width:
                    img_array[y, x + 1] += quant_error * 7 / 16

                if y + 1 < height:
                    if x - 1 >= 0:
                        img_array[y + 1, x - 1] += quant_error * 3 / 16
                    img_array[y + 1, x] += quant_error * 5 / 16
                    if x + 1 < width:
                        img_array[y + 1, x + 1] += quant_error * 1 / 16

        img_array = np.clip(img_array, 0, 255)
        result_img = Image.fromarray(img_array.astype(np.uint8), mode='L')
        return result_img

    @staticmethod
    def adaptive_threshold(im):
        """Apply local adaptive threshold binarization."""
        img_array = np.array(im)
        window_size = 15
        half_window = window_size // 2

        padded_img = np.pad(img_array, ((half_window, half_window), (half_window, half_window)), mode='reflect')
        output = np.zeros_like(img_array)
        height, width = img_array.shape

        for y in range(height):
            for x in range(width):
                local_region = padded_img[y:y + window_size, x:x + window_size]
                local_mean = np.mean(local_region)
                threshold = local_mean - 5
                output[y, x] = 0 if img_array[y, x] < threshold else 255

        return Image.fromarray(output.astype(np.uint8), mode='L')

    @staticmethod
    def count_black_pixels(im):
        """Count black pixels in a binary image."""
        binary_img = im.point(lambda x: 0 if x < 128 else 255, mode='1')
        img_array = np.array(binary_img)
        return np.sum(img_array == 0)

    @staticmethod
    def process_image_for_printing_with_mode(image_path, mode="auto", no_rotate=False):
        """Process an image file for printing with the given mode.

        Args:
            image_path: Path to the image file.
            mode: One of "floyd" ("f"), "adaptive" ("a"), or "auto".
            no_rotate: If True, skip automatic rotation.

        Returns:
            Binary print data ready to send to the printer.
        """
        original_img = Image.open(image_path)

        # Auto-rotate: pick the orientation that fits the 576px width better
        if not no_rotate:
            width, height = original_img.size
            ratio_original = float(width) / height
            ratio_rotated = float(height) / width

            if ratio_rotated < ratio_original and ratio_original > 1.2 and ratio_original < 2:
                original_img = original_img.rotate(-90, expand=True)

        if original_img.width > 576:
            resized_img = original_img.resize(
                (576, int(original_img.height * 576 / original_img.width)), Image.LANCZOS
            )
            resized_img = resized_img.convert('L')
        else:
            resized_img = Image.new("L", (576, original_img.height), 255)
            paste_x = (576 - original_img.width) // 2
            resized_img.paste(original_img, (paste_x, 0))

        if mode in ("floyd", "f"):
            processed_img = ImageConverter.floyd_steinberg_dithering(resized_img)
        elif mode in ("adaptive", "a"):
            processed_img = ImageConverter.adaptive_threshold(resized_img)
        else:
            processed_img = ImageConverter.floyd_steinberg_dithering(resized_img)

        bmp_data = ImageConverter.im2bmp(processed_img)
        return bmp_data

    @staticmethod
    def process_image_for_printing(image_path):
        """Auto-mode image processing (backward-compatible)."""
        return ImageConverter.process_image_for_printing_with_mode(image_path, "auto")

    @staticmethod
    def generate_qr_code(qr_string):
        """Generate a QR code and convert to print-ready bitmap data.

        Args:
            qr_string: Text to encode in the QR code.

        Returns:
            Binary print data.
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=4,
            border=4,
        )
        qr.add_data(qr_string)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img = qr_img.convert('1')

        qr_width, qr_height = qr_img.size
        if qr_width > 576:
            raise ValueError("二维码太大无法打印")
        elif qr_width != 576:
            new_img = Image.new("1", (576, qr_height), 255)
            paste_x = (576 - qr_width) // 2
            new_img.paste(qr_img, (paste_x, 0))
            img_data = ImageConverter.im2bmp(new_img)
        else:
            img_data = ImageConverter.im2bmp(qr_img)

        return img_data
