
# ExportIcons.jsx Script

## Overview

`ExportIcons.jsx` is a Photoshop script designed to streamline the export of icons for various resolutions. The script starts by exporting a 1000x1000 pixel "original" image and then creates scaled-down versions for `380x380px`, `144x144px`, and `64x64px` resolutions. This script is particularly useful for game developers or designers who need consistent icon sizes.

## Features
- Exports an "original" image at 1000x1000 pixels.
- Scales the original to:
  - `380x380px` (38% of original size).
  - `144x144px` (14.4% of original size).
  - `64x64px` (6.4% of original size).
- Automatically organizes exported images into distinct folders:
  - `Original`
  - `GUI/380x380 Tooltip PNG`
  - `GUI/144x144 ControllerUI PNG`
  - `GUI/64x64 PNG`
- Converts images to the sRGB color space with profile embedding.
- Excludes metadata for optimized export.

## Installation
1. Place the `ExportIcons.jsx` file in the Photoshop Scripts folder:
   - **Windows**: `C:\Program Files\Adobe\Adobe Photoshop 2023\Presets\Scripts`
   - **Mac**: `/Applications/Adobe Photoshop 2023/Presets/Scripts`
   - Alternatively, save it in a location of your choice and load it manually (see "Usage").

2. Restart Photoshop to load the script into the `File > Scripts` menu.

## Usage
1. Open a Photoshop document you want to export.
2. Run the script:
   - **Menu**: Go to `File > Scripts > ExportIcons`.
   - **Browse**: Alternatively, select `File > Scripts > Browse` and locate the script file.
3. Follow the prompts:
   - Select an export folder.
   - Enter the base file name (e.g., `icon_base`).
4. The script will create the following structure:
   ```
   Export Folder/
   ├── Original/
   │   └── icon_base.png
   ├── GUI/
       ├── 380x380 Tooltip PNG/
       │   └── icon_base.png
       ├── 144x144 ControllerUI PNG/
       │   └── icon_base.png
       └── 64x64 PNG/
           └── icon_base.png
   ```

## Dependencies
- Photoshop CC 2020 or later.
- Tested on Adobe Photoshop 2023.

## Troubleshooting
### "Need Administrator Privileges" Error
If you're unable to copy the script to the Photoshop Scripts folder:
1. Run Photoshop as Administrator.
2. Use PowerShell to copy the file:
   ```powershell
   Copy-Item -Path "C:\Path\To\ExportIcons.jsx" -Destination "C:\Program Files\Adobe\Adobe Photoshop 2023\Presets\Scripts" -Force
   ```

### Blurry Images
Ensure the original document resolution is set appropriately before running the script.

## License
This script is provided as-is under the MIT License. See `LICENSE` for details.
