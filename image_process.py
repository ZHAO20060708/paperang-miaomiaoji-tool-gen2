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
            
        # 应用Floyd-Steinberg扩散算法
        dithered_img = ImageConverter.floyd_steinberg_dithering(original_img)
        
        # 转换为打印机可识别的数据格式
        bmp_data = ImageConverter.im2bmp(dithered_img)
        
        return bmp_data

class TextConverter:
    def text2bmp(text, height=25, font_path=None, font_size=24):
        # Create a blank image with width 576 (printer width)
        img = Image.new('L', (576, height), 255)  # White background
        draw = ImageDraw.Draw(img)
        
        # Try to use a better font if available
        try:
            if font_path:
                font = ImageFont.truetype(font_path, font_size)
            else:
                # Try to find a system font that supports Chinese
                font_candidates = [
                    "HarmonyOS_Sans_SC_Regular.ttf"
                ]
                font = None
                for font_file in font_candidates:
                    try:
                        font = ImageFont.truetype(font_file, font_size)
                        break
                    except:
                        continue
                if font is None:
                    font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # Draw text
        draw.text((0, 0), text, font=font, fill=0)  # Black text
        return ImageConverter.im2bmp(img)
