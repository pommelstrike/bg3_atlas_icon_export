
# pommelstrike's ATLAS Icon Stage Tool

This tool automates the process of resizing and exporting UI asset icons for Baldur's Gate 3 mod projects. Designed with a user-friendly GUI and night mode, it simplifies managing and generating project assets efficiently.

---

## Features
- Resizes images to pre-defined formats for UI assets:
  - **Original (1000x1000)**, **380x380 Tooltip PNG**, **144x144 ControllerUI PNG**, **64x64 PNG**
- Outputs project-specific folders for organization.
- Supports bulk processing of multiple PNG files.
- Includes a modern GUI with a **night mode theme**.
- Displays the export location upon successful processing.

---

## Requirements
- Python >= 3.10
- Required Python Libraries:
  - `Pillow`
  - `tqdm`
  - `tkinter` (comes pre-installed with Python)

Install the required libraries with:
```bash
pip install Pillow tqdm
```

---

## Usage
### Interactive GUI
1. Launch the tool:
   ```bash
   python bg3_icons_GUI.py
   ```
2. **Select Input Path**: Browse to a folder containing PNG files or a single PNG file.
3. **Specify Output Path**: Choose the directory where the processed project folders will be generated.
4. **Enter Project Name**: Provide a name for the project.
5. Click **Start Processing** to begin.

---

## GUI Overview
- **Input Path**: Select a PNG file or directory with 1000x1000 PNG files.
- **Output Path**: Choose the folder where your project assets will be saved.
- **Project Name**: Enter the project name; the tool organizes files into project-specific folders.

---

## Success Message
After processing, the tool displays:
```
Batch export complete!

Project UI Assets Icons are located in:
[Path to output folder]
```

---

## Development
### Code Features
- Built with Python and **Tkinter** for the GUI.
- Night mode theme with customizable colors.
- Dynamic success messages with export paths.

### Contributing
Pull requests are welcome! For major changes, please open an issue first to discuss your ideas.

---

## License
This project is open-source and licensed under the MIT License.

---

## Links
- **GitHub Repository**: [GitHub](https://github.com/pommelstrike/bg3_atlas_icon_export)
- **BG3 Mod.io Page**: [Mod.io](https://mod.io/g/baldursgate3/u/pommelstrike/r)
