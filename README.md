# ItemSetExport.jsx Script for Adobe Photoshop 2020+

## Overview

`ItemSetExport.jsx` (also known as pommelstrike's ATLAS Item Set Icon Export Tool) is a Photoshop JSX script designed to automate the export of icons with predefined layer styles in multiple sizes for Baldur's Gate 3 modding, game development, or UI design. The script applies four layer styles (`item_blue`, `item_purple`, `item_green`, `item_gold`) to the active layer and exports each variant in 1000x1000, 380x380, 144x144, and 64x64 resolutions. It organizes exported PNGs into distinct folders, converts to sRGB color space, embeds the profile, and excludes metadata for optimization.

## Guide
- For a detailed tutorial on setup and usage, see the [Tutorial Markdown](Photoshop%20Item%20Set%20Export%20Script%20Tutorial.markdown) in this repository.
- Visit my guide on mod.io for additional details: https://mod.io/g/baldursgate3/r/pommelstrikes-atlas-icons-photoshop-addon
- For integrating exported icons into Baldur's Gate 3 mods, refer to the [Adding Skill and Item Icons guide](https://mod.io/g/baldursgate3/r/adding-skill-and-item-icons). Key instructional snippets include:

  - "This guide describes how to create a new texture atlas, and add new icons for skills and/or items."
  - "## Adding New Skill or Item Icons The process is almost identical for adding both skill and item icons."
  - "### Adding the 64x64 Icon In the Editor, open the Texture Atlas Editor from the main toolbar. Open an atlas (or create a new one following the steps above)."
  - Requires icons in multiple resolutions, such as 380x380 for tooltips, matching the export sizes provided by this script.
  - Place exported files in your mod's folder structure, e.g., `\Data\Mods\YourMod\GUI\Assets\` for appropriate subfolders.

## Features
- Applies four layer styles: `item_blue`, `item_purple`, `item_green`, `item_gold`.
- Exports each styled icon in four sizes/formats:
  - Original (1000x1000 px)
  - GUI/380x380 Tooltip PNG (38% scale)
  - GUI/144x144 ControllerUI PNG (14.4% scale)
  - GUI/64x64 PNG (6.4% scale)
- Automatically creates folder structure in the selected export path:
  ```
  Export Folder/
  ├── Original/
  │   ├── baseName_blue.png
  │   ├── baseName_purple.png
  │   ├── baseName_green.png
  │   └── baseName_gold.png
  ├── GUI/
      ├── 380x380 Tooltip PNG/
      │   ├── baseName_blue.png
      │   ├── baseName_purple.png
      │   ├── baseName_green.png
      │   └── baseName_gold.png
      ├── 144x144 ControllerUI PNG/
      │   ├── baseName_blue.png
      │   ├── baseName_purple.png
      │   ├── baseName_green.png
      │   └── baseName_gold.png
      └── 64x64 PNG/
          ├── baseName_blue.png
          ├── baseName_purple.png
          ├── baseName_green.png
          └── baseName_gold.png
  ```
- Saves PNGs with sRGB color profile, no interlacing.
- Version: 1.5.0

## Installation
1. Download `ItemSetExport.jsx` from the [latest release](https://github.com/pommelstrike/bg3_atlas_icon_export/releases).
2. Place the script in Photoshop’s Scripts folder:
   - **Windows**: `C:\Program Files\Adobe\Adobe Photoshop [Version]\Presets\Scripts\`
   - **Mac**: `/Applications/Adobe Photoshop [Version]/Presets/Scripts/`
3. Restart Photoshop to load the script into the `File > Scripts` menu. Alternatively, run it directly via `File > Scripts > Browse`.

## Usage
1. Open a PSD file (canvas at least 1000x1000 px) and select the active layer containing the icon.
2. Ensure layer styles (`item_blue`, `item_purple`, `item_green`, `item_gold`) are available in the Styles panel.
3. Run the script:
   - Via menu: `File > Scripts > ItemSetExport`
   - Or browse to the script file.
4. Follow prompts:
   - Select an export folder.
   - Enter a base file name (e.g., `icon_base` – avoid spaces/special characters).
5. The script applies styles, exports files, and displays a completion alert. Check the JavaScript console for logs.
6. Integrate the exported PNGs into your BG3 mod as per the [Adding Skill and Item Icons guide](https://mod.io/g/baldursgate3/r/adding-skill-and-item-icons), using tools like the Texture Atlas Editor for the 64x64 icons.

## Integrating Exported Icons into BG3 Mods

After exporting your icons using the script, follow these detailed steps to integrate them into your Baldur's Gate 3 mod. These steps are based on the official modding guide and assume you have the Baldur's Gate 3 Editor (Toolkit) installed, a mod project created in the Resources tab, and your PNG assets organized. Note that the script exports multiple color variants (_blue, _purple, _green, _gold), which are suitable for item icons with different rarities or styles. Ensure all variants for a set use identical base names across resolutions to avoid errors.

### Prerequisites for Integration
- Baldur's Gate 3 Editor installed and a mod package created.
- Exported PNGs from the script: Use the 64x64 for hotbar/atlas, 144x144 for ControllerUI, 380x380 for tooltips. The 1000x1000 original can be kept as a source file.
- Store PNGs in `/Data/Public/[modname]/GUI/` (recommended for source assets).
- Identical file names across resolutions (e.g., `icon_base_blue.png` for all sizes).

### Step 1: Create a New Texture Atlas (for 64x64 Icons)
1. Open the Texture Atlas Editor from the main toolbar in the BG3 Editor.
2. Create a new atlas via `File > New`.
3. In the dialog:
   - Set file paths for .lsx and .dds (rename for clarity, e.g., `MyItemIcons.lsx`).
   - Icon size: 64x64.
   - Texture size: 512x512 (for up to 64 icons) or 1024x1024 (for up to 256 icons).
   - Enable square icons; disable custom.
   - Select your mod package.
4. Save the atlas.

### Step 2: Add 64x64 Icons to the Atlas (Hotbar Display)
1. Open your atlas in the Texture Atlas Editor.
2. Click **Add Entries** and select your 64x64 PNGs (e.g., from `GUI/64x64 PNG/` folder).
3. If an "icon ID already exists" error appears, rename your PNG to avoid conflicts.
4. Save the atlas. This generates .dds and .lsx files in `/Data/Public/[modname]/Assets/Textures/Icons/` and `/Data/Public/[modname]/GUI/`.

### Step 3: Add 144x144 ControllerUI Icons
1. Go to **Project > Convert UI Assets…** in the Editor.
2. Add your 144x144 PNGs (e.g., from `GUI/144x144 ControllerUI PNG/`).
3. Select your mod and set output subfolder:
   - For items: `ControllerUIIcons/items_png`.
4. Click OK to convert to DDS. Files will be in `/Data/Mods/[modname]/GUI/Assets/ControllerUIIcons/items_png/` and low-res variant.

### Step 4: Add 380x380 Tooltip Icons
1. Open **Convert UI Assets** again.
2. Add your 380x380 PNGs (e.g., from `GUI/380x380 Tooltip PNG/`).
3. Set output subfolder:
   - For items: `Tooltips/ItemIcons`.
4. Convert to DDS. Files will be in `/Data/Mods/[modname]/GUI/Assets/Tooltips/ItemIcons/` and low-res variant.

### Step 5: Hook Up Icons in the Mod
- For items: In the Root Templates Manager, set the **Item > Icon** property to the icon filename (e.g., `icon_base_blue`).
- Ensure names match exactly without extensions.

### Step 6: Test in Game
1. Load a test level (e.g., Basic_Level_A) in Game Mode.
2. Use console commands like `addDebugSpell %name%` for skills or equivalent for items.
3. Restart the Editor if icons don't appear.

### Troubleshooting Integration
- Icons not showing: Restart the Editor.
- Dark icons: Adjust PNG color profile (e.g., to sRGB) and reconvert.
- File errors: Ensure identical names across all PNG sizes.
- DLL errors: Install Visual C++ Redistributable.
- Avoid reusing game icon names.

For full details, consult the [Adding Skill and Item Icons guide](https://mod.io/g/baldursgate3/r/adding-skill-and-item-icons).

## Dependencies
- Adobe Photoshop CC 2020 or later (tested on 2023).
- Layer styles (`item_blue`, `item_purple`, `item_green`, `item_gold`) must be predefined in the PSD or Styles panel.

## Troubleshooting
- **Script not in menu**: Confirm placement in Scripts folder and restart Photoshop.
- **Failed to apply style**: Verify style names match exactly and are available.
- **No document open**: Open a PSD before running.
- **Incorrect/missing exports**: Ensure active layer is visible; canvas supports scaling (1000x1000+ px recommended).
- **Color issues**: Script converts to sRGB; check PSD color profile if problems persist.
- **Admin privileges needed**: Run PowerShell as admin to copy (e.g., `Copy-Item -Path "ItemSetExport.jsx" -Destination "C:\Program Files\Adobe\Adobe Photoshop 2023\Presets\Scripts" -Force`).

## License
This script is provided as-is under the MIT License. See `LICENSE` for details.
