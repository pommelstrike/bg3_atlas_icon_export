# bg3_atlas_icon_export
ExportIcons.jsx
ExportIcons.jsx is an Adobe Photoshop script designed to streamline the export process for image assets. This script automates exporting a high-resolution image (1000x1000px) as well as scaled-down versions at 380x380px, 144x144px, and 64x64px. It is ideal for game developers, UI designers, and artists creating assets for projects requiring multiple sizes.

Features
Original Export: Exports the full-resolution (1000x1000px) image to the Original folder.
Scalable Exports:
380x380px (38%)
144x144px (14.4%)
64x64px (6.4%)
Organized Output: Automatically organizes exports into the following folders:
Original
GUI/380x380 Tooltip PNG
GUI/144x144 ControllerUI PNG
GUI/64x64 PNG
Color Profile Conversion: Ensures all exports are in sRGB IEC61966-2.1 color space.
Resample Quality: Uses Preserve Details resampling for high-quality scaling.
Installation
Save the ExportIcons.jsx file to your computer.
Copy the script to Photoshop’s Scripts folder:
Windows: C:\Program Files\Adobe\Adobe Photoshop 2023\Presets\Scripts
Mac: /Applications/Adobe Photoshop 2023/Presets/Scripts
Restart Photoshop to load the script.
Alternatively, you can run the script from any location:

Open Photoshop.
Go to File > Scripts > Browse.
Locate and select the ExportIcons.jsx file.
Usage
Open a Photoshop document.
Run the script:
From the menu: File > Scripts > ExportIcons.
Or use File > Scripts > Browse to locate the script.
Follow the prompts:
Select an export folder.
Enter a base file name (e.g., icon_base).
The script will:
Export the original (1000x1000px) image to the Original folder.
Scale and export smaller versions into their respective folders.
Output Example
If your base file name is icon_base and you export to C:\Assets, the following structure will be created:

mathematica
Copy code
C:\Assets\
│
├── Original\
│   └── icon_base.png
│
├── GUI\
│   ├── 380x380 Tooltip PNG\
│   │   └── icon_base.png
│   │
│   ├── 144x144 ControllerUI PNG\
│   │   └── icon_base.png
│   │
│   └── 64x64 PNG\
│       └── icon_base.png
Requirements
Adobe Photoshop: The script is tested with Photoshop 2023 but should work with earlier versions.
JavaScript Engine: ExtendScript support is required.
Troubleshooting
Error: Need Administrator Privileges:
If copying the script to Program Files fails, run Photoshop as Administrator or use the Browse feature.
Scaling Issues:
Ensure the source image is at least 1000x1000px for optimal results.
Color Profile Issues:
The script attempts to convert color profiles to sRGB IEC61966-2.1. If conversion fails, ensure your Photoshop installation supports the profile.
Contributing
Feel free to fork this repository and submit pull requests for improvements or additional features.

License
This script is released under the MIT License.

Author
Developed by pommelstrike. Contributions and feedback are welcome!

Notes:
Replace LICENSE with the appropriate license file link if the script is under MIT or another license.
Update the Author section if you'd like to include additional details or contact links.
Let me know if you need further customization!
