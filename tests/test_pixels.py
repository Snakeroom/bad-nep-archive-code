from placedump.tasks.pixels import get_pixel


def test_pixel_get():
    pixel = get_pixel(69, 420, False)

    assert pixel["x"] == 69
    assert pixel["y"] == 420

    print(pixel)
