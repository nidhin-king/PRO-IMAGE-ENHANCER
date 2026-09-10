import numpy as np

from app.tiling import blend_tiles, iter_tiles


def test_tile_grid_covers_full_image_without_gaps():
    height, width = 50, 40
    tiles = list(iter_tiles(width=width, height=height, tile_size=16, overlap=4))
    covered = np.zeros((height, width), dtype=np.uint8)
    for tile in tiles:
        covered[tile.y0 : tile.y1, tile.x0 : tile.x1] = 1
    assert int(covered.sum()) == height * width
    assert tiles[0].y0 == 0 and tiles[0].x0 == 0
    assert any(t.y1 == height for t in tiles)
    assert any(t.x1 == width for t in tiles)


def test_tiles_keep_original_spatial_order():
    tiles = list(iter_tiles(width=30, height=40, tile_size=10, overlap=2))
    coords = [(t.y0, t.x0) for t in tiles]
    assert coords == sorted(coords)


def test_overlap_blend_reconstructs_exact_canvas_for_identity():
    src = np.arange(20 * 12 * 3, dtype=np.uint8).reshape(20, 12, 3)

    def identity(tile):
        return tile.copy()

    canvas = blend_tiles(source=src, scale=1, tile_size=8, overlap=2, infer_fn=identity)
    np.testing.assert_array_equal(canvas, src)


def test_4x_tile_output_size_is_exact():
    src = np.zeros((15, 11, 3), dtype=np.uint8)
    src[0, 0] = [255, 0, 0]
    src[-1, -1] = [0, 255, 0]

    def nearest_4x(tile):
        return np.repeat(np.repeat(tile, 4, axis=0), 4, axis=1)

    canvas = blend_tiles(source=src, scale=4, tile_size=8, overlap=2, infer_fn=nearest_4x)
    assert canvas.shape == (60, 44, 3)
    np.testing.assert_array_equal(canvas[0:4, 0:4, 0], 255)
    np.testing.assert_array_equal(canvas[-4:, -4:, 1], 255)
