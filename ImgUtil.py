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
        Build a new RGB image of size dst_size (or same as source).
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
            gray = (r + g + b) // 3

            if gray >= threshold:
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
        expanding the canvas to fit the full rotated content and filling
        empty areas with black using nearest-neighbor sampling.
        """

        # Precompute trig
        theta = math.radians(angle)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        # Original image dimensions and pivot
        w, h = self.width, self.height
        px, py = pivot

        # Compute positions of corners relative to pivot
        corners = [
            (-px, -py),
            (w - px, -py),
            (-px, h - py),
            (w - px, h - py)
        ]

        # Rotate corners to find extents
        xs = []
        ys = []
        for x_rel, y_rel in corners:
            x_rot = x_rel * cos_t - y_rel * sin_t
            y_rot = x_rel * sin_t + y_rel * cos_t
            xs.append(x_rot)
            ys.append(y_rot)

        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)

        # New canvas size
        new_w = int(math.ceil(max_x - min_x))
        new_h = int(math.ceil(max_y - min_y))

        # Offsets to map dst coords into rotated space
        x_off = -min_x
        y_off = -min_y

        def to_rotate(dx, dy, util):
            # Map dst pixel to rotated coordinates (relative to pivot)
            x_rot = dx - x_off
            y_rot = dy - y_off

            # Inverse rotation to get original relative coords
            x_rel = x_rot * cos_t + y_rot * sin_t
            y_rel = -x_rot * sin_t + y_rot * cos_t

            # Map back to original image coords
            src_x = int(round(x_rel + px))
            src_y = int(round(y_rel + py))

            # Fetch pixel or black
            if 0 <= src_x < w and 0 <= src_y < h:
                return util.pixels[src_x, src_y]
            else:
                return (0, 0, 0)

        return self._transform_pixels(to_rotate, (new_w, new_h))
