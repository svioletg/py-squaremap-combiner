from pathlib import Path

from PIL import Image, ImageDraw
from tqdm import tqdm


use_tqdm = False

class Combiner:
    """Takes a squaremap `tiles` directory path, handles calculating rows/columns,
    and is able to export full map images.
    """
    TILE_SIZE: int = 512
    """The size of each tile image in pixels.
    Only made a constant in case squaremap happens to change its image sizes in the future.
    """
    def __init__(self, tiles_dir: str | Path):
        if not (tiles_dir := Path(tiles_dir)).is_dir():
            raise NotADirectoryError(f'Not a directory: {tiles_dir}')
        self.tiles_dir = tiles_dir
        self.mapped_worlds: list[str] = [p.stem for p in tiles_dir.glob('minecraft_*/')]

    def combine(self, world: str | Path, detail: int) -> Image.Image:
        """Combine the given world (dimension) tile images into one large map.
        @param world: Name of the world to combine images of.
            Should be the name of a subdirectory located in this instance's `tiles_dir`.
        @param detail: The level of detail, 0 up through 3, to use for this map.
            Will correspond to which numbered subdirectory within the given world to use images from.
        """
        if world not in self.mapped_worlds:
            print(world)
            print(self.mapped_worlds)
            raise ValueError(f'No world directory of name "{world}" exists in "{self.tiles_dir}"')
        if not (0 <= detail <= 3):
            raise ValueError(f'Detail level must be between 0 and 3; given {detail}')
        source_dir: Path = self.tiles_dir / world / str(detail)
        columns: set[int] = set()
        rows: set[int] = set()
        regions: dict[int, dict[int, Path]] = {}

        # Sort out what regions we're going to stitch
        for img in tqdm(source_dir.glob('*_*.png'), disable=not use_tqdm):
            col, row = map(int, img.stem.split('_'))
            if col not in regions:
                columns.add(col)
                regions[col] = {}
            if row not in regions[col]:
                rows.add(row)
                regions[col][row] = img

        # Start stitching
        out = Image.new(mode='RGBA', size=(self.TILE_SIZE * len(columns), self.TILE_SIZE * len(rows)))
        for c in tqdm(regions, disable=not use_tqdm):
            for r in tqdm(regions[c], disable=not use_tqdm, leave=False):
                x, y = self.TILE_SIZE * (c - min(columns)), self.TILE_SIZE * (r - min(rows))
                out.paste(Image.open(regions[c][r]), (x, y, x + self.TILE_SIZE, y + self.TILE_SIZE))

        return out

def quick(tiles_dir) -> None:
    print(Combiner(tiles_dir).combine('minecraft_overworld', 3))

def main():
    pass

if __name__ == '__main__':
    main()
