from ImgUtil import ImgUtil

if __name__ == '__main__':
    orig = ImgUtil("picture.png")

    ## Ex 1) Color spaces
    """
    gray_img = orig.grayscale().save("output/grayscale.png")
    binary_img = orig.binary(75).save("output/binary.png")
    negative_img = orig.negative().save("output/negative.png")
    reduced_img = orig.reduce_bit_depth(1).save("output/reduced.png")

    hsl_img = orig.rgb_to_hsl().save("output/rgb_to_hsl.png")
    rgb = ImgUtil("output/rgb_to_hsl.png").hsl_to_rgb().save("output/hsl_to_rgb.png")
    """

    ## Ex 2) Rotations
    """
    img_vertically = orig.flip_vertically().save("output/img_vertically.png")
    img_horizontally = orig.flip_horizontally().save("output/img_horizontally.png")

    img90 = orig.rotate().save("output/rotate90.png")
    img180 = orig.rotate(1).save("output/rotate180.png")
    img270 = orig.rotate(2).save("output/rotate270.png")

    rotated = orig.rotate_on_point(20, (1500, 600))
    rotated2 = orig.rotate_on_point(45, (90, 1000))
    rotated.save('output/rotated_output.png')
    rotated2.save('output/rotated_output2.png')
    """

    ## Ex 3) Scaling
    scaled_x, scaled_y = orig.get_scaled_coordinates(40, 20, 0.75, 0.75)
    print(f"Scaled coordinates: {scaled_x}, {scaled_y}")
    unscaled_x, unscaled_y = orig.get_unscaled_coordinates(30, 15, 0.75, 0.75)
    print(f"Unscaled coordinates: {unscaled_x}, {unscaled_y}")

    scaled_image = orig.scale(0.15, 0.15).save("output/small_scaled_image.png")
    big_image = ImgUtil("output/small_scaled_image.png")
    big_image.scale(15, 15).save("output/big_scaled_image.png")


    scaled_bi = orig.scale_bilinear(0.15, 0.15).save("output/small_bilinear.png")
    big_bi = ImgUtil("output/small_bilinear.png")
    big_bi.scale_bilinear(15, 15).save("output/big_bilinear.png")




