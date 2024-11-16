
# ExportIcons.jsx Script for Adobe Photoshop 2020+

## Overview

`BG3_ExportIcons` is a Photoshop JSX script designed to streamline the export of icons for the 3 resolutions need to make a BG3 UI icons in modkit. The script exports the "original" 1000x1000px image and scaled-down versions for `380x380px`, `144x144px`, and `64x64px` resolutions needed for Tooltip and Controller UIs and Automatically organizes exported images into distinct folders.

## Guide
- Visit my guide on mod.io for details

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
   - Alternatively, save it in a location of your choice and load it manually (see "Usage").

2. Restart Photoshop to load the script into the `File > Scripts` menu.

## Usage
1. Open a Photoshop document you want to export. The .PSD needs to be in 1000x1000 
2. Run the script:
   - **Menu**: Go to `File > Scripts > BG3_ExportIcons`.
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
1. Run PowerShell as Administrator. 
2. Use PowerShell to copy the file: (Update command line to your version of Photoshop, Adobe Photoshop 2023 is used in this example)
   ```powershell
   Copy-Item -Path "BG3_ExportIcons.jsx" -Destination "C:\Program Files\Adobe\Adobe Photoshop 2023\Presets\Scripts" -Force
   ```

### Blurry Images
Ensure the original document resolution & canva (1000x1000) is set appropriately before running the script.

## License
This script is provided as-is under the MIT License. See `LICENSE` for details.
