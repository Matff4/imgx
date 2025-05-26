from PIL import Image
import math


class ImgUtil:
    def __init__(self, path):
        #
        # pixels[x,y] is (r,g,b)
        #
        self.image = Image.open(path).convert('RGB')
        self.pixels = self.image.load()
        self.width, self.height = self.image.size

    # ===== Private helper methods =====
    def _iterate_pixels(self):
        for y in range(self.height):
            for x in range(self.width):
                yield x, y, self.pixels[x, y]

    def _transform_pixels(self, map_pixel_fn, dst_size=None):
        """
        Returns a new RGB image
        For each destination coordinate (dx, dy):
            1. Call map_pixel_fn(dx, dy, self)
            2. Expect it to return an (r,g,b) tuple
            3. Write that into the new image at (dx, dy)
        """
        dst_w, dst_h = dst_size or (self.width, self.height)
        dst_img = Image.new('RGB', (dst_w, dst_h))
        dst_px = dst_img.load()

        for dy in range(dst_h):
            for dx in range(dst_w):
                # map_pixel_fn returns the color for the destination pixel (dx,dy)
                dst_px[dx, dy] = map_pixel_fn(dx, dy, self)

        return dst_img

    ### ===== Public converting methods =====
    ## Ex 1) Color spaces
    def grayscale(self):
        def to_gray(x, y, util):
            r, g, b = util.pixels[x, y]
            gray = (r + g + b) // 3

            return gray, gray, gray

        return self._transform_pixels(to_gray)

    def binary(self, threshold):
        def to_binary(x, y, util):
            r, g, b = util.pixels[x, y]
            avg = (r + g + b) // 3

            if avg >= threshold:
                return 0xFF, 0xFF, 0xFF
            else:
                return 0x00, 0x00, 0x00

        return self._transform_pixels(to_binary)

    def negative(self):
        def to_negative(x, y, util):
            r, g, b = util.pixels[x, y]
            return 0xFF - r, 0xFF - g, 0xFF - b

        return self._transform_pixels(to_negative)

    def reduce_bit_depth(self, bits_per_channel):
        def to_reduce_bit_depth(x, y, util):
            r, g, b = util.pixels[x, y]

            mask = ((1 << bits_per_channel) - 1) << (8 - bits_per_channel)

            return r & mask, g & mask, b & mask

        return self._transform_pixels(to_reduce_bit_depth)

    def rgb_to_hsl(self):
        def to_hsl(x, y, util):
            r, g, b = util.pixels[x, y]

            r, g, b = r / 255.0, g / 255.0, b / 255.0

            c_max = max(r, g, b)
            c_min = min(r, g, b)
            delta = c_max - c_min

            # L
            l = (c_max + c_min) / 2

            # S
            if delta == 0:
                s = 0
            else:
                s = delta / (1 - abs(2 * l - 1))

            # H
            if delta == 0:
                h = 0
            elif c_max == r:
                h = ((g - b) / delta) % 6
            elif c_max == g:
                h = ((b - r) / delta) + 2
            else:  # c_max == b
                h = ((r - g) / delta) + 4

            h = h * 60

            # Comment in prod - drastically slows down script if image is big
            # print(f"RGB: {util.pixels[x, y]}, HSV:{h}, {s}, {l}")

            # Scale into 0–255 for storage
            h8 = int(round(h / 360 * 255))
            s8 = int(round(s * 255))
            l8 = int(round(l * 255))

            return h8, s8, l8

        return self._transform_pixels(to_hsl)  # HSL image is stored as RGB

    def hsl_to_rgb(self):
        def to_rgb(x, y, util):
            h8, s8, l8 = util.pixels[x, y]

            # Undo scaling
            h = (h8 / 255.0) * 360
            s = s8 / 255.0
            l = l8 / 255.0

            # Calculate chroma, X, and m
            c = (1 - abs(2 * l - 1)) * s
            x_ = c * (1 - abs((h / 60) % 2 - 1))
            m = l - c / 2

            # Determine RGB primes
            if 0 <= h < 60:
                rp, gp, bp = c, x_, 0
            elif 60 <= h < 120:
                rp, gp, bp = x_, c, 0
            elif 120 <= h < 180:
                rp, gp, bp = 0, c, x_
            elif 180 <= h < 240:
                rp, gp, bp = 0, x_, c
            elif 240 <= h < 300:
                rp, gp, bp = x_, 0, c
            else:
                rp, gp, bp = c, 0, x_

            # Convert back to 0–255 range
            r = int(round((rp + m) * 255))
            g = int(round((gp + m) * 255))
            b = int(round((bp + m) * 255))

            return r, g, b

        return self._transform_pixels(to_rgb)

    ## Ex 2) Rotations
    def flip_vertically(self):
        def to_flip(x, y, util):
            flipped_y = util.height - 1 - y

            return util.pixels[x, flipped_y]

        return self._transform_pixels(to_flip)

    def flip_horizontally(self):
        def to_flip(x, y, util):
            flipped_x = util.width - 1 - x

            return util.pixels[flipped_x, y]

        return self._transform_pixels(to_flip)

    def rotate(self, step=0):
        if step in (0, 2):
            dst_size = (self.height, self.width)
        else:  # step == 1
            dst_size = (self.width, self.height)

        def to_rotate(x, y, util):
            w, h = util.width, util.height

            if step == 0:  # 90*
                src_x = w - 1 - y
                src_y = x

            elif step == 1:  # 180*
                src_x = w - 1 - x
                src_y = h - 1 - y

            else:  # step == 2   # 270*
                src_x = y
                src_y = h - 1 - x

            return util.pixels[src_x, src_y]

        return self._transform_pixels(to_rotate, dst_size)

    def rotate_on_point(self, angle, pivot):
        """
        Rotate the image by 'angle' degrees around 'pivot'=(px,py),
        filling empty areas with black, using nearest-neighbor sampling.
        """

        theta = math.radians(angle)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        px, py = pivot

        def to_rotate(dx, dy, util):
            # Map destination pixel to pivot-centered coords
            x_rot = dx - px
            y_rot = dy - py

            # Inverse-rotate back to source-centered coords
            x_rel = x_rot * cos_t + y_rot * sin_t
            y_rel = -x_rot * sin_t + y_rot * cos_t

            # Translate back into original image space
            src_x = int(round(x_rel + px))
            src_y = int(round(y_rel + py))

            # Nearest-neighbor fetch or black
            if 0 <= src_x < self.width and 0 <= src_y < self.height:
                return util.pixels[src_x, src_y]
            else:
                return 0, 255, 0

        return self._transform_pixels(to_rotate)

    ## Ex 3) Scaling
    @staticmethod
    def get_scaled_coordinates(x, y, x_factor, y_factor=None):
        if y_factor is None:
            y_factor = x_factor
        return x * x_factor, y * y_factor

    @staticmethod
    def get_unscaled_coordinates(x_scaled, y_scaled, x_factor, y_factor=None):
        if y_factor is None:
            y_factor = x_factor
        return round(x_scaled / x_factor), round(y_scaled / y_factor)

    def scale(self, x_factor, y_factor=None):
        """
        Resize the image by (x_factor, y_factor) using nearest‐neighbor sampling.
        """
        if y_factor is None:
            y_factor = x_factor

        # Compute destination size
        dst_w = round(self.width * x_factor)
        dst_h = round(self.height * y_factor)

        def to_scale(dx, dy, util):
            # Map the destination pixel back to source coords
            src_x, src_y = ImgUtil.get_unscaled_coordinates(dx, dy, x_factor, y_factor)

            # Nearest‐neighbor: fetch pixel if in bounds, else black
            if 0 <= src_x < self.width and 0 <= src_y < self.height:
                return util.pixels[src_x, src_y]
            else:
                return 0, 0, 0

        return self._transform_pixels(to_scale, dst_size=(dst_w, dst_h))

    def scale_bilinear(self, x_factor, y_factor=None):
        """
        Resize the image by (x_factor, y_factor) using bilinear interpolation.
        If y_factor is None, uses x_factor for both dimensions.
        """
        if y_factor is None:
            y_factor = x_factor

        # Compute output dimensions
        dst_w = round(self.width * x_factor)
        dst_h = round(self.height * y_factor)

        def to_bilinear(dx, dy, util):
            # 1) Map destination to exact source float coords
            src_xf = dx / x_factor
            src_yf = dy / y_factor

            # 2) Identify the 4 surrounding pixel indices
            x0 = math.floor(src_xf)
            y0 = math.floor(src_yf)
            x1 = x0 + 1
            y1 = y0 + 1

            # 3) Compute the fractional part
            wx = src_xf - x0
            wy = src_yf - y0

            # 4) Fetch the four neighbours, clamping at borders
            def clamp(v, max_v):
                return max(0, min(v, max_v))

            x0c = clamp(x0, self.width - 1)
            x1c = clamp(x1, self.width - 1)
            y0c = clamp(y0, self.height - 1)
            y1c = clamp(y1, self.height - 1)

            p00 = util.pixels[x0c, y0c]
            p10 = util.pixels[x1c, y0c]
            p01 = util.pixels[x0c, y1c]
            p11 = util.pixels[x1c, y1c]

            # 5) Compute weights
            w00 = (1 - wx) * (1 - wy)
            w10 = wx * (1 - wy)
            w01 = (1 - wx) * wy
            w11 = wx * wy

            # 6) Blend each channel
            r = round(p00[0] * w00 + p10[0] * w10 + p01[0] * w01 + p11[0] * w11)
            g = round(p00[1] * w00 + p10[1] * w10 + p01[1] * w01 + p11[1] * w11)
            b = round(p00[2] * w00 + p10[2] * w10 + p01[2] * w01 + p11[2] * w11)

            return (r, g, b)

        return self._transform_pixels(to_bilinear, dst_size=(dst_w, dst_h))
