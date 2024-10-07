# py-squaremap-combiner

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)

Python script written to combine the images generated by the [squaremap](https://modrinth.com/plugin/squaremap) Minecraft plugin. Not affiliated with squaremap or its authors.

The seed used for the world the sample images were created from is `-2590089827693666277`.

## Usage

The script can either be directly run...

```bash
python3 squaremap_combine.py my-tiles overworld 2 --output_ext jpg
```

...or installed as a package (`pip install git+https://github.com/svioletg/py-squaremap-combiner.git`), then either imported...

```python
import squaremap_combine.squaremap_combine as sq

combiner = Combiner('my-tiles')
map_image = combiner.combine('minecraft_overworld', 2)
map_image.save('output.jpg')
```

...or run via the `-m` switch as its own command.

```bash
python3 -m squaremap_combine my-tiles overworld 2 --output_ext jpg
```

Use the `-h` or `--help` argument to see full arguments and their defaults.

Installing this repository as a package is only a convenience feature. If you don't want to install it, this package only really contains a single script, so you can download it and use it on its own, provided you have the required packages installed. The script can be found in this repository at `src/squaremap_combine/squaremap_combine.py`.

To find squaremap's tiles, go to the folder your server JAR is in, and then navigate to `plugins/squaremap/web`. Inside, there will be a `tiles` folder which likely contains folders like `minecraft_overworld`, `minecraft_the_nether`, and `minecraft_the_end`. You will supply the path to this `tiles` folder for the script to work, and then specify a "world" (dimension) to use the tiles of, which will be one of the three aformentioned subfolders - the `minecraft_` prefix can be omitted when entering them, but you should not alter the folder names themselves.

After these two, specify what detail level to use, any number from 0 through 3. Level 3 is the highest detail and thus will result in the largest image, while 0 is the lowest detail and results in the smallest.

| Detail | Description |
|---|---|
| 3 | 1 block per pixel |
| 2 | 2x2 block area per pixel |
| 1 | 4x4 block area per pixel |
| 0 | 8x8 block area per pixel |

This is all you need to create a basic full-map image. Your command might look something like this:

```bash
python3 squaremap_combine.py server-tiles overworld 3
```

Note that very large maps can of course easily result in very large images, and it may take a while for the full image to be completed.

Beyond this, there are various options that can be given to the script to alter its behavior. If you're not familiar with using the command-line, these options are typed out after the main command, in any order, with their associated values following directly after, like `squaremap_combine.py tiles overworld 3 --option value --option-two value`. If any of the options below are not used, their **default** is used automatically.

> Note: You can use either hyphens (`-`) or underscores (`_`) and the option will work the same, e.g. `--output-ext` or `--output_ext`

| Option | Description | Default |
|-|-|-|
| `--output-dir` or `-o` | Specifies a folder to save the completed image to. | `.` (The directory the script was run from.) |
| `--output-ext` or `-ext` | What file extension/format to give the resulting image. `png`, `jpg`, `webp`, etc. | `png` |
| `--timestamp` or `-t` | Adds a timestamp to the beginning of the image's filename, in the given format — see [strftime.org](https://strftime.org/) for a formatting code cheat sheet, however note that you'll need to use question marks (`?`) rather than percent symbols for the codes in this case. Using the argument alone without any string given after it will use automatically use the default format, which is `?Y-?m-?d_?H-?M-?S` (e.g. `2024-06-06_07-41-00`). | Timestamp is omitted if this option is unused. |
| `--overwrite` or `-ow` | Flag that allows the script to overwrite any image with the same name as the one it wants to save to. The script saves images in the format `world_name-detail.(extension)` (e.g. `minecraft_overworld-3.png`), so if a file with this name already exists in the targeted output directory, it will be overwritten with this option. | Not using this flag will result in a number being added to the filename before saving, based on how many copies with the same name exist already. |
| `--area` or `-a` | Specifies a specific area to export an image of, rather than the full map. This option expects coordinates as they would appear in the Minecraft world itself, as the top-left and bottom-right corners of a rectangle — in the order of `X1 Y1 X2 Y2`. | The full map is rendered if no area is specified. |
| `--no-autotrim` | Tells the script not to trim off any empty (as in, fully transparent) space around the created image. | |
| `--force-size` or `-fs` | Centers the image within the given width and height, in that order, and then crops the image to that size before saving. If only one number is given, it will be used for both the width and height. | |
| `--use-grid` or `-g` | Adds a grid onto the final image in the given X and Y intervals. If only X_INTERVAL is given, the same interval will be used for both X and Y grid lines. The resulting grid will be based on the coordinates as they would be in Minecraft, not of the image itself. | No grid is added. |
| `--show-coords` or `-gc` | Adds coordinate text to every grid interval intersection. Requires the use of the --use-grid option. | No coordinates are shown. |
| `--coords-format` or `-gcf` | A string to format how grid coordinates appear. Use "{x}" and "{y}" (curly-braces included) where you want the X and Y coordinates to appear, e.g. "X: {x} Y: {y}" could appear as "X: 100 Y: 200". | `({x}, {y})` |
| `--background` or `-bg` | Specify an RGBA color (with values from 0 to 255 for each) to use for the background of the image. A hexcode (e.g. FF0000) can be used as well, and an 8-character hex code can be used to specify alpha with the last two bytes. If only RED, GREEN, and BLUE are given, the alpha is set to 255 (fully opaque) automatically. | Background is fully transparent. |
| `--yes-to-all` or `-y` | Automatically skips and approves any prompts for user confirmation. This is useful if you intend to run this script automatically, like in a crontab. | |

Using some of these options, your command may look something like this:

```bash
python3 squaremap_combine.py tiles overworld 3 --area -700 -500 100 200 --timestamp default --output-dir town-area --output-ext jpg -y
```
