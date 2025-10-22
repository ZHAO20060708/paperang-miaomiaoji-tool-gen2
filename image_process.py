from PIL import Image, ImageDraw, ImageFont
import numpy as np

class ImageConverter:
    def pre_process(im):
        fixed_width = 576
        # Convert to grayscale if needed
        if im.mode != 'L':
            gray = im.convert('L')
        else:
            gray = im
        # Resize to fixed width while maintaining aspect ratio
        ratio = float(fixed_width) / gray.width
        new_height = int(gray.height * ratio)
        new_im = gray.resize((fixed_width, new_height), Image.LANCZOS)
        return new_im

    def frombits(bitmap):
        # chars = []
        #bytes类型
        data = b''
        #将每8个bit合成一个字节放进data
        for b in range(0, len(bitmap), 8):
            data += bytes([int(''.join([str(bitmap[i]) for i in range(b, b + 8)]), 2)])
        return data

    def im2bmp(im):
        im = ImageConverter.pre_process(im)
        # Convert to binary (black and white)
        im_binary = im.point(lambda x: 0 if x < 128 else 255, mode='1')
        
        # Convert to numpy array for easier processing
        img_array = np.array(im_binary)
        height, width = img_array.shape
        
        # Pack bits into bytes
        ret = b''
        byte_data = 0
        
        # Process image data row by row
        for y in range(height):
            for x in range(width):
                byte_data <<= 1
                # Invert: 0 for white, 1 for black
                byte_data |= 0 if img_array[y, x] else 1
                if (y * width + x + 1) % 8 == 0:
                    ret += bytes([byte_data])
                    byte_data = 0

        return ret
    
    def floyd_steinberg_dithering(im):
        """
        使用Floyd-Steinberg算法将彩色图像转换为扩散的黑白图像
        :param im: 输入的PIL图像对象
        :return: 处理后的扩散二值化图像
        """
        # 预处理图像
        im = ImageConverter.pre_process(im)
        
        # 转换为numpy数组进行处理
        img_array = np.array(im, dtype=np.float32)
        height, width = img_array.shape
        
        # Floyd-Steinberg扩散算法
        for y in range(height):
            for x in range(width):
                old_pixel = img_array[y, x]
                new_pixel = 255 if old_pixel > 128 else 0
                img_array[y, x] = new_pixel
                quant_error = old_pixel - new_pixel
                
                # 扩散误差到相邻像素
                if x + 1 < width:
                    img_array[y, x + 1] += quant_error * 7 / 16
                
                if y + 1 < height:
                    if x - 1 >= 0:
                        img_array[y + 1, x - 1] += quant_error * 3 / 16
                    img_array[y + 1, x] += quant_error * 5 / 16
                    if x + 1 < width:
                        img_array[y + 1, x + 1] += quant_error * 1 / 16
        
        # 转换回PIL图像
        # 限制像素值范围在0-255之间
        img_array = np.clip(img_array, 0, 255)
        result_img = Image.fromarray(img_array.astype(np.uint8), mode='L')
        return result_img

    def process_image_for_printing(image_path):
        """
        自动处理图像以适应打印机要求：自动旋转、缩放到合适尺寸，
        应用Floyd-Steinberg扩散算法，并转换为打印机可识别的数据格式
        
        :param image_path: 图像文件路径
        :return: 处理后的二进制打印数据
        """
        # 打开图像
        original_img = Image.open(image_path)
        
        # 自动旋转：比较原始图像的宽高比与旋转90度后的宽高比，选择更适合打印机的 orientation
        # 打印机宽度固定为576像素，所以我们要找到最佳的orientation
        width, height = original_img.size
        ratio_original = float(width) / height
        ratio_rotated = float(height) / width
        
        # 如果原始方向更接近1（正方形），或者更窄（高度大于宽度），则保持原方向
        # 如果旋转后更接近1，或者更适合打印（宽度远大于高度），则旋转
        if ratio_rotated < ratio_original and ratio_original > 1.2 and ratio_original < 2:
            # 旋转90度以获得更好的打印效果
            original_img = original_img.rotate(-90, expand=True)
            
        # 缩放到固定宽度576像素
        resized_img = original_img.resize((576, int(original_img.height * 576 / original_img.width)), Image.LANCZOS)
        
        # 应用Floyd-Steinberg扩散算法
        dithered_img = ImageConverter.floyd_steinberg_dithering(resized_img)
        
        # 转换为打印机可识别的数据格式
        bmp_data = ImageConverter.im2bmp(dithered_img)
        
        return bmp_data

class TextConverter:
    def text2bmp(text, font_size=24):
        # Use a monospace font
        mono_font_candidates = [
            "MapleMono-NF-CN-Light.ttf"
        ]
        
        font = ImageFont.load_default()
        for font_file in mono_font_candidates:
            try:
                font = ImageFont.truetype(font_file, font_size)
                font.set_variation_by_name("WIDTH")
                break
            except:
                continue
        
        # Split text into lines
        lines = []
        for paragraph in text.split('\n'):
            line = ''
            for char in paragraph:
                # Check the width of the line with the new character
                test_line = line + char
                bbox = font.getbbox(test_line)
                if bbox[2] <= 576:
                    line = test_line
                else:
                    # Line is full, start a new line
                    lines.append(line)
                    line = char
            
            # Add the last line if it's not empty
            if line:
                lines.append(line)
        
        # Calculate line height
        line_height = font.getbbox('A')[3]
        
        # Create a blank image with width 576 (printer width) and height based on number of lines
        img = Image.new('L', (576, line_height * len(lines) + 10), 255)  # White background
        draw = ImageDraw.Draw(img)
        
        # Draw text line by line
        y_text = 0
        for line in lines:
            draw.text((0, y_text), line, font=font, fill=0)  # Black text
            y_text += line_height
        
        return ImageConverter.im2bmp(img)