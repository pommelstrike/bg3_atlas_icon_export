import argparse
import shutil
import os
import sys
import json
import subprocess
import uuid
import logging
import atexit
import glob
import urllib.request
import zipfile
import tempfile
import math
from datetime import datetime
from xml.dom.minidom import parseString, Document
from xml.parsers.expat import ExpatError
from PIL import Image, ImageOps
import numpy as np
import colorama
from colorama import Fore, Style
colorama.init(autoreset=True)

def download_texconv(dest_dir=None):
    if dest_dir is None:
        dest_dir = os.path.join(os.path.dirname(__file__), 'texconv')
    os.makedirs(dest_dir, exist_ok=True)
    TEXCONV_URL = 'https://github.com/microsoft/DirectXTex/releases/download/dec2024/texconv.exe'
    texconv_path = os.path.join(dest_dir, 'texconv.exe')
    print(Fore.CYAN + f'[TEXCONV] Downloading from Microsoft DirectXTex...')
    print(Fore.GREEN + f'[DEBUG] Download URL: {TEXCONV_URL}')
    print(Fore.GREEN + f'[DEBUG] Destination: {texconv_path}')
    try:
        print(Fore.YELLOW + '[TEXCONV] Downloading... (this may take a minute)')
        urllib.request.urlretrieve(TEXCONV_URL, texconv_path)
        if os.path.exists(texconv_path):
            file_size = os.path.getsize(texconv_path) / 1024 / 1024
            print(Fore.GREEN + f'✓ Downloaded texconv.exe ({file_size:.2f} MB)')
            print(Fore.GREEN + f'✓ Saved to: {texconv_path}')
            return texconv_path
        else:
            print(Fore.RED + '[ERROR] Download completed but file not found')
            return None
    except Exception as e:
        print(Fore.RED + f'[ERROR] Failed to download texconv.exe: {e}')
        print(Fore.YELLOW + '[INFO] You can manually download from:')
        print(Fore.YELLOW + '       https://github.com/microsoft/DirectXTex/releases')
        return None

def find_texconv(prefs_path=None):
    if prefs_path and os.path.isfile(prefs_path):
        print(Fore.GREEN + f'[TEXCONV] Found in preferences: {prefs_path}')
        return prefs_path
    script_dir = os.path.dirname(__file__)
    local_texconv = os.path.join(script_dir, 'texconv', 'texconv.exe')
    if os.path.isfile(local_texconv):
        print(Fore.GREEN + f'[TEXCONV] Found in script directory: {local_texconv}')
        return local_texconv
    system_texconv = shutil.which('texconv')
    if system_texconv:
        print(Fore.GREEN + f'[TEXCONV] Found in system PATH: {system_texconv}')
        return system_texconv
    print(Fore.YELLOW + '[TEXCONV] Not found in any location')
    print(Fore.YELLOW + '[INFO] Texconv will be needed for DDS conversion')
    print(Fore.YELLOW + '[INFO] You can download it from Preferences tab')
    return None
TEXCONV_PATH = find_texconv()
HAS_PYQT = True
try:
    from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, QComboBox, QMessageBox, QInputDialog, QToolTip, QTabWidget, QLineEdit, QRadioButton, QButtonGroup, QGroupBox, QMenu, QDialog, QCheckBox, QSpinBox, QSizePolicy
    from PyQt6.QtGui import QPixmap, QImage, QColor, QPalette, QCursor, QPainter, QPen, QAction
    from PyQt6.QtCore import Qt, QEvent, QTimer
    from console_viewer_widget import ConsoleCapture, ConsoleViewerDialog
except ImportError:
    HAS_PYQT = False
VERSION = '1.8.0'
TEMP_DIR = os.path.abspath('temp')
os.makedirs(TEMP_DIR, exist_ok=True)
CONSOLE_CAPTURE = None
EXPORT_ORDER_ITEMS = [{'folder': 'AssetsLowRes\\ControllerUIIcons\\items_png', 'size': 72}, {'folder': 'Assets\\ControllerUIIcons\\items_png', 'size': 144}, {'folder': 'AssetsLowRes\\Tooltips\\ItemIcons', 'size': 192}, {'folder': 'Assets\\Tooltips\\ItemIcons', 'size': 380}]
EXPORT_ORDER_SKILLS = [{'folder': 'AssetsLowRes\\ControllerUIIcons\\skills_png', 'size': 72}, {'folder': 'Assets\\ControllerUIIcons\\skills_png', 'size': 144}, {'folder': 'AssetsLowRes\\Tooltips\\SkillIcons', 'size': 192}, {'folder': 'Assets\\Tooltips\\SkillIcons', 'size': 380}]
_log_file_handler = None
_log_file_path = None
_logging_enabled = False

def setup_logging(log_dir=None, log_level='DEBUG', enabled=True):
    global _log_file_handler, _log_file_path, _logging_enabled
    _logging_enabled = enabled
    if not enabled:
        print(Fore.YELLOW + '[LOGGING] File logging disabled in preferences')
        return None
    if log_dir is None or not log_dir.strip():
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f'icon_manager_{timestamp}.log'
    _log_file_path = os.path.join(log_dir, log_filename)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    _log_file_handler = logging.FileHandler(_log_file_path, mode='w', encoding='utf-8')
    _log_file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    _log_file_handler.setFormatter(formatter)
    logger.addHandler(_log_file_handler)
    print(Fore.GREEN + f'[LOGGING] Session log created: {_log_file_path}')
    print(Fore.GREEN + f'[LOGGING] File log level: DEBUG (captures everything)')
    print(Fore.GREEN + f'[LOGGING] Console display level: {log_level}')
    logging.info('=' * 60)
    logging.info(f'Icon Manager v{VERSION} - Session started')
    logging.info(f'File Log Level: DEBUG (everything)')
    logging.info(f'Console Display Level: {log_level}')
    logging.info('=' * 60)
    return _log_file_path

def cleanup_old_logs(log_dir=None, max_files=10):
    if log_dir is None or not log_dir.strip():
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    if not os.path.exists(log_dir):
        return
    log_pattern = os.path.join(log_dir, 'icon_manager_*.log')
    log_files = glob.glob(log_pattern)
    if len(log_files) <= max_files:
        return
    log_files.sort(key=os.path.getmtime)
    files_to_delete = log_files[:-max_files]
    for old_log in files_to_delete:
        try:
            os.remove(old_log)
            print(Fore.YELLOW + f'[LOGGING] Cleaned up old log: {os.path.basename(old_log)}')
        except Exception as e:
            print(Fore.RED + f'[LOGGING] Failed to delete old log {old_log}: {e}')

def cleanup_logging():
    global _log_file_handler, _log_file_path
    if _log_file_handler:
        logging.info('=' * 60)
        logging.info('Icon Manager session ended')
        logging.info('=' * 60)
        logging.shutdown()
        print(Fore.GREEN + f'[LOGGING] Session log saved: {_log_file_path}')

def log_print(message, level='DEBUG', color=Fore.GREEN):
    print(color + message)
    if _logging_enabled:
        clean_message = message
        level_upper = level.upper()
        if level_upper == 'DEBUG':
            logging.debug(clean_message)
        elif level_upper == 'INFO':
            logging.info(clean_message)
        elif level_upper == 'WARNING':
            logging.warning(clean_message)
        elif level_upper == 'ERROR':
            logging.error(clean_message)
        elif level_upper == 'CRITICAL':
            logging.critical(clean_message)
        else:
            logging.debug(clean_message)
DEFAULT_BG3_PATHS = ['C:\\SteamLibrary\\steamapps\\common\\Baldurs Gate 3\\Data', '/home/deck/.steam/steam/steamapps/common/Baldurs Gate 3/Data', '~/Library/Application Support/Steam/steamapps/common/Baldurs Gate 3/Data']
STRINGS_EN = {'window_title': f'BG3 Icon Tool v{VERSION}', 'load_atlas': 'Load .lsx Atlas', 'replace_icon': 'Replace Selected Icon', 'add_icon': 'Add New Icon', 'save_atlas': 'Save Updated Atlas', 'resize_item': 'Resize Item PNG to Smaller Sizes', 'resize_skill': 'Resize Skill PNG to Smaller Sizes', 'select_png_replace': 'Select PNG to Replace', 'select_png_add': 'Select PNG to Add', 'mapkey_prompt': 'Enter MapKey for new icon:', 'error_load': 'Load atlas first.', 'error_no_slots': 'No free slots.', 'success_replace': 'Replaced {key}', 'success_add': 'Added {key}', 'success_save': 'Saved to {lsx} and {dds}', 'success_resize': 'Resized {type} DDS files saved to specified folders.', 'select_item_png': 'Select Item PNG to Resize', 'select_skill_png': 'Select Skill PNG to Resize', 'select_dest_dir': 'Select Destination Directory'}

def resize_with_alpha(im, size, resample=Image.BICUBIC):
    if im.mode != 'RGBA':
        return im.resize(size, resample)
    original_width, original_height = im.size
    target_width, target_height = size
    scale_factor = min(target_width / original_width, target_height / original_height)
    if scale_factor < 0.25:
        print(Fore.CYAN + f'[RESIZE] Multi-stage downsampling: {original_width}x{original_height} → {target_width}x{target_height} (factor: {scale_factor:.2f}x)')
        intermediate_size = (int(target_width * 2), int(target_height * 2))
        im = im.resize(intermediate_size, resample)
        result = im.resize(size, resample)
        print(Fore.GREEN + f'[RESIZE] Multi-stage complete')
        return result
    else:
        print(Fore.GREEN + f'[RESIZE] Single-stage: {original_width}x{original_height} → {target_width}x{target_height}')
        return im.resize(size, resample)

def apply_alpha_dither(im, strength=0.5):
    if im.mode != 'RGBA':
        return im
    img_array = np.array(im, dtype=np.float32)
    alpha = img_array[:, :, 3]
    noise = np.random.uniform(-strength, strength, alpha.shape)
    alpha_dithered = np.clip(alpha + noise, 0, 255)
    img_array[:, :, 3] = alpha_dithered
    return Image.fromarray(img_array.astype(np.uint8), 'RGBA')

def main():
    global CONSOLE_CAPTURE
    if HAS_PYQT:
        try:
            CONSOLE_CAPTURE = ConsoleCapture()
            print(Fore.CYAN + '=' * 60)
            print(Fore.CYAN + 'BG3 Icon Manager v6.1 - Console Capture Active')
            print(Fore.CYAN + "Click 'Show Console' button to view logs")
            print(Fore.CYAN + '=' * 60)
        except Exception as e:
            print(Fore.YELLOW + f'[WARNING] Console capture initialization failed: {e}')
            print(Fore.YELLOW + '[INFO] Console viewer will not be available')
    prefs_file = os.path.join(os.path.dirname(__file__), 'preferences.json')
    if os.path.exists(prefs_file):
        with open(prefs_file, 'r', encoding='utf-8') as f:
            prefs = json.load(f)
    else:
        prefs = {}
    log_enabled = prefs.get('log_enabled', True)
    log_directory = prefs.get('log_directory', os.path.join(os.path.dirname(__file__), 'logs'))
    log_level = prefs.get('log_level', 'DEBUG')
    max_log_files = prefs.get('max_log_files', 10)
    setup_logging(log_dir=log_directory, log_level=log_level, enabled=log_enabled)
    atexit.register(cleanup_logging)
    if log_enabled:
        cleanup_old_logs(log_dir=log_directory, max_files=max_log_files)
    if not HAS_PYQT:
        print(Fore.RED + 'PyQt6 not installed. Exiting.')
        sys.exit(1)
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(palette)
    window = GuiWindow()
    window.show()
    sys.exit(app.exec())

def resize_png(png_path, skill_mode=False, dest_dir='', output_name=None):
    print(Fore.CYAN + f'\n=== RESIZE PNG OPERATION START ===')
    print(Fore.GREEN + f'[DEBUG] Input PNG: {png_path}')
    print(Fore.GREEN + f'[DEBUG] Skill Mode: {skill_mode}')
    print(Fore.GREEN + f'[DEBUG] Destination Directory: {dest_dir}')
    print(Fore.GREEN + f"[DEBUG] Output Name Override: {(output_name if output_name else '(auto-detect)')}")
    im = Image.open(png_path)
    width, height = im.size
    print(Fore.GREEN + f'[DEBUG] Image dimensions: {width}x{height}')
    if width != height:
        print(Fore.YELLOW + f'[WARNING] Skipping non-square image: {png_path}')
        return
    if output_name:
        base_name = output_name
        print(Fore.GREEN + f'✓ Base name from override: {base_name}')
    else:
        base_name = os.path.basename(png_path).rsplit('.', 1)[0]
        print(Fore.GREEN + f'✓ Base name auto-extracted from filename: {base_name}')
        print(Fore.CYAN + f'[INFO] This will be used as the icon name (no manual input required)')
    if skill_mode:
        base_name += '_skill'
        print(Fore.GREEN + f'[DEBUG] Skill mode suffix added: {base_name}')
    export_order = EXPORT_ORDER_SKILLS if skill_mode else EXPORT_ORDER_ITEMS
    print(Fore.GREEN + f"[DEBUG] Export order selected: {('SKILLS' if skill_mode else 'ITEMS')} ({len(export_order)} sizes)")
    temp_png = os.path.join(TEMP_DIR, f'{base_name}_temp.png')
    print(Fore.GREEN + f'[DEBUG] Temporary PNG path: {temp_png}')
    for idx, exp in enumerate(export_order):
        folder = exp['folder']
        size = exp['size']
        print(Fore.CYAN + f'[STEP {idx + 1}/{len(export_order)}] Processing size {size}x{size} for folder: {folder}')
        full_folder = os.path.join(dest_dir, folder)
        print(Fore.GREEN + f'[DEBUG] Full folder path: {full_folder}')
        os.makedirs(full_folder, exist_ok=True)
        print(Fore.GREEN + f'[DEBUG] Directory created/verified')
        resized = resize_with_alpha(im, (size, size), Image.BICUBIC)
        print(Fore.GREEN + f'[DEBUG] Image resized to {size}x{size} with alpha preservation')
        resized.save(temp_png, 'PNG')
        print(Fore.GREEN + f'[DEBUG] Temporary PNG saved')
        out_path = os.path.join(full_folder, f'{base_name}.dds')
        print(Fore.GREEN + f'[DEBUG] Converting to DDS: {out_path}')
        png_to_dds(temp_png, out_path, format='BC7_UNORM', mipmaps=1)
        print(Fore.GREEN + f'✓ Saved resized DDS to {out_path}')
    if os.path.exists(temp_png):
        os.remove(temp_png)
        print(Fore.GREEN + f'[DEBUG] Cleaned up temporary PNG')
    print(Fore.GREEN + f'=== RESIZE PNG OPERATION COMPLETE ===\n')

def dds_to_png(dds_path, png_path):
    print(Fore.CYAN + f'\n--- DDS to PNG Conversion Start ---')
    print(Fore.GREEN + f'[DEBUG] Input DDS: {dds_path}')
    print(Fore.GREEN + f'[DEBUG] Output PNG: {png_path}')
    print(Fore.GREEN + f'[DEBUG] DDS file exists: {os.path.exists(dds_path)}')
    try:
        output_dir = os.path.normpath(os.path.dirname(png_path))
        input_dds = os.path.normpath(dds_path)
        cmd = [TEXCONV_PATH, '-ft', 'PNG', '-o', output_dir, '-y', input_dds]
        print(Fore.CYAN + f"[TEXCONV] Running command: {' '.join(cmd)}")
        print(Fore.GREEN + f'[DEBUG] Output directory: {output_dir}')
        subprocess.check_call(cmd)
        print(Fore.GREEN + f'[DEBUG] texconv completed successfully')
        output_file = os.path.join(os.path.dirname(png_path), os.path.basename(dds_path).replace('.dds', '.PNG').replace('.DDS', '.PNG'))
        print(Fore.GREEN + f'[DEBUG] Expected texconv output: {output_file}')
        print(Fore.GREEN + f'[DEBUG] Output file exists: {os.path.exists(output_file)}')
        if os.path.exists(png_path):
            print(Fore.GREEN + f'[DEBUG] Removing existing PNG at destination')
            os.remove(png_path)
        if os.path.exists(output_file):
            print(Fore.GREEN + f'[DEBUG] Renaming {output_file} to {png_path}')
            os.rename(output_file, png_path)
        print(Fore.GREEN + f'✓ Converted DDS to PNG: {dds_path} -> {png_path}')
    except FileNotFoundError:
        print(Fore.RED + "[ERROR] texconv.exe not found. Ensure it's downloaded and in PATH/script dir.")
        print(Fore.YELLOW + '[FALLBACK] Attempting Pillow conversion (basic support)')
        try:
            im = Image.open(dds_path)
            print(Fore.GREEN + f'[DEBUG] PIL opened DDS successfully')
            im.save(png_path, 'PNG')
            print(Fore.GREEN + f'✓ Pillow fallback conversion successful')
        except Exception as pil_e:
            print(Fore.RED + f'[ERROR] Pillow conversion failed: {pil_e}')
    except subprocess.CalledProcessError as e:
        print(Fore.RED + f'[ERROR] Texconv DDS to PNG failed with error code {e.returncode}')
        print(Fore.YELLOW + '[FALLBACK] Attempting Pillow conversion')
        try:
            im = Image.open(dds_path)
            print(Fore.GREEN + f'[DEBUG] PIL opened DDS successfully')
            im.save(png_path, 'PNG')
            print(Fore.GREEN + f'✓ Fallback converted DDS to PNG: {dds_path} -> {png_path}')
        except Exception as fallback_e:
            print(Fore.RED + f'[ERROR] PIL fallback also failed: {fallback_e}')
    print(Fore.CYAN + f'--- DDS to PNG Conversion End ---\n')

def png_to_dds(png_path, dds_path, format='BC3_UNORM', mipmaps=None):
    print(Fore.CYAN + f'\n--- PNG to DDS Conversion Start ---')
    print(Fore.GREEN + f'[DEBUG] Input PNG: {png_path}')
    print(Fore.GREEN + f'[DEBUG] Output DDS: {dds_path}')
    print(Fore.GREEN + f'[DEBUG] PNG file exists: {os.path.exists(png_path)}')
    try:
        with Image.open(png_path) as img:
            width, height = img.size
        if mipmaps is None:
            max_dimension = max(width, height)
            mipmaps = math.floor(math.log2(max_dimension)) + 1
        print(Fore.GREEN + f'[DEBUG] Image dimensions: {width}x{height}')
        print(Fore.GREEN + f'[DEBUG] Mipmap levels: {mipmaps}')
        output_dir = os.path.normpath(os.path.dirname(dds_path))
        input_png = os.path.normpath(png_path)
        format_label = 'BC3_UNORM (DXT5)' if format == 'BC3_UNORM' else f'{format}'
        cmd = [TEXCONV_PATH, '-f', format, '-m', str(mipmaps), '-o', output_dir, '-y', input_png]
        print(Fore.CYAN + f"[TEXCONV] Running command: {' '.join(cmd)}")
        print(Fore.GREEN + f'[DEBUG] Output directory: {output_dir}')
        print(Fore.GREEN + f'[DEBUG] Compression format: {format_label}')
        print(Fore.GREEN + f'[DEBUG] Mipmap levels: {mipmaps}')
        subprocess.check_call(cmd)
        print(Fore.GREEN + f'[DEBUG] texconv completed successfully')
        output_dir = os.path.dirname(dds_path)
        base_name = os.path.basename(png_path).lower().replace('.png', '')
        possible_outputs = [os.path.join(output_dir, base_name + '.DDS'), os.path.join(output_dir, base_name + '.dds'), os.path.join(output_dir, os.path.basename(png_path).replace('.png', '.DDS')), os.path.join(output_dir, os.path.basename(png_path).replace('.png', '.dds')), os.path.join(output_dir, os.path.basename(png_path).replace('.PNG', '.DDS')), os.path.join(output_dir, os.path.basename(png_path).replace('.PNG', '.dds'))]
        output_file = None
        for candidate in possible_outputs:
            if os.path.exists(candidate):
                output_file = candidate
                print(Fore.GREEN + f'[DEBUG] Found texconv output: {output_file}')
                break
        if not output_file:
            print(Fore.RED + f'[ERROR] Could not find texconv output! Checked:')
            for candidate in possible_outputs[:3]:
                print(Fore.RED + f'  - {candidate}')
            raise FileNotFoundError(f'Texconv output not found in {output_dir}')
        if os.path.exists(dds_path) and output_file != dds_path:
            print(Fore.GREEN + f'[DEBUG] Removing existing DDS at destination')
            os.remove(dds_path)
        if output_file != dds_path:
            print(Fore.GREEN + f'[DEBUG] Renaming {output_file} to {dds_path}')
            os.rename(output_file, dds_path)
        print(Fore.GREEN + f'✓ Converted PNG to DDS: {png_path} -> {dds_path}')
    except FileNotFoundError:
        print(Fore.RED + "[ERROR] texconv.exe not found. Ensure it's downloaded and in PATH/script dir.")
        print(Fore.YELLOW + '[FALLBACK] Attempting Pillow conversion (basic support)')
        try:
            with Image.open(png_path) as img:
                width, height = img.size
                im = img.convert('RGBA')
            if mipmaps is None:
                max_dimension = max(width, height)
                mipmaps = math.floor(math.log2(max_dimension)) + 1
            dxt_format = 'DXT5'
            print(Fore.GREEN + f'[DEBUG] PIL opened PNG and converted to RGBA')
            print(Fore.GREEN + f'[DEBUG] Image dimensions: {width}x{height}')
            print(Fore.GREEN + f'[DEBUG] Using {dxt_format} compression with {mipmaps} mipmap levels')
            im.save(dds_path, 'DDS', format=dxt_format, mipmaps=mipmaps)
            print(Fore.GREEN + f'✓ Pillow fallback conversion successful')
        except Exception as pil_e:
            print(Fore.RED + f'[ERROR] Pillow conversion failed: {pil_e}')
    except subprocess.CalledProcessError as e:
        print(Fore.RED + f'[ERROR] Texconv PNG to DDS failed with error code {e.returncode}')
        print(Fore.YELLOW + '[FALLBACK] Attempting Pillow conversion')
        try:
            with Image.open(png_path) as img:
                width, height = img.size
                im = img.convert('RGBA')
            if mipmaps is None:
                max_dimension = max(width, height)
                mipmaps = math.floor(math.log2(max_dimension)) + 1
            dxt_format = 'DXT5'
            print(Fore.GREEN + f'[DEBUG] PIL opened PNG and converted to RGBA')
            print(Fore.GREEN + f'[DEBUG] Image dimensions: {width}x{height}')
            print(Fore.GREEN + f'[DEBUG] Using {dxt_format} compression with {mipmaps} mipmap levels')
            im.save(dds_path, 'DDS', format=dxt_format, mipmaps=mipmaps)
            print(Fore.GREEN + f'✓ Fallback converted PNG to DDS: {png_path} -> {dds_path}')
        except Exception as fallback_e:
            print(Fore.RED + f'[ERROR] PIL fallback also failed: {fallback_e}')
    print(Fore.CYAN + f'--- PNG to DDS Conversion End ---\n')

def parse_lsx(lsx_path, game_dir=None, mode='standalone'):
    print(Fore.CYAN + f'\n=== PARSING LSX FILE ===')
    print(Fore.GREEN + f'[DEBUG] LSX Path: {lsx_path}')
    print(Fore.GREEN + f'[DEBUG] Game Directory: {game_dir}')
    print(Fore.GREEN + f'[DEBUG] Mode: {mode}')
    print(Fore.GREEN + f'[DEBUG] LSX file exists: {os.path.exists(lsx_path)}')
    from pathlib import Path
    print(Fore.GREEN + f'[DEBUG] Reading LSX file...')
    with open(lsx_path, 'r', encoding='utf-8') as f:
        content = f.read()
    print(Fore.GREEN + f'[DEBUG] LSX file size: {len(content)} bytes')
    try:
        print(Fore.GREEN + f'[DEBUG] Parsing XML content...')
        dom = parseString(content)
        print(Fore.GREEN + f'✓ XML parsed successfully')
    except ExpatError as e:
        print(Fore.RED + f'[ERROR] XML parse error in {lsx_path}: {e}')
        return (None, None, None, None, None)
    atlas_path = None
    atlas_size = None
    tile_size = None
    print(Fore.GREEN + f'[DEBUG] Searching for TextureAtlasInfo region...')
    for region in dom.getElementsByTagName('region'):
        if region.getAttribute('id') == 'TextureAtlasInfo':
            print(Fore.GREEN + f'✓ Found TextureAtlasInfo region')
            for node in region.getElementsByTagName('node'):
                if node.getAttribute('id') == 'TextureAtlasTextureSize':
                    print(Fore.GREEN + f'[DEBUG] Found TextureAtlasTextureSize node')
                    for attr in node.getElementsByTagName('attribute'):
                        if attr.getAttribute('id') == 'Width':
                            atlas_size = int(attr.getAttribute('value'))
                            print(Fore.GREEN + f'✓ Atlas size: {atlas_size}x{atlas_size}')
                            break
                elif node.getAttribute('id') == 'TextureAtlasIconSize':
                    print(Fore.GREEN + f'[DEBUG] Found TextureAtlasIconSize node')
                    for attr in node.getElementsByTagName('attribute'):
                        if attr.getAttribute('id') == 'Width':
                            tile_size = int(attr.getAttribute('value'))
                            print(Fore.GREEN + f'✓ Tile size: {tile_size}x{tile_size}')
                            break
                if atlas_size and tile_size:
                    break
            break
    if atlas_size is None or tile_size is None:
        print(Fore.RED + f'[ERROR] Could not parse atlas_size or tile_size from {lsx_path}.')
        print(Fore.RED + f'[ERROR] atlas_size={atlas_size}, tile_size={tile_size}')
        return (None, None, None, None, None)
    print(Fore.GREEN + f'[DEBUG] Searching for atlas Path attribute...')
    for node in dom.getElementsByTagName('attribute'):
        if node.getAttribute('id') == 'Path':
            atlas_path = node.getAttribute('value')
            print(Fore.GREEN + f'✓ Found atlas path in LSX: {atlas_path}')
            break
    if atlas_path:
        print(Fore.GREEN + f'[DEBUG] Resolving DDS path for mode: {mode}')
        lsx_dir = Path(lsx_path).parent
        rel_path = Path(atlas_path)
        print(Fore.GREEN + f'[DEBUG] LSX directory: {lsx_dir}')
        print(Fore.GREEN + f'[DEBUG] Relative path from LSX: {rel_path}')
        if mode == 'mod_project':
            print(Fore.GREEN + f'[DEBUG] Mod project mode - searching for DDS in Public folders')
            if game_dir:
                print(Fore.GREEN + f'[DEBUG] Game directory provided: {game_dir}')
                lsx_path_obj = Path(lsx_path)
                mod_uuid = None
                path_parts = lsx_path_obj.parts
                for i, part in enumerate(path_parts):
                    if part.lower() in ['public', 'mods'] and i + 1 < len(path_parts):
                        mod_uuid = path_parts[i + 1]
                        print(Fore.GREEN + f'✓ Extracted mod UUID from path: {mod_uuid}')
                        break
                if not mod_uuid:
                    print(Fore.YELLOW + f'[WARNING] Could not extract mod UUID from LSX path')
                    search_roots = [Path(game_dir) / 'Public', Path(game_dir) / 'Generated' / 'Public']
                else:
                    search_roots = [Path(game_dir) / 'Public' / mod_uuid, Path(game_dir) / 'Generated' / 'Public' / mod_uuid]
                print(Fore.GREEN + f'[DEBUG] Searching in roots: {[str(r) for r in search_roots]}')
                for root in search_roots:
                    if root.is_dir():
                        candidate = root / rel_path
                        print(Fore.GREEN + f'[DEBUG] Checking candidate: {candidate}')
                        print(Fore.GREEN + f'[DEBUG] Candidate exists: {candidate.exists()}')
                        if candidate.exists():
                            full_dds = candidate
                            print(Fore.GREEN + f'✓ Found DDS at: {full_dds}')
                            break
                else:
                    print(Fore.YELLOW + f'[WARNING] DDS not found in any search location')
                    full_dds = None
            else:
                print(Fore.YELLOW + f'[WARNING] No game directory provided for mod project mode')
                full_dds = None
        else:
            print(Fore.GREEN + f'[DEBUG] Standalone mode - resolving path relative to LSX')
            if rel_path.is_absolute():
                print(Fore.GREEN + f'[DEBUG] Path is absolute: {rel_path}')
                full_dds = rel_path
            else:
                print(Fore.GREEN + f'[DEBUG] Path is relative, resolving from LSX directory')
                full_dds = (lsx_dir / rel_path).resolve()
                print(Fore.GREEN + f'[DEBUG] Resolved to: {full_dds}')
        atlas_path = str(full_dds) if full_dds else None
        if atlas_path:
            print(Fore.GREEN + f'✓ Final DDS path: {atlas_path}')
            print(Fore.GREEN + f'[DEBUG] DDS file exists: {os.path.exists(atlas_path)}')
    else:
        print(Fore.RED + f'[ERROR] No atlas path found in {lsx_path}.')
        return (None, None, None, None, None)
    print(Fore.GREEN + f'[DEBUG] Parsing icon UV mappings...')
    icons = []
    icon_count = 0
    for node in dom.getElementsByTagName('node'):
        if node.getAttribute('id') == 'IconUV':
            icon_count += 1
            mapkey = None
            u1 = v1 = u2 = v2 = None
            for attr in node.getElementsByTagName('attribute'):
                aid = attr.getAttribute('id')
                if aid == 'MapKey':
                    mapkey = attr.getAttribute('value')
                elif aid == 'U1':
                    u1 = float(attr.getAttribute('value'))
                elif aid == 'U2':
                    u2 = float(attr.getAttribute('value'))
                elif aid == 'V1':
                    v1 = float(attr.getAttribute('value'))
                elif aid == 'V2':
                    v2 = float(attr.getAttribute('value'))
            if mapkey:
                icons.append({'mapkey': mapkey, 'u1': u1, 'u2': u2, 'v1': v1, 'v2': v2})
                if icon_count <= 5:
                    print(Fore.GREEN + f'[DEBUG] Icon {icon_count}: {mapkey} (UV: {u1:.3f},{v1:.3f} to {u2:.3f},{v2:.3f})')
    print(Fore.GREEN + f'✓ Parsed {len(icons)} icons from atlas')
    print(Fore.CYAN + f'=== LSX PARSING COMPLETE ===')
    print(Fore.CYAN + f'Summary: atlas_size={atlas_size}, tile_size={tile_size}, icons={len(icons)}, path={atlas_path}\n')
    return (dom, atlas_path, icons, atlas_size, tile_size)

def get_grid_slot(u1, v1, grid_size):
    col = int(u1 * grid_size)
    row = int(v1 * grid_size)
    return (col, row)

def create_new_atlas(png_folder, output_path, atlas_size, tile_size, grid_size):
    dom = Document()
    save = dom.createElement('save')
    dom.appendChild(save)
    version = dom.createElement('version')
    version.setAttribute('major', '4')
    version.setAttribute('minor', '0')
    version.setAttribute('revision', '9')
    version.setAttribute('build', '320')
    save.appendChild(version)
    region_tex = dom.createElement('region')
    region_tex.setAttribute('id', 'TextureAtlasInfo')
    save.appendChild(region_tex)
    node_root_tex = dom.createElement('node')
    node_root_tex.setAttribute('id', 'root')
    region_tex.appendChild(node_root_tex)
    children_tex = dom.createElement('children')
    node_root_tex.appendChild(children_tex)
    node_tex_size = dom.createElement('node')
    node_tex_size.setAttribute('id', 'TextureAtlasTextureSize')
    attr_height = dom.createElement('attribute')
    attr_height.setAttribute('id', 'Height')
    attr_height.setAttribute('type', 'int32')
    attr_height.setAttribute('value', str(atlas_size))
    node_tex_size.appendChild(attr_height)
    attr_width = dom.createElement('attribute')
    attr_width.setAttribute('id', 'Width')
    attr_width.setAttribute('type', 'int32')
    attr_width.setAttribute('value', str(atlas_size))
    node_tex_size.appendChild(attr_width)
    children_tex.appendChild(node_tex_size)
    node_icon_size = dom.createElement('node')
    node_icon_size.setAttribute('id', 'TextureAtlasIconSize')
    attr_height = dom.createElement('attribute')
    attr_height.setAttribute('id', 'Height')
    attr_height.setAttribute('type', 'int32')
    attr_height.setAttribute('value', str(tile_size))
    node_icon_size.appendChild(attr_height)
    attr_width = dom.createElement('attribute')
    attr_width.setAttribute('id', 'Width')
    attr_width.setAttribute('type', 'int32')
    attr_width.setAttribute('value', str(tile_size))
    node_icon_size.appendChild(attr_width)
    children_tex.appendChild(node_icon_size)
    node_path = dom.createElement('node')
    node_path.setAttribute('id', 'TextureAtlasPath')
    attr_path = dom.createElement('attribute')
    attr_path.setAttribute('id', 'Path')
    attr_path.setAttribute('type', 'string')
    attr_path.setAttribute('value', 'Assets/Textures/Icons/New_Atlas.dds')
    node_path.appendChild(attr_path)
    attr_uuid = dom.createElement('attribute')
    attr_uuid.setAttribute('id', 'UUID')
    attr_uuid.setAttribute('type', 'FixedString')
    attr_uuid.setAttribute('value', str(uuid.uuid4()))
    node_path.appendChild(attr_uuid)
    children_tex.appendChild(node_path)
    region_uv = dom.createElement('region')
    region_uv.setAttribute('id', 'IconUVList')
    save.appendChild(region_uv)
    node_root_uv = dom.createElement('node')
    node_root_uv.setAttribute('id', 'root')
    region_uv.appendChild(node_root_uv)
    children_uv = dom.createElement('children')
    node_root_uv.appendChild(children_uv)
    im = Image.new('RGBA', (atlas_size, atlas_size), (0, 0, 0, 0))
    png_files = sorted([f for f in os.listdir(png_folder) if f.lower().endswith('.png')])
    for idx, png_file in enumerate(png_files):
        mapkey = os.path.splitext(png_file)[0]
        row = idx // grid_size
        col = idx % grid_size
        if row >= grid_size:
            print(Fore.YELLOW + f'Skipping {png_file}: Atlas full.')
            continue
        x = col * tile_size
        y = row * tile_size
        png_path = os.path.join(png_folder, png_file)
        new_im = resize_with_alpha(Image.open(png_path), (tile_size, tile_size), Image.BICUBIC)
        im.paste(new_im, (x, y), new_im if new_im.mode == 'RGBA' else None)
        u1 = col / grid_size
        v1 = row / grid_size
        u2 = u1 + 1 / grid_size
        v2 = v1 + 1 / grid_size
        node_uv = dom.createElement('node')
        node_uv.setAttribute('id', 'IconUV')
        attr_mapkey = dom.createElement('attribute')
        attr_mapkey.setAttribute('id', 'MapKey')
        attr_mapkey.setAttribute('type', 'FixedString')
        attr_mapkey.setAttribute('value', mapkey)
        node_uv.appendChild(attr_mapkey)
        attr_u1 = dom.createElement('attribute')
        attr_u1.setAttribute('id', 'U1')
        attr_u1.setAttribute('type', 'float')
        attr_u1.setAttribute('value', str(u1))
        node_uv.appendChild(attr_u1)
        attr_v1 = dom.createElement('attribute')
        attr_v1.setAttribute('id', 'V1')
        attr_v1.setAttribute('type', 'float')
        attr_v1.setAttribute('value', str(v1))
        node_uv.appendChild(attr_v1)
        attr_u2 = dom.createElement('attribute')
        attr_u2.setAttribute('id', 'U2')
        attr_u2.setAttribute('type', 'float')
        attr_u2.setAttribute('value', str(u2))
        node_uv.appendChild(attr_u2)
        attr_v2 = dom.createElement('attribute')
        attr_v2.setAttribute('id', 'V2')
        attr_v2.setAttribute('type', 'float')
        attr_v2.setAttribute('value', str(v2))
        node_uv.appendChild(attr_v2)
        children_uv.appendChild(node_uv)
    temp_png = os.path.join(TEMP_DIR, 'temp_new.png')
    dithered = apply_alpha_dither(im, strength=0.5)
    dithered.save(temp_png, 'PNG')
    output_dds = output_path if output_path else os.path.join(png_folder, 'New_Atlas.dds')
    png_to_dds(temp_png, output_dds, format='BC3_UNORM', mipmaps=1)
    output_lsx = os.path.splitext(output_dds)[0] + '.lsx'
    with open(output_lsx, 'w', encoding='utf-8') as f:
        dom.writexml(f, indent='    ', addindent='    ', newl='\n', encoding='UTF-8')
    if os.path.exists(temp_png):
        os.remove(temp_png)
    print(Fore.GREEN + f'Created new atlas: {output_dds}, {output_lsx}')

def update_atlas(lsx_path, png_folder, icon_key=None, output_path=None, atlas_size=None, tile_size=None, grid_size=None, game_dir=None, mode='standalone'):
    dom, atlas_path, icons, parsed_atlas_size, parsed_tile_size = parse_lsx(lsx_path, game_dir, mode)
    if dom is None:
        return
    if atlas_size is None:
        atlas_size = parsed_atlas_size
    if tile_size is None:
        tile_size = parsed_tile_size
    if grid_size is None:
        grid_size = atlas_size // tile_size
    if atlas_size % tile_size != 0:
        print(Fore.RED + f'Invalid atlas: atlas_size {atlas_size} not divisible by tile_size {tile_size}.')
        return
    full_dds = atlas_path
    temp_png = os.path.join(TEMP_DIR, 'temp_update.png')
    dds_to_png(full_dds, temp_png)
    im = Image.open(temp_png)
    png_files = [f for f in os.listdir(png_folder) if f.endswith('.png')]
    for png_file in png_files:
        mapkey = icon_key or os.path.splitext(png_file)[0]
        matching_icons = [icon for icon in icons if icon['mapkey'] == mapkey]
        if not matching_icons:
            print(Fore.YELLOW + f"Skipping {png_file}: MapKey '{mapkey}' not found.")
            continue
        icon = matching_icons[0]
        col, row = get_grid_slot(icon['u1'], icon['v1'], grid_size)
        x = col * tile_size
        y = row * tile_size
        png_path = os.path.join(png_folder, png_file)
        clear_im = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
        im.paste(clear_im, (x, y))
        new_im = resize_with_alpha(Image.open(png_path), (tile_size, tile_size), Image.BICUBIC)
        im.paste(new_im, (x, y), new_im if 'A' in new_im.getbands() else None)
        print(Fore.GREEN + f'Updated {mapkey}')
    dithered = apply_alpha_dither(im, strength=0.5)
    dithered.save(temp_png, 'PNG')
    output_dds = output_path if output_path else full_dds
    png_to_dds(temp_png, output_dds, format='BC3_UNORM', mipmaps=1)
    output_lsx = os.path.splitext(output_dds)[0] + '.lsx'
    with open(output_lsx, 'w', encoding='utf-8') as f:
        dom.writexml(f, indent='    ', addindent='    ', newl='\n', encoding='UTF-8')
    if os.path.exists(temp_png):
        os.remove(temp_png)
    print(Fore.GREEN + f'Updated atlas: {output_dds}, {output_lsx}')

class InteractivePreviewLabel(QLabel):

    def __init__(self, icons, preview_size, atlas_size, tile_size, parent=None):
        super().__init__(parent)
        self.icons = icons
        self.preview_size = preview_size
        self.atlas_size = atlas_size
        self.tile_size = tile_size
        self.setMouseTracking(True)
        self.tile_regions = self._compute_tile_regions()
        self.selected_icon = None
        self.parent_window = parent
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def _compute_tile_regions(self):
        regions = {}
        for icon in self.icons:
            x_start = int(icon['u1'] * self.atlas_size)
            y_start = int(icon['v1'] * self.atlas_size)
            x_end = int(icon['u2'] * self.atlas_size)
            y_end = int(icon['v2'] * self.atlas_size)
            regions[icon['mapkey']] = (x_start, y_start, x_end, y_end)
        return regions

    def get_icon_at_position(self, mouse_x, mouse_y):
        atlas_x = mouse_x / self.preview_size * self.atlas_size
        atlas_y = mouse_y / self.preview_size * self.atlas_size
        for icon in self.icons:
            x_start = int(icon['u1'] * self.atlas_size)
            y_start = int(icon['v1'] * self.atlas_size)
            x_end = int(icon['u2'] * self.atlas_size)
            y_end = int(icon['v2'] * self.atlas_size)
            if x_start <= atlas_x < x_end and y_start <= atlas_y < y_end:
                return icon
        return None

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        mouse_x = event.pos().x()
        mouse_y = event.pos().y()
        atlas_x = mouse_x / self.preview_size * self.atlas_size
        atlas_y = mouse_y / self.preview_size * self.atlas_size
        for mapkey, (x_start, y_start, x_end, y_end) in self.tile_regions.items():
            if x_start <= atlas_x < x_end and y_start <= atlas_y < y_end:
                QToolTip.showText(QCursor.pos(), mapkey)
                return
        QToolTip.hideText()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            icon = self.get_icon_at_position(event.pos().x(), event.pos().y())
            if icon:
                self.selected_icon = icon
                print(Fore.GREEN + f"[DEBUG] Selected icon: {icon['mapkey']}")
                self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.selected_icon and self.pixmap():
            painter = QPainter(self)
            pen = QPen(QColor(255, 140, 0), 3)
            painter.setPen(pen)
            x_start = int(self.selected_icon['u1'] * self.preview_size)
            y_start = int(self.selected_icon['v1'] * self.preview_size)
            x_end = int(self.selected_icon['u2'] * self.preview_size)
            y_end = int(self.selected_icon['v2'] * self.preview_size)
            width = x_end - x_start
            height = y_end - y_start
            painter.drawRect(x_start, y_start, width, height)
            painter.end()

    def show_context_menu(self, position):
        icon = self.get_icon_at_position(position.x(), position.y())
        if not icon:
            return
        self.selected_icon = icon
        self.update()
        print(Fore.CYAN + f"[USER] Right-clicked on icon: {icon['mapkey']}")
        menu = QMenu(self)
        menu.setStyleSheet('QMenu { background-color: #2a2a2a; color: white; } QMenu::item:selected { background-color: #3a3a3a; }')
        preview_action = QAction('🔍 Preview Full Size', self)
        preview_action.triggered.connect(lambda: self.parent_window.preview_full_size(icon['mapkey']))
        menu.addAction(preview_action)
        replace_action = QAction('📝 Replace Icon', self)
        replace_action.triggered.connect(lambda: self.parent_window.replace_icon_from_context(icon['mapkey']))
        menu.addAction(replace_action)
        menu.addSeparator()
        copy_action = QAction('📋 Copy MapKey Name', self)
        copy_action.triggered.connect(lambda: self.parent_window.copy_mapkey(icon['mapkey']))
        menu.addAction(copy_action)
        delete_action = QAction('🗑️ Delete from Atlas', self)
        delete_action.triggered.connect(lambda: self.parent_window.delete_icon_from_atlas(icon['mapkey']))
        menu.addAction(delete_action)
        menu.exec(self.mapToGlobal(position))

class GuiWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.strings = STRINGS_EN
        self.setWindowTitle(self.strings['window_title'])
        self.setGeometry(100, 100, 1200, 800)
        toolbar = self.addToolBar('Tools')
        toolbar.setMovable(False)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        toolbar.addWidget(spacer)
        console_action = QAction('📋 Show Console', self)
        console_action.setToolTip('View real-time console output, logs, and debug information')
        console_action.triggered.connect(self.show_console_viewer)
        toolbar.addAction(console_action)
        self.atlas_im = None
        self.dom = None
        self.icons = []
        self.atlas_path = None
        self.preview_label = None
        self.preview_size = 1024
        self.mode = 'mod_project'
        self.dom_modified = False
        self.prefs = self.load_preferences()
        self.bg3_data = self.prefs.get('bg3_data', DEFAULT_BG3_PATHS[0])
        self.temp_dir = self.prefs.get('temp_dir', TEMP_DIR)
        self.output_path = self.prefs.get('output_path', '')
        self.zip_output_path = self.prefs.get('zip_output_path', '')
        self.preview_size_option = self.prefs.get('preview_size', 'Full Atlas Size')
        central = QWidget()
        layout = QHBoxLayout()
        central.setLayout(layout)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        main_tab = QWidget()
        self.tabs.addTab(main_tab, 'Main')
        main_layout = QVBoxLayout()
        main_tab.setLayout(main_layout)
        bg3_layout = QHBoxLayout()
        bg3_layout.addWidget(QLabel('BG3 Data Path:'))
        self.bg3_edit = QLineEdit(self.bg3_data)
        bg3_layout.addWidget(self.bg3_edit)
        btn_browse_bg3 = QPushButton('Browse')
        btn_browse_bg3.clicked.connect(self.browse_bg3)
        bg3_layout.addWidget(btn_browse_bg3)
        main_layout.addLayout(bg3_layout)
        mod_layout = QHBoxLayout()
        mod_layout.addWidget(QLabel('Mod Project:'))
        self.mod_combo = QComboBox()
        self.mod_combo.setStyleSheet('QComboBox { text-align: left; padding-left: 10px; }')
        self.mod_combo.currentIndexChanged.connect(self.on_mod_selection_changed)
        mod_layout.addWidget(self.mod_combo)
        main_layout.addLayout(mod_layout)
        mode_group = QGroupBox('Mode')
        mode_layout = QVBoxLayout()
        self.mode_standalone = QRadioButton('Standalone Mode')
        self.mode_standalone.toggled.connect(self.toggle_mode)
        mode_layout.addWidget(self.mode_standalone)
        self.mode_project = QRadioButton('Mod Project Mode')
        self.mode_project.setChecked(True)
        self.mode_project.toggled.connect(self.toggle_mode)
        mode_layout.addWidget(self.mode_project)
        mode_group.setLayout(mode_layout)
        main_layout.addWidget(mode_group)
        self.standalone_group = QGroupBox('Standalone Paths')
        standalone_layout = QVBoxLayout()
        standalone_layout.addWidget(QLabel('Atlas .lsx Path:'))
        self.standalone_lsx_edit = QLineEdit()
        standalone_layout.addWidget(self.standalone_lsx_edit)
        btn_browse_lsx = QPushButton('Browse')
        btn_browse_lsx.clicked.connect(lambda: self.browse_path(self.standalone_lsx_edit, 'Select .lsx', '*.lsx'))
        standalone_layout.addWidget(btn_browse_lsx)
        standalone_layout.addWidget(QLabel('Atlas DDS Path:'))
        self.standalone_dds_edit = QLineEdit()
        standalone_layout.addWidget(self.standalone_dds_edit)
        btn_browse_dds = QPushButton('Browse')
        btn_browse_dds.clicked.connect(lambda: self.browse_path(self.standalone_dds_edit, 'Select DDS', '*.dds'))
        standalone_layout.addWidget(btn_browse_dds)
        self.standalone_group.setLayout(standalone_layout)
        self.standalone_group.setVisible(False)
        main_layout.addWidget(self.standalone_group)
        self.project_group = QGroupBox('Mod Project')
        project_layout = QVBoxLayout()
        self.atlas_status_label = QLabel('No Atlas Loaded')
        self.atlas_status_label.setStyleSheet('QLabel { color: #888; font-style: italic; }')
        project_layout.addWidget(self.atlas_status_label)
        project_layout.addWidget(QLabel('Current Atlas:'))
        self.project_lsx_edit = QLineEdit()
        self.project_lsx_edit.setReadOnly(True)
        self.project_lsx_edit.setPlaceholderText('No atlas loaded')
        self.project_lsx_edit.setStyleSheet('QLineEdit { background-color: #2a2a2a; }')
        project_layout.addWidget(self.project_lsx_edit)
        self.btn_load_project_atlas = QPushButton('Load Atlas from Project')
        self.btn_load_project_atlas.clicked.connect(self.load_atlas_from_project)
        self.btn_load_project_atlas.setEnabled(False)
        self.btn_load_project_atlas.setStyleSheet('QPushButton:disabled { color: #555; }')
        project_layout.addWidget(self.btn_load_project_atlas)
        btn_browse_project_lsx = QPushButton('Browse Manually (Advanced)')
        btn_browse_project_lsx.clicked.connect(lambda: self.browse_path(self.project_lsx_edit, 'Select .lsx', '*.lsx'))
        btn_browse_project_lsx.setStyleSheet('QPushButton { font-size: 9pt; color: #888; }')
        project_layout.addWidget(btn_browse_project_lsx)
        self.project_group.setLayout(project_layout)
        self.project_group.setVisible(True)
        main_layout.addWidget(self.project_group)
        btn_load = QPushButton(self.strings['load_atlas'])
        btn_load.clicked.connect(self.load_atlas)
        main_layout.addWidget(btn_load)
        self.combo_icons = QComboBox()
        main_layout.addWidget(self.combo_icons)
        btn_replace = QPushButton(self.strings['replace_icon'])
        btn_replace.clicked.connect(self.replace_icon)
        main_layout.addWidget(btn_replace)
        btn_add = QPushButton(self.strings['add_icon'])
        btn_add.clicked.connect(self.add_icon)
        main_layout.addWidget(btn_add)
        btn_save = QPushButton(self.strings['save_atlas'])
        btn_save.clicked.connect(self.save_atlas)
        main_layout.addWidget(btn_save)
        btn_resize_item = QPushButton(self.strings['resize_item'])
        btn_resize_item.clicked.connect(self.resize_item_png_gui)
        main_layout.addWidget(btn_resize_item)
        btn_resize_skill = QPushButton(self.strings['resize_skill'])
        btn_resize_skill.clicked.connect(self.resize_skill_png_gui)
        main_layout.addWidget(btn_resize_skill)
        self.preview_placeholder = QLabel('Load an atlas to see preview')
        self.preview_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview_placeholder)
        self.setCentralWidget(central)
        create_tab = QWidget()
        self.tabs.addTab(create_tab, 'Create Atlas')
        create_layout = QVBoxLayout()
        create_tab.setLayout(create_layout)
        header_label = QLabel('Generate New Atlas')
        header_label.setStyleSheet('QLabel { font-size: 14pt; font-weight: bold; margin-bottom: 10px; }')
        create_layout.addWidget(header_label)
        mod_select_group = QGroupBox('Mod Project')
        mod_select_layout = QVBoxLayout()
        mod_row = QHBoxLayout()
        mod_row.addWidget(QLabel('Select Mod:'))
        self.create_mod_combo = QComboBox()
        self.create_mod_combo.setStyleSheet('QComboBox { text-align: left; padding-left: 10px; }')
        self.create_mod_combo.currentIndexChanged.connect(self.on_create_mod_changed)
        mod_row.addWidget(self.create_mod_combo)
        mod_select_layout.addLayout(mod_row)
        mod_select_group.setLayout(mod_select_layout)
        create_layout.addWidget(mod_select_group)
        template_group = QGroupBox('1. Atlas Configuration')
        template_layout = QVBoxLayout()
        canvas_layout = QHBoxLayout()
        canvas_layout.addWidget(QLabel('Canvas Size:'))
        self.canvas_size_group = QButtonGroup(self)
        self.canvas_512 = QRadioButton('512 x 512 (Standard)')
        self.canvas_512.setChecked(True)
        self.canvas_1024 = QRadioButton('1024 x 1024 (Large)')
        self.canvas_size_group.addButton(self.canvas_512)
        self.canvas_size_group.addButton(self.canvas_1024)
        canvas_layout.addWidget(self.canvas_512)
        canvas_layout.addWidget(self.canvas_1024)
        canvas_layout.addStretch()
        template_layout.addLayout(canvas_layout)
        self.grid_info_label = QLabel('Grid: 64x64 icons | Total slots: 64 (8x8)')
        self.grid_info_label.setStyleSheet('QLabel { color: #888; font-style: italic; margin-left: 20px; }')
        template_layout.addWidget(self.grid_info_label)
        self.canvas_512.toggled.connect(self.update_create_atlas_grid_info)
        self.canvas_1024.toggled.connect(self.update_create_atlas_grid_info)
        template_group.setLayout(template_layout)
        create_layout.addWidget(template_group)
        location_group = QGroupBox('2. Destination')
        location_layout = QVBoxLayout()
        location_info = QLabel("Atlas will be created in the selected mod's GUI folder:")
        location_info.setWordWrap(True)
        location_layout.addWidget(location_info)
        self.create_atlas_path_label = QLabel('No mod selected')
        self.create_atlas_path_label.setStyleSheet('QLabel { color: #888; font-style: italic; margin-left: 20px; background-color: #2a2a2a; padding: 5px; }')
        self.create_atlas_path_label.setWordWrap(True)
        location_layout.addWidget(self.create_atlas_path_label)
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel('Atlas Name:'))
        self.atlas_name_edit = QLineEdit('IconAtlas')
        self.atlas_name_edit.setPlaceholderText('e.g., IconAtlas, SkillAtlas')
        self.atlas_name_edit.textChanged.connect(self.update_create_atlas_status)
        name_layout.addWidget(self.atlas_name_edit)
        location_layout.addLayout(name_layout)
        location_group.setLayout(location_layout)
        create_layout.addWidget(location_group)
        icons_group = QGroupBox('3. Initial Icons (Optional)')
        icons_layout = QVBoxLayout()
        self.start_empty_radio = QRadioButton('Start with empty atlas')
        self.start_empty_radio.setChecked(True)
        self.start_empty_radio.toggled.connect(self.toggle_import_options)
        icons_layout.addWidget(self.start_empty_radio)
        self.import_folder_radio = QRadioButton('Import icons from folder')
        self.import_folder_radio.toggled.connect(self.toggle_import_options)
        icons_layout.addWidget(self.import_folder_radio)
        self.import_controls_widget = QWidget()
        import_controls_layout = QVBoxLayout()
        import_controls_layout.setContentsMargins(20, 0, 0, 0)
        folder_select_layout = QHBoxLayout()
        folder_select_layout.addWidget(QLabel('Folder:'))
        self.import_folder_edit = QLineEdit()
        self.import_folder_edit.setPlaceholderText('Select folder containing PNG images')
        self.import_folder_edit.textChanged.connect(self.scan_import_folder)
        folder_select_layout.addWidget(self.import_folder_edit)
        btn_browse_import = QPushButton('Browse')
        btn_browse_import.clicked.connect(self.browse_import_folder)
        folder_select_layout.addWidget(btn_browse_import)
        import_controls_layout.addLayout(folder_select_layout)
        self.import_count_label = QLabel('No folder selected')
        self.import_count_label.setStyleSheet('QLabel { color: #888; font-style: italic; }')
        import_controls_layout.addWidget(self.import_count_label)
        prefix_layout = QHBoxLayout()
        prefix_layout.addWidget(QLabel('MapKey Prefix (optional):'))
        self.mapkey_prefix_edit = QLineEdit()
        self.mapkey_prefix_edit.setPlaceholderText('e.g., MOD, CUSTOM')
        self.mapkey_prefix_edit.setMaximumWidth(200)
        prefix_layout.addWidget(self.mapkey_prefix_edit)
        prefix_layout.addStretch()
        import_controls_layout.addLayout(prefix_layout)
        self.prefix_example_label = QLabel('Example: sword.png → MapKey: sword')
        self.prefix_example_label.setStyleSheet('QLabel { color: #666; font-size: 9pt; margin-left: 20px; }')
        self.mapkey_prefix_edit.textChanged.connect(self.update_prefix_example)
        import_controls_layout.addWidget(self.prefix_example_label)
        import_controls_layout.addWidget(QLabel(''))
        self.auto_resize_checkbox = QCheckBox('Auto-generate resized versions (72, 144, 192, 380px)')
        self.auto_resize_checkbox.setChecked(True)
        self.auto_resize_checkbox.setToolTip('Creates multiple DDS sizes for game UI compatibility')
        self.auto_resize_checkbox.toggled.connect(self.toggle_resize_type_selection)
        import_controls_layout.addWidget(self.auto_resize_checkbox)
        self.resize_type_widget = QWidget()
        resize_type_layout = QHBoxLayout()
        resize_type_layout.setContentsMargins(20, 0, 0, 0)
        resize_type_layout.addWidget(QLabel('Icon Type:'))
        self.resize_type_group = QButtonGroup(self)
        self.resize_type_item = QRadioButton('Items')
        self.resize_type_item.setChecked(True)
        self.resize_type_skill = QRadioButton('Skills')
        self.resize_type_group.addButton(self.resize_type_item)
        self.resize_type_group.addButton(self.resize_type_skill)
        resize_type_layout.addWidget(self.resize_type_item)
        resize_type_layout.addWidget(self.resize_type_skill)
        resize_type_layout.addStretch()
        self.resize_type_widget.setLayout(resize_type_layout)
        import_controls_layout.addWidget(self.resize_type_widget)
        self.import_controls_widget.setLayout(import_controls_layout)
        self.import_controls_widget.setEnabled(False)
        icons_layout.addWidget(self.import_controls_widget)
        icons_group.setLayout(icons_layout)
        create_layout.addWidget(icons_group)
        create_layout.addStretch()
        self.btn_generate_atlas = QPushButton('Generate Atlas')
        self.btn_generate_atlas.setStyleSheet('QPushButton { font-size: 12pt; font-weight: bold; padding: 10px; background-color: #2a5a8a; } QPushButton:hover { background-color: #3a6a9a; } QPushButton:disabled { background-color: #444; color: #666; }')
        self.btn_generate_atlas.clicked.connect(self.generate_new_atlas)
        self.btn_generate_atlas.setEnabled(False)
        create_layout.addWidget(self.btn_generate_atlas)
        self.create_status_label = QLabel('')
        self.create_status_label.setStyleSheet('QLabel { color: #888; font-style: italic; }')
        self.create_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        create_layout.addWidget(self.create_status_label)
        prefs_tab = QWidget()
        self.tabs.addTab(prefs_tab, 'Preferences')
        prefs_layout = QVBoxLayout()
        prefs_tab.setLayout(prefs_layout)
        prefs_layout.addWidget(QLabel('BG3 Data Path:'))
        bg3_prefs_layout = QHBoxLayout()
        self.bg3_prefs_edit = QLineEdit(self.bg3_data)
        bg3_prefs_layout.addWidget(self.bg3_prefs_edit)
        btn_browse_bg3_prefs = QPushButton('Browse')
        btn_browse_bg3_prefs.clicked.connect(lambda: self.browse_path(self.bg3_prefs_edit, 'Select BG3 Data Directory'))
        bg3_prefs_layout.addWidget(btn_browse_bg3_prefs)
        prefs_layout.addLayout(bg3_prefs_layout)
        prefs_layout.addWidget(QLabel('Temp Directory:'))
        temp_layout = QHBoxLayout()
        self.temp_edit = QLineEdit(self.temp_dir)
        temp_layout.addWidget(self.temp_edit)
        btn_browse_temp = QPushButton('Browse')
        btn_browse_temp.clicked.connect(lambda: self.browse_path(self.temp_edit, 'Select Temp Directory'))
        temp_layout.addWidget(btn_browse_temp)
        prefs_layout.addLayout(temp_layout)
        prefs_layout.addWidget(QLabel('Output Path:'))
        output_layout = QHBoxLayout()
        self.output_edit = QLineEdit(self.output_path)
        output_layout.addWidget(self.output_edit)
        btn_browse_output = QPushButton('Browse')
        btn_browse_output.clicked.connect(lambda: self.browse_path(self.output_edit, 'Select Output Directory'))
        output_layout.addWidget(btn_browse_output)
        prefs_layout.addLayout(output_layout)
        prefs_layout.addWidget(QLabel('Zip Output Path:'))
        zip_layout = QHBoxLayout()
        self.zip_edit = QLineEdit(self.zip_output_path)
        zip_layout.addWidget(self.zip_edit)
        btn_browse_zip = QPushButton('Browse')
        btn_browse_zip.clicked.connect(lambda: self.browse_path(self.zip_edit, 'Select Zip Output Directory'))
        zip_layout.addWidget(btn_browse_zip)
        prefs_layout.addLayout(zip_layout)
        prefs_layout.addWidget(QLabel('Preview Size:'))
        self.preview_combo = QComboBox()
        self.preview_combo.addItems(['512x512', 'Full Atlas Size'])
        self.preview_combo.setCurrentText(self.preview_size_option)
        self.preview_combo.currentTextChanged.connect(self.update_preview_size)
        prefs_layout.addWidget(self.preview_combo)
        prefs_layout.addWidget(QLabel(''))
        logging_label = QLabel('Logging Settings')
        logging_label.setStyleSheet('QLabel { font-weight: bold; font-size: 12pt; color: #66ff66; }')
        prefs_layout.addWidget(logging_label)
        self.log_enabled_checkbox = QCheckBox('Enable session logging to file')
        self.log_enabled_checkbox.setChecked(self.prefs.get('log_enabled', True))
        self.log_enabled_checkbox.setToolTip('When enabled, creates a timestamped log file for each session')
        prefs_layout.addWidget(self.log_enabled_checkbox)
        prefs_layout.addWidget(QLabel('Log Directory:'))
        log_dir_layout = QHBoxLayout()
        default_log_dir = self.prefs.get('log_directory', os.path.join(os.path.dirname(__file__), 'logs'))
        self.log_dir_edit = QLineEdit(default_log_dir)
        self.log_dir_edit.setToolTip('Directory where log files will be saved')
        log_dir_layout.addWidget(self.log_dir_edit)
        btn_browse_log_dir = QPushButton('Browse')
        btn_browse_log_dir.clicked.connect(lambda: self.browse_path(self.log_dir_edit, 'Select Log Directory'))
        log_dir_layout.addWidget(btn_browse_log_dir)
        prefs_layout.addLayout(log_dir_layout)
        log_level_layout = QHBoxLayout()
        log_level_layout.addWidget(QLabel('Console Display Level:'))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
        self.log_level_combo.setCurrentText(self.prefs.get('log_level', 'DEBUG'))
        self.log_level_combo.setToolTip('Controls console output verbosity. File log ALWAYS captures everything at DEBUG level.\nDEBUG: Show all | INFO: General info | WARNING/ERROR: Issues only')
        log_level_layout.addWidget(self.log_level_combo)
        log_level_layout.addStretch()
        prefs_layout.addLayout(log_level_layout)
        log_level_note = QLabel('Note: Log file always captures everything (DEBUG), this setting only affects console display')
        log_level_note.setStyleSheet('QLabel { color: #88aaff; font-style: italic; font-size: 9pt; margin-left: 20px; }')
        prefs_layout.addWidget(log_level_note)
        max_log_layout = QHBoxLayout()
        max_log_layout.addWidget(QLabel('Keep last N log files:'))
        self.max_log_files_spinbox = QSpinBox()
        self.max_log_files_spinbox.setMinimum(1)
        self.max_log_files_spinbox.setMaximum(100)
        self.max_log_files_spinbox.setValue(self.prefs.get('max_log_files', 10))
        self.max_log_files_spinbox.setToolTip('Automatically deletes older log files, keeping only the most recent N files')
        max_log_layout.addWidget(self.max_log_files_spinbox)
        max_log_layout.addStretch()
        prefs_layout.addLayout(max_log_layout)
        log_note = QLabel('Note: Logging changes take effect on next application start')
        log_note.setStyleSheet('QLabel { color: #ffaa00; font-style: italic; font-size: 9pt; }')
        prefs_layout.addWidget(log_note)
        prefs_layout.addWidget(QLabel(''))
        texconv_label = QLabel('Texconv Settings (DDS Conversion Tool)')
        texconv_label.setStyleSheet('QLabel { font-weight: bold; font-size: 12pt; color: #66ff66; }')
        prefs_layout.addWidget(texconv_label)
        self.texconv_status_label = QLabel('Checking texconv...')
        self.texconv_status_label.setStyleSheet('QLabel { color: #ffaa00; font-style: italic; }')
        prefs_layout.addWidget(self.texconv_status_label)
        prefs_layout.addWidget(QLabel('Texconv Path (optional - leave blank for auto-detect):'))
        texconv_path_layout = QHBoxLayout()
        texconv_path_default = self.prefs.get('texconv_path', '')
        self.texconv_path_edit = QLineEdit(texconv_path_default)
        self.texconv_path_edit.setPlaceholderText('Auto-detect from: script_dir/texconv/, system PATH')
        self.texconv_path_edit.setToolTip('Leave blank to auto-detect, or specify full path to texconv.exe')
        texconv_path_layout.addWidget(self.texconv_path_edit)
        btn_browse_texconv = QPushButton('Browse')
        btn_browse_texconv.clicked.connect(self.browse_texconv)
        texconv_path_layout.addWidget(btn_browse_texconv)
        prefs_layout.addLayout(texconv_path_layout)
        texconv_buttons_layout = QHBoxLayout()
        self.btn_download_texconv = QPushButton('Download Texconv')
        self.btn_download_texconv.setToolTip('Download texconv.exe from Microsoft DirectXTex (official source)')
        self.btn_download_texconv.clicked.connect(self.download_texconv_clicked)
        texconv_buttons_layout.addWidget(self.btn_download_texconv)
        btn_check_texconv = QPushButton('Check Status')
        btn_check_texconv.setToolTip('Verify texconv.exe is found and working')
        btn_check_texconv.clicked.connect(self.update_texconv_status)
        texconv_buttons_layout.addWidget(btn_check_texconv)
        texconv_buttons_layout.addStretch()
        prefs_layout.addLayout(texconv_buttons_layout)
        texconv_info = QLabel('Texconv is used for PNG↔DDS conversion. Will be downloaded to script_dir/texconv/')
        texconv_info.setStyleSheet('QLabel { color: #88aaff; font-style: italic; font-size: 9pt; }')
        prefs_layout.addWidget(texconv_info)
        self.update_texconv_status()
        prefs_layout.addStretch()
        btn_save_prefs = QPushButton('Save Preferences')
        btn_save_prefs.clicked.connect(self.save_preferences)
        prefs_layout.addWidget(btn_save_prefs)
        self.refresh_mods()
        self.update_create_atlas_status()

    def browse_bg3(self):
        dir_ = QFileDialog.getExistingDirectory(self, 'Select BG3 Data folder', self.bg3_edit.text())
        if dir_:
            self.bg3_edit.setText(dir_)
            self.refresh_mods()

    def refresh_mods(self):
        bg3 = self.bg3_edit.text().strip()
        if not bg3 or not os.path.isdir(bg3):
            self.mod_combo.clear()
            self.create_mod_combo.clear()
            return
        public = os.path.join(bg3, 'Public')
        generated = os.path.join(bg3, 'Generated', 'Public')
        mods = set()
        if os.path.isdir(public):
            mods.update([d for d in os.listdir(public) if os.path.isdir(os.path.join(public, d))])
        if os.path.isdir(generated):
            mods.update([d for d in os.listdir(generated) if os.path.isdir(os.path.join(generated, d))])
        mods = sorted(mods)
        current = self.mod_combo.currentText()
        self.mod_combo.blockSignals(True)
        self.mod_combo.clear()
        self.mod_combo.addItems(mods)
        self.mod_combo.blockSignals(False)
        if current in mods:
            self.mod_combo.setCurrentText(current)
        self.create_mod_combo.blockSignals(True)
        self.create_mod_combo.clear()
        self.create_mod_combo.addItems(mods)
        self.create_mod_combo.blockSignals(False)
        if current in mods:
            self.create_mod_combo.setCurrentText(current)

    def toggle_mode(self):
        print(Fore.CYAN + f'\n--- MODE CHANGE ---')
        if self.mode_standalone.isChecked():
            self.mode = 'standalone'
            print(Fore.GREEN + f'✓ Switched to STANDALONE mode')
            self.standalone_group.setVisible(True)
            self.project_group.setVisible(False)
        else:
            self.mode = 'mod_project'
            print(Fore.GREEN + f'✓ Switched to MOD PROJECT mode')
            self.standalone_group.setVisible(False)
            self.project_group.setVisible(True)
        print(Fore.CYAN + f'-------------------\n')

    def on_mod_selection_changed(self):
        mod = self.mod_combo.currentText()
        if mod and self.mode == 'mod_project':
            self.btn_load_project_atlas.setEnabled(True)
            print(Fore.GREEN + f'[DEBUG] Mod selected: {mod} - Load button enabled')
        else:
            self.btn_load_project_atlas.setEnabled(False)
            print(Fore.GREEN + f'[DEBUG] No mod selected - Load button disabled')
        if mod and mod != self.create_mod_combo.currentText():
            self.create_mod_combo.blockSignals(True)
            self.create_mod_combo.setCurrentText(mod)
            self.create_mod_combo.blockSignals(False)
        self.update_create_atlas_status()

    def load_atlas_from_project(self):
        print(Fore.CYAN + f"\n{'=' * 60}")
        print(Fore.CYAN + f'USER ACTION: Load Atlas from Project')
        print(Fore.CYAN + f"{'=' * 60}")
        bg3_data = self.bg3_edit.text().strip()
        mod = self.mod_combo.currentText()
        if not mod:
            print(Fore.RED + f'[ERROR] No mod selected')
            print(Fore.RED + f'[POPUP] Showing error: Please select a mod from the dropdown first.')
            QMessageBox.warning(self, 'Error', 'Please select a mod from the dropdown first.')
            return
        if not bg3_data or not os.path.exists(bg3_data):
            print(Fore.RED + f'[ERROR] Invalid BG3 Data path: {bg3_data}')
            print(Fore.RED + f'[POPUP] Showing error: Invalid BG3 Data path.')
            QMessageBox.warning(self, 'Error', 'Invalid BG3 Data path. Please set it in preferences.')
            return
        print(Fore.GREEN + f'[DEBUG] Selected mod: {mod}')
        print(Fore.GREEN + f'[DEBUG] BG3 Data path: {bg3_data}')
        scan_paths = [os.path.join(bg3_data, 'Mods', mod, 'GUI'), os.path.join(bg3_data, 'Public', mod, 'GUI')]
        found_lsx_files = []
        for scan_path in scan_paths:
            print(Fore.CYAN + f'[SCAN] Searching for .lsx files in: {scan_path}')
            if os.path.exists(scan_path):
                for file in os.listdir(scan_path):
                    if file.endswith('.lsx'):
                        full_path = os.path.join(scan_path, file)
                        found_lsx_files.append(full_path)
                        print(Fore.GREEN + f'✓ Found .lsx file: {full_path}')
        if not found_lsx_files:
            print(Fore.RED + f'[ERROR] No .lsx files found in mod GUI folders')
            error_msg = f'No .lsx files found in:\n{scan_paths[0]}\n{scan_paths[1]}\n\nPlease ensure your mod has atlas files in the GUI folder.'
            print(Fore.RED + f'[POPUP] Showing error: {error_msg}')
            QMessageBox.warning(self, 'No Atlas Files Found', error_msg)
            return
        lsx_path = None
        if len(found_lsx_files) == 1:
            lsx_path = found_lsx_files[0]
            print(Fore.GREEN + f'✓ Auto-selected single .lsx file: {lsx_path}')
        else:
            print(Fore.CYAN + f'[USER] Multiple .lsx files found ({len(found_lsx_files)}), prompting user to choose...')
            file_names = [os.path.basename(f) for f in found_lsx_files]
            print(Fore.GREEN + f'[POPUP] Showing selection dialog with options: {file_names}')
            chosen_file, ok = QInputDialog.getItem(self, 'Select Atlas File', f'Found {len(found_lsx_files)} atlas files. Choose one:', file_names, 0, False)
            if ok and chosen_file:
                lsx_path = found_lsx_files[file_names.index(chosen_file)]
                print(Fore.GREEN + f'✓ User selected: {lsx_path}')
            else:
                print(Fore.YELLOW + f'[WARNING] User cancelled .lsx selection')
                return
        self.project_lsx_edit.setText(lsx_path)
        print(Fore.CYAN + f'[OPERATION] Parsing LSX file in mod project mode...')
        self.dom, self.atlas_path, self.icons, self.atlas_size, self.tile_size = parse_lsx(lsx_path, bg3_data, 'mod_project')
        if self.dom is None:
            print(Fore.RED + f'[ERROR] Failed to parse LSX file')
            self.atlas_status_label.setText('Failed to load atlas')
            self.atlas_status_label.setStyleSheet('QLabel { color: #ff4444; font-style: italic; }')
            return
        if self.atlas_path is None or not os.path.exists(self.atlas_path):
            print(Fore.YELLOW + f'[WARNING] DDS not found at resolved path: {self.atlas_path}')
            print(Fore.YELLOW + f'[POPUP] Prompting user: Could not find DDS. Browse manually?')
            reply = QMessageBox.question(self, 'DDS Not Found', f'Could not find DDS at {self.atlas_path}.\n\nBrowse manually?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                print(Fore.CYAN + f'[USER] User chose to browse for DDS manually')
                default_dir = self.get_default_file_dialog_path()
                print(Fore.GREEN + f"[DEBUG] Default browse path: {(default_dir if default_dir else '(current directory)')}")
                dds_path = QFileDialog.getOpenFileName(self, 'Select DDS', default_dir, '*.dds')[0]
                if dds_path:
                    self.atlas_path = dds_path
                    print(Fore.GREEN + f'✓ User selected DDS: {self.atlas_path}')
                else:
                    print(Fore.RED + f'[ERROR] User cancelled DDS selection')
                    print(Fore.RED + f'[POPUP] Showing error: DDS path required.')
                    QMessageBox.warning(self, 'Error', 'DDS path required.')
                    return
            else:
                print(Fore.RED + f'[ERROR] User declined to browse for DDS')
                print(Fore.RED + f'[POPUP] Showing error: Cannot load atlas without DDS.')
                QMessageBox.warning(self, 'Error', 'Cannot load atlas without DDS.')
                return
        self.grid_size = self.atlas_size // self.tile_size
        print(Fore.GREEN + f'[DEBUG] Calculated grid size: {self.grid_size}x{self.grid_size}')
        if self.atlas_size % self.tile_size != 0:
            print(Fore.RED + f'[ERROR] Atlas size not divisible by tile size: {self.atlas_size} % {self.tile_size} != 0')
            error_msg = f'Invalid atlas: atlas_size {self.atlas_size} not divisible by tile_size {self.tile_size}.'
            print(Fore.RED + f'[POPUP] Showing error: {error_msg}')
            QMessageBox.warning(self, 'Error', error_msg)
            return
        print(Fore.CYAN + f'[OPERATION] Converting DDS to PNG for preview...')
        temp_png = os.path.join(TEMP_DIR, 'temp_gui.png')
        dds_to_png(self.atlas_path, temp_png)
        print(Fore.GREEN + f'[DEBUG] Loading and resizing atlas image...')
        self.atlas_im = resize_with_alpha(Image.open(temp_png), (self.atlas_size, self.atlas_size), Image.BICUBIC)
        print(Fore.GREEN + f'✓ Atlas image loaded: {self.atlas_im.size}')
        print(Fore.CYAN + f'[OPERATION] Updating preview...')
        self.update_preview()
        print(Fore.CYAN + f'[OPERATION] Populating icon combo box...')
        self.combo_icons.clear()
        for icon in sorted(self.icons, key=lambda i: i['mapkey']):
            self.combo_icons.addItem(icon['mapkey'])
        print(Fore.GREEN + f'✓ Added {self.combo_icons.count()} icons to dropdown')
        self.dom_modified = False
        atlas_name = os.path.basename(lsx_path)
        self.atlas_status_label.setText(f'Loaded: {atlas_name}')
        self.atlas_status_label.setStyleSheet('QLabel { color: #44ff44; font-weight: bold; }')
        self.btn_load_project_atlas.setText('Reload Atlas')
        print(Fore.GREEN + f"\n{'=' * 60}")
        print(Fore.GREEN + f'ATLAS LOADED SUCCESSFULLY FROM PROJECT')
        print(Fore.GREEN + f"{'=' * 60}\n")

    def get_default_file_dialog_path(self):
        if self.mode == 'mod_project':
            bg3_data = self.bg3_edit.text().strip()
            mod = self.mod_combo.currentText()
            if mod and bg3_data and os.path.exists(bg3_data):
                public_path = os.path.join(bg3_data, 'Public', mod)
                if os.path.exists(public_path):
                    return public_path
                mods_path = os.path.join(bg3_data, 'Mods', mod)
                if os.path.exists(mods_path):
                    return mods_path
        return ''

    def browse_path(self, edit, title, filter='*'):
        default_path = self.get_default_file_dialog_path()
        if 'Directory' in title:
            path = QFileDialog.getExistingDirectory(self, title, default_path)
        else:
            path = QFileDialog.getOpenFileName(self, title, default_path, filter)[0]
        if path:
            edit.setText(path)

    def browse_texconv(self):
        default_path = self.get_default_file_dialog_path()
        file_path, _ = QFileDialog.getOpenFileName(self, 'Select texconv.exe', default_path, 'Executable Files (*.exe);;All Files (*.*)')
        if file_path:
            self.texconv_path_edit.setText(file_path)
            self.update_texconv_status()

    def download_texconv_clicked(self):
        print(Fore.CYAN + '\n[USER ACTION] Download Texconv')
        reply = QMessageBox.question(self, 'Download Texconv', 'Download texconv.exe from Microsoft DirectXTex (official source)?\n\nWill be saved to: script_dir/texconv/texconv.exe\nSize: ~2-3 MB', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            print(Fore.YELLOW + '[CANCELLED] User cancelled download')
            return
        script_dir = os.path.dirname(__file__)
        dest_dir = os.path.join(script_dir, 'texconv')
        print(Fore.CYAN + f'[OPERATION] Downloading texconv to: {dest_dir}')
        texconv_path = download_texconv(dest_dir)
        if texconv_path:
            global TEXCONV_PATH
            TEXCONV_PATH = texconv_path
            self.texconv_path_edit.setText(texconv_path)
            self.update_texconv_status()
            QMessageBox.information(self, 'Success', f'Texconv downloaded successfully!\n\nPath: {texconv_path}\n\nYou can now use DDS conversion features.')
        else:
            QMessageBox.warning(self, 'Download Failed', 'Failed to download texconv.exe\n\nYou can manually download from:\nhttps://github.com/microsoft/DirectXTex/releases\n\nExtract texconv.exe and select it using the Browse button.')

    def update_texconv_status(self):
        global TEXCONV_PATH
        custom_path = self.texconv_path_edit.text().strip()
        TEXCONV_PATH = find_texconv(custom_path if custom_path else None)
        if TEXCONV_PATH:
            self.texconv_status_label.setText(f'✓ Found: {TEXCONV_PATH}')
            self.texconv_status_label.setStyleSheet('QLabel { color: #66ff66; font-weight: bold; }')
            self.btn_download_texconv.setText('Re-download Texconv')
        else:
            self.texconv_status_label.setText("✗ Not found - Click 'Download Texconv' to install")
            self.texconv_status_label.setStyleSheet('QLabel { color: #ff6666; font-weight: bold; }')
            self.btn_download_texconv.setText('Download Texconv')

    def load_atlas(self):
        print(Fore.CYAN + f"\n{'=' * 60}")
        print(Fore.CYAN + f'USER ACTION: Load Atlas')
        print(Fore.CYAN + f"{'=' * 60}")
        bg3_data = self.bg3_edit.text().strip()
        print(Fore.GREEN + f'[DEBUG] BG3 Data path: {bg3_data}')
        print(Fore.GREEN + f'[DEBUG] Current mode: {self.mode}')
        if self.mode == 'standalone':
            print(Fore.CYAN + f'[MODE] Standalone mode selected')
            lsx_path = self.standalone_lsx_edit.text()
            print(Fore.GREEN + f'[DEBUG] LSX path from input: {lsx_path}')
            if not lsx_path or not os.path.exists(lsx_path):
                print(Fore.RED + f'[ERROR] Invalid standalone .lsx path: {lsx_path}')
                print(Fore.RED + f'[POPUP] Showing error: Invalid standalone .lsx path.')
                QMessageBox.warning(self, 'Error', 'Invalid standalone .lsx path.')
                return
            dds_path = self.standalone_dds_edit.text()
            print(Fore.GREEN + f'[DEBUG] DDS path from input: {dds_path}')
            if not dds_path or not os.path.exists(dds_path):
                print(Fore.RED + f'[ERROR] Invalid standalone DDS path: {dds_path}')
                print(Fore.RED + f'[POPUP] Showing error: Invalid standalone DDS path.')
                QMessageBox.warning(self, 'Error', 'Invalid standalone DDS path.')
                return
            print(Fore.CYAN + f'[OPERATION] Parsing LSX file...')
            self.dom, self.atlas_path, self.icons, self.atlas_size, self.tile_size = parse_lsx(lsx_path, None, 'standalone')
            if self.dom is None:
                print(Fore.RED + f'[ERROR] Failed to parse LSX file')
                return
            self.atlas_path = dds_path
            print(Fore.GREEN + f'[DEBUG] Using manual DDS path: {self.atlas_path}')
        else:
            print(Fore.CYAN + f'[MODE] Mod project mode selected')
            lsx_path = self.project_lsx_edit.text()
            print(Fore.GREEN + f'[DEBUG] Project LSX path from input: {lsx_path}')
            if not lsx_path or not os.path.isfile(lsx_path):
                if lsx_path:
                    print(Fore.YELLOW + f'[WARNING] LSX path does not exist or is not a file: {lsx_path}')
                else:
                    print(Fore.YELLOW + f'[WARNING] No LSX path provided')
                print(Fore.YELLOW + f'[WARNING] Attempting to scan for .lsx files...')
                mod = self.mod_combo.currentText()
                if mod and bg3_data:
                    scan_paths = [os.path.join(bg3_data, 'Mods', mod, 'GUI'), os.path.join(bg3_data, 'Public', mod, 'GUI')]
                    found_lsx_files = []
                    for scan_path in scan_paths:
                        print(Fore.GREEN + f'[DEBUG] Scanning for .lsx files in: {scan_path}')
                        if os.path.exists(scan_path):
                            for file in os.listdir(scan_path):
                                if file.endswith('.lsx'):
                                    full_path = os.path.join(scan_path, file)
                                    found_lsx_files.append(full_path)
                                    print(Fore.GREEN + f'✓ Found .lsx file: {full_path}')
                    if not found_lsx_files:
                        print(Fore.RED + f'[ERROR] No .lsx files found in mod GUI folders')
                        print(Fore.RED + f'[POPUP] Showing error: No .lsx files found in mod GUI folders. Please select manually.')
                        QMessageBox.warning(self, 'Error', 'No .lsx files found in mod GUI folders. Please select manually.')
                        return
                    elif len(found_lsx_files) == 1:
                        lsx_path = found_lsx_files[0]
                        print(Fore.GREEN + f'✓ Auto-selected single .lsx file: {lsx_path}')
                        self.project_lsx_edit.setText(lsx_path)
                    else:
                        print(Fore.CYAN + f'[USER] Multiple .lsx files found, prompting user to choose...')
                        file_names = [os.path.basename(f) for f in found_lsx_files]
                        chosen_file, ok = QInputDialog.getItem(self, 'Select LSX File', f'Found {len(found_lsx_files)} .lsx files. Choose one:', file_names, 0, False)
                        if ok and chosen_file:
                            lsx_path = found_lsx_files[file_names.index(chosen_file)]
                            print(Fore.GREEN + f'✓ User selected: {lsx_path}')
                            self.project_lsx_edit.setText(lsx_path)
                        else:
                            print(Fore.YELLOW + f'[WARNING] User cancelled LSX selection')
                            return
                else:
                    print(Fore.RED + f'[ERROR] Invalid project .lsx path and cannot auto-scan without mod selection')
                    print(Fore.RED + f'[POPUP] Showing error: Invalid project .lsx path.')
                    QMessageBox.warning(self, 'Error', 'Invalid project .lsx path.')
                    return
            print(Fore.CYAN + f'[OPERATION] Parsing LSX file in mod project mode...')
            self.dom, self.atlas_path, self.icons, self.atlas_size, self.tile_size = parse_lsx(lsx_path, bg3_data, 'mod_project')
            if self.dom is None:
                print(Fore.RED + f'[ERROR] Failed to parse LSX file')
                return
            if self.atlas_path is None or not os.path.exists(self.atlas_path):
                print(Fore.YELLOW + f'[WARNING] DDS not found at resolved path: {self.atlas_path}')
                print(Fore.YELLOW + f'[POPUP] Prompting user: Could not find DDS at {self.atlas_path}. Browse manually?')
                reply = QMessageBox.question(self, 'DDS Not Found', f'Could not find DDS at {self.atlas_path}. Browse manually?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    print(Fore.CYAN + f'[USER] User chose to browse for DDS manually')
                    default_path = self.get_default_file_dialog_path()
                    print(Fore.GREEN + f"[DEBUG] Default browse path: {(default_path if default_path else '(current directory)')}")
                    dds_path = QFileDialog.getOpenFileName(self, 'Select DDS', default_path, '*.dds')[0]
                    if dds_path:
                        self.atlas_path = dds_path
                        print(Fore.GREEN + f'✓ User selected DDS: {self.atlas_path}')
                    else:
                        print(Fore.RED + f'[ERROR] User cancelled DDS selection')
                        print(Fore.RED + f'[POPUP] Showing error: DDS path required.')
                        QMessageBox.warning(self, 'Error', 'DDS path required.')
                        return
                else:
                    print(Fore.RED + f'[ERROR] User declined to browse for DDS')
                    print(Fore.RED + f'[POPUP] Showing error: Cannot load atlas without DDS.')
                    QMessageBox.warning(self, 'Error', 'Cannot load atlas without DDS.')
                    return
        self.grid_size = self.atlas_size // self.tile_size
        print(Fore.GREEN + f'[DEBUG] Calculated grid size: {self.grid_size}x{self.grid_size}')
        if self.atlas_size % self.tile_size != 0:
            print(Fore.RED + f'[ERROR] Atlas size not divisible by tile size: {self.atlas_size} % {self.tile_size} != 0')
            error_msg = f'Invalid atlas: atlas_size {self.atlas_size} not divisible by tile_size {self.tile_size}.'
            print(Fore.RED + f'[POPUP] Showing error: {error_msg}')
            QMessageBox.warning(self, 'Error', error_msg)
            return
        print(Fore.CYAN + f'[OPERATION] Converting DDS to PNG for preview...')
        temp_png = os.path.join(TEMP_DIR, 'temp_gui.png')
        dds_to_png(self.atlas_path, temp_png)
        print(Fore.GREEN + f'[DEBUG] Loading and resizing atlas image...')
        self.atlas_im = resize_with_alpha(Image.open(temp_png), (self.atlas_size, self.atlas_size), Image.BICUBIC)
        print(Fore.GREEN + f'✓ Atlas image loaded: {self.atlas_im.size}')
        print(Fore.CYAN + f'[OPERATION] Updating preview...')
        self.update_preview()
        print(Fore.CYAN + f'[OPERATION] Populating icon combo box...')
        self.combo_icons.clear()
        for icon in sorted(self.icons, key=lambda i: i['mapkey']):
            self.combo_icons.addItem(icon['mapkey'])
        print(Fore.GREEN + f'✓ Added {self.combo_icons.count()} icons to dropdown')
        self.dom_modified = False
        if self.mode == 'standalone':
            atlas_name = os.path.basename(self.standalone_lsx_edit.text())
        else:
            atlas_name = os.path.basename(self.project_lsx_edit.text())
        self.atlas_status_label.setText(f'Loaded: {atlas_name}')
        self.atlas_status_label.setStyleSheet('QLabel { color: #44ff44; font-weight: bold; }')
        print(Fore.GREEN + f'✓ Status updated: {atlas_name}')
        print(Fore.GREEN + f"\n{'=' * 60}")
        print(Fore.GREEN + f'ATLAS LOADED SUCCESSFULLY')
        print(Fore.GREEN + f"{'=' * 60}\n")

    def update_preview(self):
        if self.atlas_im:
            self.preview_label = InteractivePreviewLabel(self.icons, min(self.preview_size, self.atlas_size), self.atlas_size, self.tile_size, self)
            self.preview_label.setFixedSize(min(self.preview_size, self.atlas_size), min(self.preview_size, self.atlas_size))
            preview = resize_with_alpha(self.atlas_im, (min(self.preview_size, self.atlas_size), min(self.preview_size, self.atlas_size)), Image.BICUBIC)
            qim = self.pil_to_qimage(preview)
            pix = QPixmap.fromImage(qim)
            self.preview_label.setPixmap(pix)
            central_layout = self.centralWidget().layout()
            if central_layout.itemAt(1).widget() != self.preview_label:
                if central_layout.itemAt(1).widget():
                    central_layout.itemAt(1).widget().deleteLater()
                central_layout.addWidget(self.preview_label)

    def update_preview_size(self):
        self.preview_size = 512 if self.preview_combo.currentText() == '512x512' else self.atlas_size if self.atlas_size else 1024
        self.update_preview()

    def pil_to_qimage(self, pil_im):
        pil_im = pil_im.convert('RGBA')
        data = pil_im.tobytes('raw', 'RGBA')
        qim = QImage(data, pil_im.size[0], pil_im.size[1], QImage.Format.Format_RGBA8888)
        return qim

    def replace_icon(self):
        print(Fore.CYAN + f"\n{'=' * 60}")
        print(Fore.CYAN + f'USER ACTION: Replace Icon')
        print(Fore.CYAN + f"{'=' * 60}")
        if not self.atlas_im:
            print(Fore.RED + f'[ERROR] No atlas loaded')
            print(Fore.RED + f"[POPUP] Showing error: {self.strings['error_load']}")
            QMessageBox.warning(self, 'Error', self.strings['error_load'])
            return
        selected_key = self.combo_icons.currentText()
        print(Fore.GREEN + f'[DEBUG] Selected icon: {selected_key}')
        if not selected_key:
            print(Fore.YELLOW + f'[WARNING] No icon selected')
            return
        print(Fore.CYAN + f'[USER] Opening file dialog for PNG selection...')
        default_path = self.get_default_file_dialog_path()
        print(Fore.GREEN + f'[DEBUG] Default file dialog path: {default_path}')
        png_path = QFileDialog.getOpenFileName(self, self.strings['select_png_replace'], default_path, 'PNG (*.png)')[0]
        if not png_path:
            print(Fore.YELLOW + f'[WARNING] User cancelled PNG selection')
            return
        print(Fore.GREEN + f'✓ User selected PNG: {png_path}')
        print(Fore.GREEN + f'[DEBUG] PNG file exists: {os.path.exists(png_path)}')
        for icon in self.icons:
            if icon['mapkey'] == selected_key:
                print(Fore.CYAN + f"[OPERATION] Replacing icon '{selected_key}'")
                print(Fore.GREEN + f"[DEBUG] Icon UV: u1={icon['u1']:.3f}, v1={icon['v1']:.3f}, u2={icon['u2']:.3f}, v2={icon['v2']:.3f}")
                col, row = get_grid_slot(icon['u1'], icon['v1'], self.grid_size)
                print(Fore.GREEN + f'[DEBUG] Grid position: col={col}, row={row}')
                x = col * self.tile_size
                y = row * self.tile_size
                print(Fore.GREEN + f'[DEBUG] Pixel position: x={x}, y={y}')
                print(Fore.GREEN + f'[DEBUG] Clearing existing tile area...')
                clear_im = Image.new('RGBA', (self.tile_size, self.tile_size), (0, 0, 0, 0))
                self.atlas_im.paste(clear_im, (x, y))
                print(Fore.GREEN + f'[DEBUG] Loading and resizing new icon to {self.tile_size}x{self.tile_size}...')
                new_im = resize_with_alpha(Image.open(png_path), (self.tile_size, self.tile_size), Image.BICUBIC)
                print(Fore.GREEN + f'[DEBUG] New icon size: {new_im.size}, mode: {new_im.mode}')
                print(Fore.GREEN + f'[DEBUG] Pasting new icon into atlas...')
                self.atlas_im.paste(new_im, (x, y), new_im if 'A' in new_im.getbands() else None)
                print(Fore.CYAN + f'[OPERATION] Updating preview...')
                self.update_preview()
                print(Fore.GREEN + f"✓ Successfully replaced icon '{selected_key}'")
                success_msg = self.strings['success_replace'].format(key=selected_key)
                print(Fore.GREEN + f'[POPUP] Showing success: {success_msg}')
                QMessageBox.information(self, 'Success', success_msg)
                return

    def add_icon(self):
        print(Fore.CYAN + f"\n{'=' * 60}")
        print(Fore.CYAN + f'USER ACTION: Add New Icon')
        print(Fore.CYAN + f"{'=' * 60}")
        if not self.atlas_im:
            print(Fore.RED + f'[ERROR] No atlas loaded')
            print(Fore.RED + f"[POPUP] Showing error: {self.strings['error_load']}")
            QMessageBox.warning(self, 'Error', self.strings['error_load'])
            return
        print(Fore.CYAN + f'[USER] Opening file dialog for PNG selection...')
        default_path = self.get_default_file_dialog_path()
        print(Fore.GREEN + f'[DEBUG] Default file dialog path: {default_path}')
        png_path = QFileDialog.getOpenFileName(self, self.strings['select_png_add'], default_path, 'PNG (*.png)')[0]
        if not png_path:
            print(Fore.YELLOW + f'[WARNING] User cancelled PNG selection')
            return
        print(Fore.GREEN + f'✓ User selected PNG: {png_path}')
        mapkey = os.path.basename(png_path).rsplit('.', 1)[0]
        print(Fore.GREEN + f"✓ Auto-extracted MapKey from filename: '{mapkey}'")
        print(Fore.CYAN + f'[INFO] MapKey will be used for atlas UV mapping and must match resize filenames!')
        info_msg = f"Using filename '{mapkey}' as MapKey.\n\nIMPORTANT: When resizing, ensure all icon files have the exact same filename:\n{mapkey}.png"
        print(Fore.GREEN + f'[POPUP] Showing info: {info_msg}')
        QMessageBox.information(self, 'MapKey Confirmed', info_msg)
        print(Fore.CYAN + f'[OPERATION] Searching for free slot in atlas...')
        used_slots = {get_grid_slot(icon['u1'], icon['v1'], self.grid_size) for icon in self.icons}
        print(Fore.GREEN + f'[DEBUG] Used slots: {len(used_slots)}/{self.grid_size * self.grid_size}')
        free_col, free_row = (None, None)
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if (c, r) not in used_slots:
                    free_col, free_row = (c, r)
                    print(Fore.GREEN + f'✓ Found free slot at grid position: col={free_col}, row={free_row}')
                    break
            if free_col is not None:
                break
        if free_col is None:
            print(Fore.RED + f'[ERROR] No free slots available in atlas')
            print(Fore.RED + f"[POPUP] Showing error: {self.strings['error_no_slots']}")
            QMessageBox.warning(self, 'Error', self.strings['error_no_slots'])
            return
        x = free_col * self.tile_size
        y = free_row * self.tile_size
        print(Fore.GREEN + f'[DEBUG] Pixel position: x={x}, y={y}')
        print(Fore.GREEN + f'[DEBUG] Clearing tile area...')
        clear_im = Image.new('RGBA', (self.tile_size, self.tile_size), (0, 0, 0, 0))
        self.atlas_im.paste(clear_im, (x, y))
        print(Fore.GREEN + f'[DEBUG] Loading and resizing new icon to {self.tile_size}x{self.tile_size}...')
        new_im = resize_with_alpha(Image.open(png_path), (self.tile_size, self.tile_size), Image.BICUBIC)
        print(Fore.GREEN + f'[DEBUG] New icon size: {new_im.size}, mode: {new_im.mode}')
        print(Fore.GREEN + f'[DEBUG] Pasting new icon into atlas...')
        self.atlas_im.paste(new_im, (x, y), new_im if 'A' in new_im.getbands() else None)
        u1 = free_col / float(self.grid_size)
        u2 = (free_col + 1) / float(self.grid_size)
        v1 = free_row / float(self.grid_size)
        v2 = (free_row + 1) / float(self.grid_size)
        print(Fore.GREEN + f'[DEBUG] Calculated UV coordinates: u1={u1:.3f}, v1={v1:.3f}, u2={u2:.3f}, v2={v2:.3f}')
        print(Fore.CYAN + f'[OPERATION] Creating XML node for new icon...')
        node_uv = self.dom.createElement('node')
        node_uv.setAttribute('id', 'IconUV')
        attr_k = self.dom.createElement('attribute')
        attr_k.setAttribute('id', 'MapKey')
        attr_k.setAttribute('type', 'FixedString')
        attr_k.setAttribute('value', mapkey)
        node_uv.appendChild(attr_k)
        attr_u1 = self.dom.createElement('attribute')
        attr_u1.setAttribute('id', 'U1')
        attr_u1.setAttribute('type', 'float')
        attr_u1.setAttribute('value', str(u1))
        node_uv.appendChild(attr_u1)
        attr_u2 = self.dom.createElement('attribute')
        attr_u2.setAttribute('id', 'U2')
        attr_u2.setAttribute('type', 'float')
        attr_u2.setAttribute('value', str(u2))
        node_uv.appendChild(attr_u2)
        attr_v1 = self.dom.createElement('attribute')
        attr_v1.setAttribute('id', 'V1')
        attr_v1.setAttribute('type', 'float')
        attr_v1.setAttribute('value', str(v1))
        node_uv.appendChild(attr_v1)
        attr_v2 = self.dom.createElement('attribute')
        attr_v2.setAttribute('id', 'V2')
        attr_v2.setAttribute('type', 'float')
        attr_v2.setAttribute('value', str(v2))
        node_uv.appendChild(attr_v2)
        print(Fore.GREEN + f'✓ Created XML node with all attributes')
        print(Fore.CYAN + f'[OPERATION] Adding node to IconUVList...')
        for region in self.dom.getElementsByTagName('region'):
            if region.getAttribute('id') == 'IconUVList':
                root = region.getElementsByTagName('node')[0]
                children = root.getElementsByTagName('children')[0]
                children.appendChild(node_uv)
                print(Fore.GREEN + f'✓ Node added to DOM')
                break
        print(Fore.GREEN + f'[DEBUG] Updating internal icon list...')
        self.icons.append({'mapkey': mapkey, 'u1': u1, 'u2': u2, 'v1': v1, 'v2': v2})
        print(Fore.GREEN + f'[DEBUG] Total icons now: {len(self.icons)}')
        print(Fore.GREEN + f'[DEBUG] Adding icon to dropdown...')
        self.combo_icons.addItem(mapkey)
        print(Fore.CYAN + f'[OPERATION] Updating preview...')
        self.update_preview()
        self.dom_modified = True
        print(Fore.GREEN + f'[DEBUG] DOM marked as modified')
        print(Fore.GREEN + f"✓ Successfully added new icon '{mapkey}'")
        success_msg = self.strings['success_add'].format(key=mapkey)
        print(Fore.GREEN + f'[POPUP] Showing success: {success_msg}')
        QMessageBox.information(self, 'Success', success_msg)
        print(Fore.CYAN + f'[USER] Prompting for auto-resize...')
        resize_prompt = f"Would you like to automatically resize '{os.path.basename(png_path)}' to all required sizes (72, 144, 192, 380) now?\n\nThis will save you from manually running 'Resize Item PNG' and ensures the filenames match."
        print(Fore.GREEN + f'[POPUP] Showing resize prompt')
        reply = QMessageBox.question(self, 'Auto-Resize Icon?', resize_prompt, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
        if reply == QMessageBox.StandardButton.Yes:
            print(Fore.GREEN + f'✓ User selected YES - auto-resizing icon')
            print(Fore.CYAN + f'[OPERATION] Starting automatic resize operation...')
            if self.mode == 'mod_project':
                mod = self.mod_combo.currentText()
                base_dest = os.path.join(self.bg3_edit.text(), 'Mods', mod, 'GUI')
                print(Fore.GREEN + f'[DEBUG] Mod project mode - using mod: {mod}')
            else:
                base_dest = self.output_edit.text() or os.path.dirname(png_path)
                print(Fore.GREEN + f'[DEBUG] Standalone mode')
            print(Fore.GREEN + f'[DEBUG] Destination directory: {base_dest}')
            resize_png(png_path, skill_mode=False, dest_dir=base_dest)
            print(Fore.GREEN + f"\n{'=' * 60}")
            print(Fore.GREEN + f'AUTO-RESIZE COMPLETE')
            print(Fore.GREEN + f"{'=' * 60}\n")
            complete_msg = f"Icon '{mapkey}' added to atlas and resized to all required sizes!"
            print(Fore.GREEN + f'[POPUP] Showing completion: {complete_msg}')
            QMessageBox.information(self, 'Complete', complete_msg)
        else:
            print(Fore.YELLOW + f'[WARNING] User selected NO - skipping auto-resize')
            print(Fore.CYAN + f"[INFO] User can manually resize later using 'Resize Item PNG' button")

    def save_atlas(self):
        print(Fore.CYAN + f"\n{'=' * 60}")
        print(Fore.CYAN + f'USER ACTION: Save Atlas')
        print(Fore.CYAN + f"{'=' * 60}")
        if not self.atlas_im:
            print(Fore.RED + f'[ERROR] No atlas loaded')
            return
        print(Fore.GREEN + f'[DEBUG] Current mode: {self.mode}')
        if self.mode == 'mod_project':
            print(Fore.CYAN + f'[USER] Prompting for save options...')
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Save Options')
            msg_box.setText('Choose how to save your atlas:')
            msg_box.setIcon(QMessageBox.Icon.Question)
            zip_button = msg_box.addButton('Zip Only', QMessageBox.ButtonRole.YesRole)
            direct_button = msg_box.addButton('Direct Write', QMessageBox.ButtonRole.NoRole)
            both_button = msg_box.addButton('Both', QMessageBox.ButtonRole.AcceptRole)
            cancel_button = msg_box.addButton('Cancel', QMessageBox.ButtonRole.RejectRole)
            msg_box.exec()
            clicked_button = msg_box.clickedButton()
            if clicked_button == cancel_button:
                print(Fore.YELLOW + f'[WARNING] User cancelled save operation')
                return
            zip_only = clicked_button == zip_button
            direct_only = clicked_button == direct_button
            do_both = clicked_button == both_button
            print(Fore.GREEN + f'[DEBUG] Save mode: zip_only={zip_only}, direct_only={direct_only}, both={do_both}')
        else:
            print(Fore.GREEN + f'[DEBUG] Standalone mode - defaulting to zip save')
            zip_only = True
            direct_only = False
            do_both = False
        base_name = None
        timestamp = None
        zip_path = None
        if zip_only or do_both:
            print(Fore.CYAN + f'[USER] Prompting for base name...')
            base_name, ok = QInputDialog.getText(self, 'Save As', 'Enter base name for output (e.g., MyModUpdate):')
            if not ok or not base_name:
                print(Fore.YELLOW + f'[WARNING] User cancelled base name input')
                return
            timestamp = datetime.now().strftime('%d%m%y_%H%M')
            print(Fore.GREEN + f'[DEBUG] Base name: {base_name}')
            print(Fore.GREEN + f'[DEBUG] Timestamp: {timestamp}')
            zip_path = os.path.join(self.zip_edit.text() or os.path.dirname(__file__), f'{base_name}_{timestamp}.zip')
            print(Fore.GREEN + f'[DEBUG] Zip output path: {zip_path}')
        if direct_only or do_both:
            print(Fore.CYAN + f'[OPERATION] Direct write mode')
            if self.mode == 'standalone':
                dds_path = self.standalone_dds_edit.text()
                lsx_path = self.standalone_lsx_edit.text()
            else:
                dds_path = self.atlas_path
                lsx_path = self.project_lsx_edit.text()
            print(Fore.GREEN + f'[DEBUG] DDS output path: {dds_path}')
            print(Fore.GREEN + f'[DEBUG] LSX output path: {lsx_path}')
            temp_png = os.path.join(TEMP_DIR, 'temp_gui.png')
            print(Fore.GREEN + f'[DEBUG] Saving atlas to temporary PNG: {temp_png}')
            dithered = apply_alpha_dither(self.atlas_im, strength=0.5)
            dithered.save(temp_png, 'PNG')
            print(Fore.CYAN + f'[OPERATION] Converting PNG to DDS...')
            png_to_dds(temp_png, dds_path, format='BC3_UNORM', mipmaps=1)
            print(Fore.CYAN + f'[OPERATION] Writing LSX file...')
            with open(lsx_path, 'w', encoding='utf-8') as f:
                xml_str = self.dom.toprettyxml(indent='    ', newl='\n', encoding='UTF-8').decode('utf-8')
                lines = [line for line in xml_str.split('\n') if line.strip()]
                f.write('\n'.join(lines) + '\n')
            print(Fore.GREEN + f'✓ LSX file written')
            if os.path.exists(temp_png):
                os.remove(temp_png)
                print(Fore.GREEN + f'[DEBUG] Cleaned up temporary PNG')
            print(Fore.GREEN + f"\n{'=' * 60}")
            print(Fore.GREEN + f'ATLAS SAVED SUCCESSFULLY (DIRECT WRITE)')
            print(Fore.GREEN + f"{'=' * 60}\n")
            if direct_only:
                success_msg = self.strings['success_save'].format(lsx=lsx_path, dds=dds_path)
                print(Fore.GREEN + f'[POPUP] Showing success: {success_msg}')
                QMessageBox.information(self, 'Success', success_msg)
                return
            else:
                print(Fore.CYAN + f'[OPERATION] Continuing to zip creation (Both mode)...')
        if not (zip_only or do_both):
            return
        print(Fore.CYAN + f'[OPERATION] Creating zip archive: {zip_path}')
        from zipfile import ZipFile
        with ZipFile(zip_path, 'w') as zipf:
            print(Fore.GREEN + f'[DEBUG] Zip file created')
            temp_png = os.path.join(TEMP_DIR, 'temp_gui.png')
            print(Fore.GREEN + f'[DEBUG] Saving atlas to temporary PNG: {temp_png}')
            dithered = apply_alpha_dither(self.atlas_im, strength=0.5)
            dithered.save(temp_png, 'PNG')
            print(Fore.GREEN + f'[DEBUG] Extracting DDS relative path from DOM...')
            for attr in self.dom.getElementsByTagName('attribute'):
                if attr.getAttribute('id') == 'Path':
                    dds_rel_path = attr.getAttribute('value')
                    print(Fore.GREEN + f'✓ Found DDS relative path: {dds_rel_path}')
                    break
            dds_name = os.path.basename(dds_rel_path)
            dds_full_path = os.path.join(os.path.dirname(zip_path), dds_name)
            print(Fore.GREEN + f'[DEBUG] Temporary DDS path: {dds_full_path}')
            print(Fore.CYAN + f'[OPERATION] Converting PNG to DDS...')
            png_to_dds(temp_png, dds_full_path, format='BC3_UNORM', mipmaps=1)
            print(Fore.GREEN + f'[DEBUG] Adding DDS to zip as: {dds_rel_path}')
            zipf.write(dds_full_path, dds_rel_path)
            print(Fore.GREEN + f'✓ DDS added to zip')
            os.remove(dds_full_path)
            print(Fore.GREEN + f'[DEBUG] Cleaned up temporary DDS')
            lsx_rel_path = os.path.splitext(os.path.basename(self.atlas_path))[0] + '.lsx'
            print(Fore.GREEN + f'[DEBUG] LSX relative path for zip: {lsx_rel_path}')
            print(Fore.GREEN + f'[DEBUG] DOM modified: {self.dom_modified}')
            if self.dom_modified:
                print(Fore.CYAN + f'[OPERATION] Writing modified LSX to temporary file...')
                temp_lsx = os.path.join(TEMP_DIR, 'temp.lsx')
                with open(temp_lsx, 'w', encoding='utf-8') as f:
                    xml_str = self.dom.toprettyxml(indent='    ', newl='\n', encoding='UTF-8').decode('utf-8')
                    lines = [line for line in xml_str.split('\n') if line.strip()]
                    f.write('\n'.join(lines) + '\n')
                print(Fore.GREEN + f'✓ Temporary LSX written')
                print(Fore.GREEN + f'[DEBUG] Adding LSX to zip as: {lsx_rel_path}')
                zipf.write(temp_lsx, lsx_rel_path)
                print(Fore.GREEN + f'✓ LSX added to zip')
                os.remove(temp_lsx)
                print(Fore.GREEN + f'[DEBUG] Cleaned up temporary LSX')
            else:
                print(Fore.GREEN + f'[DEBUG] DOM not modified, copying original LSX')
                original_lsx = os.path.splitext(self.atlas_path)[0] + '.lsx'
                print(Fore.GREEN + f'[DEBUG] Original LSX path: {original_lsx}')
                zipf.write(original_lsx, lsx_rel_path)
                print(Fore.GREEN + f'✓ Original LSX added to zip')
        if os.path.exists(temp_png):
            os.remove(temp_png)
            print(Fore.GREEN + f'[DEBUG] Cleaned up temporary PNG')
        print(Fore.GREEN + f"\n{'=' * 60}")
        if do_both:
            print(Fore.GREEN + f'ATLAS SAVED SUCCESSFULLY (BOTH DIRECT WRITE + ZIP)')
            print(Fore.GREEN + f'Zip output: {zip_path}')
            success_msg = f'Saved to both direct location and zip:\n{zip_path}'
            print(Fore.GREEN + f'[POPUP] Showing success: {success_msg}')
            QMessageBox.information(self, 'Success', success_msg)
        else:
            print(Fore.GREEN + f'ATLAS SAVED SUCCESSFULLY (ZIP)')
            print(Fore.GREEN + f'Output: {zip_path}')
            success_msg = f'Saved to {zip_path}'
            print(Fore.GREEN + f'[POPUP] Showing success: {success_msg}')
            QMessageBox.information(self, 'Success', success_msg)
        print(Fore.GREEN + f"{'=' * 60}\n")

    def resize_item_png_gui(self):
        print(Fore.CYAN + f"\n{'=' * 60}")
        print(Fore.CYAN + f'USER ACTION: Resize Item PNG')
        print(Fore.CYAN + f"{'=' * 60}")
        print(Fore.CYAN + f'[USER] Opening file dialog for PNG selection...')
        default_path = self.get_default_file_dialog_path()
        print(Fore.GREEN + f'[DEBUG] Default file dialog path: {default_path}')
        png_path = QFileDialog.getOpenFileName(self, self.strings['select_item_png'], default_path, 'PNG (*.png)')[0]
        if not png_path:
            print(Fore.YELLOW + f'[WARNING] User cancelled PNG selection')
            return
        print(Fore.GREEN + f'✓ User selected PNG: {png_path}')
        if self.mode == 'mod_project':
            mod = self.mod_combo.currentText()
            base_dest = os.path.join(self.bg3_edit.text(), 'Mods', mod, 'GUI')
            print(Fore.GREEN + f'[DEBUG] Mod project mode - using mod: {mod}')
        else:
            base_dest = self.output_edit.text() or os.path.dirname(png_path)
            print(Fore.GREEN + f'[DEBUG] Standalone mode')
        print(Fore.GREEN + f'[DEBUG] Destination directory: {base_dest}')
        print(Fore.CYAN + f'[OPERATION] Starting item resize operation...')
        resize_png(png_path, skill_mode=False, dest_dir=base_dest)
        print(Fore.GREEN + f"\n{'=' * 60}")
        print(Fore.GREEN + f'ITEM RESIZE COMPLETE')
        print(Fore.GREEN + f"{'=' * 60}\n")
        success_msg = self.strings['success_resize'].format(type='item')
        print(Fore.GREEN + f'[POPUP] Showing success: {success_msg}')
        QMessageBox.information(self, 'Success', success_msg)

    def resize_skill_png_gui(self):
        print(Fore.CYAN + f"\n{'=' * 60}")
        print(Fore.CYAN + f'USER ACTION: Resize Skill PNG')
        print(Fore.CYAN + f"{'=' * 60}")
        print(Fore.CYAN + f'[USER] Opening file dialog for PNG selection...')
        default_path = self.get_default_file_dialog_path()
        print(Fore.GREEN + f'[DEBUG] Default file dialog path: {default_path}')
        png_path = QFileDialog.getOpenFileName(self, self.strings['select_skill_png'], default_path, 'PNG (*.png)')[0]
        if not png_path:
            print(Fore.YELLOW + f'[WARNING] User cancelled PNG selection')
            return
        print(Fore.GREEN + f'✓ User selected PNG: {png_path}')
        if self.mode == 'mod_project':
            mod = self.mod_combo.currentText()
            base_dest = os.path.join(self.bg3_edit.text(), 'Mods', mod, 'GUI')
            print(Fore.GREEN + f'[DEBUG] Mod project mode - using mod: {mod}')
        else:
            base_dest = self.output_edit.text() or os.path.dirname(png_path)
            print(Fore.GREEN + f'[DEBUG] Standalone mode')
        print(Fore.GREEN + f'[DEBUG] Destination directory: {base_dest}')
        print(Fore.CYAN + f'[OPERATION] Starting skill resize operation...')
        resize_png(png_path, skill_mode=True, dest_dir=base_dest)
        print(Fore.GREEN + f"\n{'=' * 60}")
        print(Fore.GREEN + f'SKILL RESIZE COMPLETE')
        print(Fore.GREEN + f"{'=' * 60}\n")
        success_msg = self.strings['success_resize'].format(type='skill')
        print(Fore.GREEN + f'[POPUP] Showing success: {success_msg}')
        QMessageBox.information(self, 'Success', success_msg)

    def on_create_mod_changed(self):
        create_mod = self.create_mod_combo.currentText()
        if create_mod and create_mod != self.mod_combo.currentText():
            self.mod_combo.blockSignals(True)
            self.mod_combo.setCurrentText(create_mod)
            self.mod_combo.blockSignals(False)
        print(Fore.GREEN + f'[DEBUG] Create Atlas mod changed: {create_mod}')
        self.update_create_atlas_status()

    def update_create_atlas_grid_info(self):
        if self.canvas_512.isChecked():
            atlas_size = 512
        else:
            atlas_size = 1024
        tile_size = 64
        grid_size = atlas_size // tile_size
        total_slots = grid_size * grid_size
        self.grid_info_label.setText(f'Grid: {tile_size}x{tile_size} icons | Total slots: {total_slots} ({grid_size}x{grid_size})')
        self.update_create_atlas_status()

    def toggle_import_options(self):
        is_import = self.import_folder_radio.isChecked()
        self.import_controls_widget.setEnabled(is_import)
        if not is_import:
            self.import_folder_edit.clear()
            self.import_count_label.setText('No folder selected')
        self.update_create_atlas_status()

    def toggle_resize_type_selection(self):
        is_enabled = self.auto_resize_checkbox.isChecked()
        self.resize_type_widget.setVisible(is_enabled)

    def browse_import_folder(self):
        print(Fore.CYAN + f'\n[USER] Browsing for import folder...')
        default_path = self.get_default_file_dialog_path()
        print(Fore.GREEN + f"[DEBUG] Default browse path: {(default_path if default_path else '(current directory)')}")
        folder = QFileDialog.getExistingDirectory(self, 'Select Folder with PNG Icons', default_path)
        if folder:
            self.import_folder_edit.setText(folder)
            print(Fore.GREEN + f'✓ Selected folder: {folder}')

    def scan_import_folder(self):
        folder = self.import_folder_edit.text().strip()
        if not folder or not os.path.isdir(folder):
            self.import_count_label.setText('No folder selected')
            self.import_count_label.setStyleSheet('QLabel { color: #888; font-style: italic; }')
            self.update_create_atlas_status()
            return
        png_files = [f for f in os.listdir(folder) if f.lower().endswith('.png')]
        count = len(png_files)
        atlas_size = 512 if self.canvas_512.isChecked() else 1024
        grid_size = atlas_size // 64
        max_slots = grid_size * grid_size
        if count == 0:
            self.import_count_label.setText('No PNG files found in folder')
            self.import_count_label.setStyleSheet('QLabel { color: #ff6666; font-style: italic; }')
        elif count > max_slots:
            self.import_count_label.setText(f'Found {count} PNGs (WARNING: {count - max_slots} will be skipped, atlas has {max_slots} slots)')
            self.import_count_label.setStyleSheet('QLabel { color: #ffaa00; font-style: italic; }')
        else:
            self.import_count_label.setText(f'Found {count} PNG file(s) - will use {count} of {max_slots} slots')
            self.import_count_label.setStyleSheet('QLabel { color: #66ff66; font-style: italic; }')
        print(Fore.GREEN + f'[DEBUG] Found {count} PNG files in {folder}')
        self.update_create_atlas_status()

    def update_prefix_example(self):
        prefix = self.mapkey_prefix_edit.text().strip()
        if prefix:
            self.prefix_example_label.setText(f'Example: sword.png → MapKey: {prefix}_sword')
        else:
            self.prefix_example_label.setText('Example: sword.png → MapKey: sword')

    def update_create_atlas_status(self):
        mod = self.create_mod_combo.currentText()
        if not mod:
            self.create_atlas_path_label.setText('Please select a mod from the dropdown above')
            self.create_atlas_path_label.setStyleSheet('QLabel { color: #ff6666; font-style: italic; margin-left: 20px; background-color: #2a2a2a; padding: 5px; }')
            self.btn_generate_atlas.setEnabled(False)
            self.create_status_label.setText('Select a mod to continue')
            return
        bg3_data = self.bg3_edit.text().strip()
        atlas_name = self.atlas_name_edit.text().strip() or 'IconAtlas'
        public_base = os.path.join(bg3_data, 'Public', mod)
        mods_base = os.path.join(bg3_data, 'Mods', mod)
        if os.path.exists(public_base):
            base_path = public_base
        elif os.path.exists(mods_base):
            base_path = mods_base
        else:
            base_path = public_base
        gui_path = os.path.join(base_path, 'GUI')
        textures_path = os.path.join(base_path, 'Assets', 'Textures', 'Icons')
        lsx_path = os.path.join(gui_path, f'{atlas_name}.lsx')
        dds_path = os.path.join(textures_path, f'{atlas_name}.dds')
        exists = os.path.exists(lsx_path) or os.path.exists(dds_path)
        if exists:
            self.create_atlas_path_label.setText(f'LSX: {gui_path}\nDDS: {textures_path}\n(WARNING: Files exist - will be overwritten)')
            self.create_atlas_path_label.setStyleSheet('QLabel { color: #ffaa00; font-style: italic; margin-left: 20px; background-color: #2a2a2a; padding: 5px; }')
        else:
            self.create_atlas_path_label.setText(f'LSX: {gui_path}\nDDS: {textures_path}')
            self.create_atlas_path_label.setStyleSheet('QLabel { color: #66ff66; font-style: italic; margin-left: 20px; background-color: #2a2a2a; padding: 5px; }')
        self.btn_generate_atlas.setEnabled(True)
        self.create_status_label.setText('Ready to generate')

    def generate_new_atlas(self):
        print(Fore.CYAN + f"\n{'=' * 60}")
        print(Fore.CYAN + f'USER ACTION: Generate New Atlas')
        print(Fore.CYAN + f"{'=' * 60}")
        mod = self.create_mod_combo.currentText()
        if not mod:
            print(Fore.RED + f'[ERROR] No mod selected')
            QMessageBox.warning(self, 'Error', 'Please select a mod from the dropdown.')
            return
        bg3_data = self.bg3_edit.text().strip()
        atlas_size = 512 if self.canvas_512.isChecked() else 1024
        tile_size = 64
        grid_size = atlas_size // tile_size
        atlas_name = self.atlas_name_edit.text().strip() or 'IconAtlas'
        print(Fore.GREEN + f'[DEBUG] Atlas size: {atlas_size}x{atlas_size}')
        print(Fore.GREEN + f'[DEBUG] Tile size: {tile_size}x{tile_size}')
        print(Fore.GREEN + f'[DEBUG] Grid size: {grid_size}x{grid_size}')
        print(Fore.GREEN + f'[DEBUG] Atlas name: {atlas_name}')
        public_base = os.path.join(bg3_data, 'Public', mod)
        mods_base = os.path.join(bg3_data, 'Mods', mod)
        if os.path.exists(public_base):
            base_path = public_base
        elif os.path.exists(mods_base):
            base_path = mods_base
        else:
            base_path = public_base
        gui_path = os.path.join(base_path, 'GUI')
        textures_path = os.path.join(base_path, 'Assets', 'Textures', 'Icons')
        os.makedirs(gui_path, exist_ok=True)
        os.makedirs(textures_path, exist_ok=True)
        print(Fore.GREEN + f'[DEBUG] GUI path: {gui_path}')
        print(Fore.GREEN + f'[DEBUG] Textures path: {textures_path}')
        lsx_path = os.path.join(gui_path, f'{atlas_name}.lsx')
        dds_path = os.path.join(textures_path, f'{atlas_name}.dds')
        if os.path.exists(lsx_path) or os.path.exists(dds_path):
            print(Fore.YELLOW + f'[WARNING] Atlas files already exist')
            reply = QMessageBox.question(self, 'Overwrite Existing Atlas?', f'Atlas files already exist at:\n{gui_path}\n\nOverwrite?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                print(Fore.YELLOW + f'[WARNING] User cancelled overwrite')
                return
        import_icons = self.import_folder_radio.isChecked()
        prefix = self.mapkey_prefix_edit.text().strip()
        auto_resize = self.auto_resize_checkbox.isChecked()
        skill_mode = self.resize_type_skill.isChecked()
        if import_icons:
            import_folder = self.import_folder_edit.text().strip()
            if not import_folder or not os.path.isdir(import_folder):
                print(Fore.RED + f'[ERROR] Invalid import folder')
                QMessageBox.warning(self, 'Error', 'Please select a valid import folder.')
                return
            print(Fore.GREEN + f'[DEBUG] Import folder: {import_folder}')
            print(Fore.GREEN + f"[DEBUG] MapKey prefix: {(prefix if prefix else '(none)')}")
            print(Fore.GREEN + f'[DEBUG] Auto-resize: {auto_resize}')
            if auto_resize:
                print(Fore.GREEN + f"[DEBUG] Icon type: {('Skills' if skill_mode else 'Items')}")
        else:
            import_folder = None
            print(Fore.GREEN + f'[DEBUG] Creating empty atlas')
        try:
            self.create_status_label.setText('Generating atlas...')
            self.create_status_label.setStyleSheet('QLabel { color: #ffaa00; font-style: italic; }')
            QApplication.processEvents()
            if import_folder:
                self.generate_atlas_with_icons(import_folder, dds_path, atlas_size, tile_size, grid_size, prefix, auto_resize, skill_mode, base_path)
            else:
                self.generate_empty_atlas(dds_path, atlas_size, tile_size, base_path)
            print(Fore.GREEN + f'✓ Atlas created successfully')
            print(Fore.GREEN + f'  LSX: {lsx_path}')
            print(Fore.GREEN + f'  DDS: {dds_path}')
            self.create_status_label.setText('Atlas created successfully!')
            self.create_status_label.setStyleSheet('QLabel { color: #66ff66; font-style: italic; }')
            reply = QMessageBox.question(self, 'Atlas Created', f'New atlas created successfully!\n\nFiles created:\n  {atlas_name}.lsx\n  {atlas_name}.dds\n\nLoad this atlas in the Main tab?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.tabs.setCurrentIndex(0)
                self.project_lsx_edit.setText(lsx_path)
                self.load_atlas()
                print(Fore.GREEN + f'✓ Auto-loaded new atlas in Main tab')
        except Exception as e:
            print(Fore.RED + f'[ERROR] Failed to create atlas: {e}')
            self.create_status_label.setText('Failed to create atlas')
            self.create_status_label.setStyleSheet('QLabel { color: #ff6666; font-style: italic; }')
            QMessageBox.critical(self, 'Error', f'Failed to create atlas:\n{str(e)}')

    def generate_empty_atlas(self, dds_path, atlas_size, tile_size, base_path=''):
        print(Fore.CYAN + f'[OPERATION] Generating empty atlas...')
        dom = Document()
        save = dom.createElement('save')
        dom.appendChild(save)
        version = dom.createElement('version')
        version.setAttribute('major', '4')
        version.setAttribute('minor', '0')
        version.setAttribute('revision', '9')
        version.setAttribute('build', '320')
        save.appendChild(version)
        region_tex = dom.createElement('region')
        region_tex.setAttribute('id', 'TextureAtlasInfo')
        save.appendChild(region_tex)
        node_root_tex = dom.createElement('node')
        node_root_tex.setAttribute('id', 'root')
        region_tex.appendChild(node_root_tex)
        children_tex = dom.createElement('children')
        node_root_tex.appendChild(children_tex)
        node_tex_size = dom.createElement('node')
        node_tex_size.setAttribute('id', 'TextureAtlasTextureSize')
        attr_height = dom.createElement('attribute')
        attr_height.setAttribute('id', 'Height')
        attr_height.setAttribute('type', 'int32')
        attr_height.setAttribute('value', str(atlas_size))
        node_tex_size.appendChild(attr_height)
        attr_width = dom.createElement('attribute')
        attr_width.setAttribute('id', 'Width')
        attr_width.setAttribute('type', 'int32')
        attr_width.setAttribute('value', str(atlas_size))
        node_tex_size.appendChild(attr_width)
        children_tex.appendChild(node_tex_size)
        node_icon_size = dom.createElement('node')
        node_icon_size.setAttribute('id', 'TextureAtlasIconSize')
        attr_height = dom.createElement('attribute')
        attr_height.setAttribute('id', 'Height')
        attr_height.setAttribute('type', 'int32')
        attr_height.setAttribute('value', str(tile_size))
        node_icon_size.appendChild(attr_height)
        attr_width = dom.createElement('attribute')
        attr_width.setAttribute('id', 'Width')
        attr_width.setAttribute('type', 'int32')
        attr_width.setAttribute('value', str(tile_size))
        node_icon_size.appendChild(attr_width)
        children_tex.appendChild(node_icon_size)
        node_path = dom.createElement('node')
        node_path.setAttribute('id', 'TextureAtlasPath')
        attr_path = dom.createElement('attribute')
        attr_path.setAttribute('id', 'Path')
        attr_path.setAttribute('type', 'string')
        attr_path.setAttribute('value', f'Assets/Textures/Icons/{os.path.basename(dds_path)}')
        node_path.appendChild(attr_path)
        attr_uuid = dom.createElement('attribute')
        attr_uuid.setAttribute('id', 'UUID')
        attr_uuid.setAttribute('type', 'FixedString')
        attr_uuid.setAttribute('value', str(uuid.uuid4()))
        node_path.appendChild(attr_uuid)
        children_tex.appendChild(node_path)
        region_uv = dom.createElement('region')
        region_uv.setAttribute('id', 'IconUVList')
        save.appendChild(region_uv)
        node_root_uv = dom.createElement('node')
        node_root_uv.setAttribute('id', 'root')
        region_uv.appendChild(node_root_uv)
        children_uv = dom.createElement('children')
        node_root_uv.appendChild(children_uv)
        im = Image.new('RGBA', (atlas_size, atlas_size), (0, 0, 0, 0))
        temp_png = os.path.join(TEMP_DIR, 'temp_empty_atlas.png')
        dithered = apply_alpha_dither(im, strength=0.5)
        dithered.save(temp_png, 'PNG')
        png_to_dds(temp_png, dds_path, format='BC3_UNORM', mipmaps=1)
        base_name = os.path.splitext(os.path.basename(dds_path))[0]
        if base_path:
            lsx_dir = os.path.join(base_path, 'GUI')
        else:
            lsx_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(dds_path))), 'GUI')
        os.makedirs(lsx_dir, exist_ok=True)
        lsx_path = os.path.join(lsx_dir, f'{base_name}.lsx')
        with open(lsx_path, 'w', encoding='utf-8') as f:
            dom.writexml(f, indent='    ', addindent='    ', newl='\n', encoding='UTF-8')
        if os.path.exists(temp_png):
            os.remove(temp_png)
        print(Fore.GREEN + f'✓ Empty atlas created')

    def generate_atlas_with_icons(self, import_folder, dds_path, atlas_size, tile_size, grid_size, prefix='', auto_resize=False, skill_mode=False, base_path=''):
        print(Fore.CYAN + f'[OPERATION] Generating atlas with icons from: {import_folder}')
        if auto_resize:
            print(Fore.GREEN + f"[DEBUG] Auto-resize enabled ({('Skills' if skill_mode else 'Items')})")
        dom = Document()
        save = dom.createElement('save')
        dom.appendChild(save)
        version = dom.createElement('version')
        version.setAttribute('major', '4')
        version.setAttribute('minor', '0')
        version.setAttribute('revision', '9')
        version.setAttribute('build', '320')
        save.appendChild(version)
        region_tex = dom.createElement('region')
        region_tex.setAttribute('id', 'TextureAtlasInfo')
        save.appendChild(region_tex)
        node_root_tex = dom.createElement('node')
        node_root_tex.setAttribute('id', 'root')
        region_tex.appendChild(node_root_tex)
        children_tex = dom.createElement('children')
        node_root_tex.appendChild(children_tex)
        node_tex_size = dom.createElement('node')
        node_tex_size.setAttribute('id', 'TextureAtlasTextureSize')
        attr_height = dom.createElement('attribute')
        attr_height.setAttribute('id', 'Height')
        attr_height.setAttribute('type', 'int32')
        attr_height.setAttribute('value', str(atlas_size))
        node_tex_size.appendChild(attr_height)
        attr_width = dom.createElement('attribute')
        attr_width.setAttribute('id', 'Width')
        attr_width.setAttribute('type', 'int32')
        attr_width.setAttribute('value', str(atlas_size))
        node_tex_size.appendChild(attr_width)
        children_tex.appendChild(node_tex_size)
        node_icon_size = dom.createElement('node')
        node_icon_size.setAttribute('id', 'TextureAtlasIconSize')
        attr_height = dom.createElement('attribute')
        attr_height.setAttribute('id', 'Height')
        attr_height.setAttribute('type', 'int32')
        attr_height.setAttribute('value', str(tile_size))
        node_icon_size.appendChild(attr_height)
        attr_width = dom.createElement('attribute')
        attr_width.setAttribute('id', 'Width')
        attr_width.setAttribute('type', 'int32')
        attr_width.setAttribute('value', str(tile_size))
        node_icon_size.appendChild(attr_width)
        children_tex.appendChild(node_icon_size)
        node_path = dom.createElement('node')
        node_path.setAttribute('id', 'TextureAtlasPath')
        attr_path = dom.createElement('attribute')
        attr_path.setAttribute('id', 'Path')
        attr_path.setAttribute('type', 'string')
        attr_path.setAttribute('value', f'Assets/Textures/Icons/{os.path.basename(dds_path)}')
        node_path.appendChild(attr_path)
        attr_uuid = dom.createElement('attribute')
        attr_uuid.setAttribute('id', 'UUID')
        attr_uuid.setAttribute('type', 'FixedString')
        attr_uuid.setAttribute('value', str(uuid.uuid4()))
        node_path.appendChild(attr_uuid)
        children_tex.appendChild(node_path)
        region_uv = dom.createElement('region')
        region_uv.setAttribute('id', 'IconUVList')
        save.appendChild(region_uv)
        node_root_uv = dom.createElement('node')
        node_root_uv.setAttribute('id', 'root')
        region_uv.appendChild(node_root_uv)
        children_uv = dom.createElement('children')
        node_root_uv.appendChild(children_uv)
        im = Image.new('RGBA', (atlas_size, atlas_size), (0, 0, 0, 0))
        png_files = sorted([f for f in os.listdir(import_folder) if f.lower().endswith('.png')])
        max_icons = grid_size * grid_size
        print(Fore.GREEN + f'[DEBUG] Found {len(png_files)} PNG files')
        print(Fore.GREEN + f'[DEBUG] Atlas capacity: {max_icons} icons')
        for idx, png_file in enumerate(png_files):
            if idx >= max_icons:
                print(Fore.YELLOW + f'[WARNING] Atlas full, skipping remaining {len(png_files) - idx} files')
                break
            base_mapkey = os.path.splitext(png_file)[0]
            if prefix:
                mapkey = f'{prefix}_{base_mapkey}'
            else:
                mapkey = base_mapkey
            row = idx // grid_size
            col = idx % grid_size
            x = col * tile_size
            y = row * tile_size
            png_path = os.path.join(import_folder, png_file)
            new_im = resize_with_alpha(Image.open(png_path), (tile_size, tile_size), Image.BICUBIC)
            im.paste(new_im, (x, y), new_im if new_im.mode == 'RGBA' else None)
            u1 = col / grid_size
            v1 = row / grid_size
            u2 = u1 + 1 / grid_size
            v2 = v1 + 1 / grid_size
            node_uv = dom.createElement('node')
            node_uv.setAttribute('id', 'IconUV')
            attr_mapkey = dom.createElement('attribute')
            attr_mapkey.setAttribute('id', 'MapKey')
            attr_mapkey.setAttribute('type', 'FixedString')
            attr_mapkey.setAttribute('value', mapkey)
            node_uv.appendChild(attr_mapkey)
            attr_u1 = dom.createElement('attribute')
            attr_u1.setAttribute('id', 'U1')
            attr_u1.setAttribute('type', 'float')
            attr_u1.setAttribute('value', str(u1))
            node_uv.appendChild(attr_u1)
            attr_v1 = dom.createElement('attribute')
            attr_v1.setAttribute('id', 'V1')
            attr_v1.setAttribute('type', 'float')
            attr_v1.setAttribute('value', str(v1))
            node_uv.appendChild(attr_v1)
            attr_u2 = dom.createElement('attribute')
            attr_u2.setAttribute('id', 'U2')
            attr_u2.setAttribute('type', 'float')
            attr_u2.setAttribute('value', str(u2))
            node_uv.appendChild(attr_u2)
            attr_v2 = dom.createElement('attribute')
            attr_v2.setAttribute('id', 'V2')
            attr_v2.setAttribute('type', 'float')
            attr_v2.setAttribute('value', str(v2))
            node_uv.appendChild(attr_v2)
            children_uv.appendChild(node_uv)
            print(Fore.GREEN + f'  ✓ Added icon {idx + 1}/{min(len(png_files), max_icons)}: {mapkey}')
        temp_png = os.path.join(TEMP_DIR, 'temp_new_atlas.png')
        dithered = apply_alpha_dither(im, strength=0.5)
        dithered.save(temp_png, 'PNG')
        png_to_dds(temp_png, dds_path, format='BC3_UNORM', mipmaps=1)
        base_name = os.path.splitext(os.path.basename(dds_path))[0]
        lsx_dir = os.path.join(base_path, 'GUI')
        lsx_path = os.path.join(lsx_dir, f'{base_name}.lsx')
        with open(lsx_path, 'w', encoding='utf-8') as f:
            dom.writexml(f, indent='    ', addindent='    ', newl='\n', encoding='UTF-8')
        if os.path.exists(temp_png):
            os.remove(temp_png)
        print(Fore.GREEN + f'✓ Atlas created with {min(len(png_files), max_icons)} icons')
        if auto_resize and png_files:
            print(Fore.CYAN + f'[OPERATION] Auto-resizing {min(len(png_files), max_icons)} icons...')
            for idx, png_file in enumerate(png_files):
                if idx >= max_icons:
                    break
                base_mapkey = os.path.splitext(png_file)[0]
                if prefix:
                    mapkey = f'{prefix}_{base_mapkey}'
                else:
                    mapkey = base_mapkey
                png_path = os.path.join(import_folder, png_file)
                try:
                    resize_png(png_path, skill_mode=skill_mode, dest_dir=base_path, output_name=mapkey)
                    print(Fore.GREEN + f'  ✓ Resized {idx + 1}/{min(len(png_files), max_icons)}: {mapkey}')
                except Exception as e:
                    print(Fore.YELLOW + f'  ⚠ Failed to resize {png_file}: {e}')
            print(Fore.GREEN + f'✓ Completed resizing {min(len(png_files), max_icons)} icons')

    def find_icon_all_sizes(self, mapkey):
        icon_paths = {}
        icon_type = None
        bg3_data = self.bg3_edit.text().strip()
        mod = self.mod_combo.currentText()
        size_configs = {72: {'item': 'AssetsLowRes\\ControllerUIIcons\\items_png', 'skill': 'AssetsLowRes\\ControllerUIIcons\\skills_png'}, 144: {'item': 'Assets\\ControllerUIIcons\\items_png', 'skill': 'Assets\\ControllerUIIcons\\skills_png'}, 192: {'item': 'AssetsLowRes\\Tooltips\\ItemIcons', 'skill': 'AssetsLowRes\\Tooltips\\SkillIcons'}, 380: {'item': 'Assets\\Tooltips\\ItemIcons', 'skill': 'Assets\\Tooltips\\SkillIcons'}}
        for size, paths in size_configs.items():
            found = False
            if self.mode == 'mod_project' and mod and bg3_data:
                for type_name, rel_path in paths.items():
                    search_paths = [os.path.join(bg3_data, 'Mods', mod, 'GUI', rel_path, f'{mapkey}.dds'), os.path.join(bg3_data, 'Public', mod, rel_path, f'{mapkey}.dds')]
                    for path in search_paths:
                        if os.path.exists(path):
                            icon_paths[size] = path
                            if icon_type is None:
                                icon_type = type_name
                            found = True
                            break
                    if found:
                        break
            elif self.atlas_path:
                atlas_dir = os.path.dirname(self.atlas_path)
                for type_name, rel_path in paths.items():
                    path = os.path.join(atlas_dir, rel_path, f'{mapkey}.dds')
                    if os.path.exists(path):
                        icon_paths[size] = path
                        if icon_type is None:
                            icon_type = type_name
                        found = True
                        break
        icon_paths['icon_type'] = icon_type if icon_type else 'item'
        return icon_paths

    def preview_full_size(self, mapkey):
        print(Fore.CYAN + f"\n{'=' * 60}")
        print(Fore.CYAN + f'CONTEXT MENU: Preview Full Size (Multi-Size Tabs)')
        print(Fore.CYAN + f"{'=' * 60}")
        print(Fore.GREEN + f'[DEBUG] MapKey: {mapkey}')
        icon_paths = self.find_icon_all_sizes(mapkey)
        icon_type = icon_paths.pop('icon_type', 'item')
        if not icon_paths:
            print(Fore.YELLOW + f"[WARNING] No icon sizes found for '{mapkey}'")
            QMessageBox.warning(self, 'Preview Not Available', f"Could not find any icon sizes for '{mapkey}'.")
            return
        print(Fore.GREEN + f'[DEBUG] Found {len(icon_paths)} icon sizes: {sorted(icon_paths.keys())}')
        dialog = QDialog(self)
        dialog.setWindowTitle(f'Preview: {mapkey}')
        dialog.setModal(True)
        dialog_layout = QVBoxLayout()
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet('\n            QTabWidget::pane {\n                border: 2px solid #555;\n                background-color: #2a2a2a;\n            }\n            QTabBar::tab {\n                background-color: #3a3a3a;\n                color: white;\n                padding: 8px 16px;\n                margin-right: 2px;\n                border: 1px solid #555;\n                border-bottom: none;\n                border-top-left-radius: 4px;\n                border-top-right-radius: 4px;\n            }\n            QTabBar::tab:selected {\n                background-color: #2a2a2a;\n                border-bottom: 2px solid #ff8c00;\n            }\n            QTabBar::tab:hover {\n                background-color: #4a4a4a;\n            }\n        ')
        temp_files = []
        sizes_order = [72, 144, 192, 380]
        for size in sizes_order:
            if size not in icon_paths:
                continue
            dds_path = icon_paths[size]
            temp_png = os.path.join(TEMP_DIR, f'preview_{mapkey}_{size}.png')
            temp_files.append(temp_png)
            try:
                print(Fore.CYAN + f'[OPERATION] Converting {size}px DDS to PNG for preview...')
                dds_to_png(dds_path, temp_png)
                pixmap = QPixmap(temp_png)
                if pixmap.isNull():
                    print(Fore.RED + f'[ERROR] Failed to load {size}px preview image')
                    continue
                tab_content = QWidget()
                tab_layout = QVBoxLayout()
                image_label = QLabel()
                image_label.setPixmap(pixmap)
                image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                image_label.setStyleSheet('QLabel { border: 2px solid #555; background-color: #2a2a2a; padding: 10px; }')
                tab_layout.addWidget(image_label)
                size_info = QLabel(f'<b>Dimensions:</b> {pixmap.width()}×{pixmap.height()}px')
                size_info.setStyleSheet('QLabel { padding: 5px; font-size: 11pt; color: #ccc; }')
                size_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
                size_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                tab_layout.addWidget(size_info)
                tab_content.setLayout(tab_layout)
                tab_widget.addTab(tab_content, f'{size}×{size}px')
                print(Fore.GREEN + f'✓ Added {size}px tab to preview')
            except Exception as e:
                print(Fore.RED + f'[ERROR] Failed to create {size}px preview: {e}')
                continue
        dialog_layout.addWidget(tab_widget)
        available_sizes = ', '.join([f'{s}×{s}' for s in sorted(icon_paths.keys())])
        primary_path = icon_paths.get(380) or icon_paths.get(192) or icon_paths.get(144) or icon_paths.get(72)
        info_label = QLabel(f'<b>MapKey:</b> {mapkey}<br><b>Type:</b> {icon_type.capitalize()}<br><b>Path:</b> {primary_path}<br><b>Available Sizes:</b> {available_sizes}px')
        info_label.setStyleSheet('QLabel { padding: 10px; font-size: 12pt; }')
        info_label.setWordWrap(True)
        info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        dialog_layout.addWidget(info_label)
        close_btn = QPushButton('Close')
        close_btn.setStyleSheet('QPushButton { font-size: 12pt; padding: 5px; }')
        close_btn.clicked.connect(dialog.close)
        dialog_layout.addWidget(close_btn)
        dialog.setLayout(dialog_layout)
        dialog.adjustSize()
        dialog.setMinimumWidth(420)
        print(Fore.GREEN + f'[POPUP] Showing multi-size preview dialog with {tab_widget.count()} tabs')
        dialog.exec()
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        print(Fore.GREEN + f'[DEBUG] Cleaned up {len(temp_files)} temporary preview files')

    def replace_icon_from_context(self, mapkey):
        print(Fore.CYAN + f"\n{'=' * 60}")
        print(Fore.CYAN + f'CONTEXT MENU: Replace Icon')
        print(Fore.CYAN + f"{'=' * 60}")
        print(Fore.GREEN + f'[DEBUG] MapKey: {mapkey}')
        index = self.combo_icons.findText(mapkey)
        if index >= 0:
            self.combo_icons.setCurrentIndex(index)
            print(Fore.GREEN + f"✓ Selected '{mapkey}' in dropdown")
        self.replace_icon()

    def copy_mapkey(self, mapkey):
        print(Fore.CYAN + f"\n{'=' * 60}")
        print(Fore.CYAN + f'CONTEXT MENU: Copy MapKey')
        print(Fore.CYAN + f"{'=' * 60}")
        print(Fore.GREEN + f'[DEBUG] Copying to clipboard: {mapkey}')
        clipboard = QApplication.clipboard()
        clipboard.setText(mapkey)
        print(Fore.GREEN + f"✓ MapKey '{mapkey}' copied to clipboard")
        print(Fore.GREEN + f'[POPUP] Showing info toast')
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle('Copied')
        msg.setText(f'MapKey copied: {mapkey}')
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setDefaultButton(QMessageBox.StandardButton.Ok)
        QTimer.singleShot(1500, msg.close)
        msg.exec()

    def delete_icon_from_atlas(self, mapkey):
        print(Fore.CYAN + f"\n{'=' * 60}")
        print(Fore.CYAN + f'CONTEXT MENU: Delete from Atlas')
        print(Fore.CYAN + f"{'=' * 60}")
        print(Fore.GREEN + f'[DEBUG] MapKey: {mapkey}')
        print(Fore.YELLOW + f'[POPUP] Showing deletion confirmation')
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle('Confirm Deletion')
        msg_box.setText(f"Delete icon '{mapkey}' from atlas?")
        msg_box.setInformativeText('This will:\n• Remove icon from the atlas\n• Delete all resized versions (72, 144, 192, 380 px)\n• Clear the tile in the atlas image\n\nThis action cannot be undone!')
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        reply = msg_box.exec()
        if reply != QMessageBox.StandardButton.Yes:
            print(Fore.YELLOW + f'[WARNING] User cancelled deletion')
            return
        print(Fore.GREEN + f'✓ User confirmed deletion')
        icon_to_delete = None
        for icon in self.icons:
            if icon['mapkey'] == mapkey:
                icon_to_delete = icon
                break
        if not icon_to_delete:
            print(Fore.RED + f'[ERROR] Icon not found: {mapkey}')
            return
        print(Fore.CYAN + f'[OPERATION] Deleting icon from atlas...')
        col, row = get_grid_slot(icon_to_delete['u1'], icon_to_delete['v1'], self.grid_size)
        x = col * self.tile_size
        y = row * self.tile_size
        print(Fore.GREEN + f'[DEBUG] Clearing tile at pixel position: x={x}, y={y}')
        clear_im = Image.new('RGBA', (self.tile_size, self.tile_size), (0, 0, 0, 0))
        self.atlas_im.paste(clear_im, (x, y))
        print(Fore.CYAN + f'[OPERATION] Removing from LSX...')
        for region in self.dom.getElementsByTagName('region'):
            if region.getAttribute('id') == 'IconUVList':
                root = region.getElementsByTagName('node')[0]
                children = root.getElementsByTagName('children')[0]
                for node in children.getElementsByTagName('node'):
                    if node.getAttribute('id') == 'IconUV':
                        for attr in node.getElementsByTagName('attribute'):
                            if attr.getAttribute('id') == 'MapKey' and attr.getAttribute('value') == mapkey:
                                children.removeChild(node)
                                print(Fore.GREEN + f'✓ Removed from LSX')
                                break
        self.icons = [icon for icon in self.icons if icon['mapkey'] != mapkey]
        print(Fore.GREEN + f'[DEBUG] Removed from internal list. Total icons now: {len(self.icons)}')
        index = self.combo_icons.findText(mapkey)
        if index >= 0:
            self.combo_icons.removeItem(index)
            print(Fore.GREEN + f'✓ Removed from dropdown')
        if self.mode == 'mod_project':
            bg3_data = self.bg3_edit.text().strip()
            mod = self.mod_combo.currentText()
            if mod and bg3_data:
                print(Fore.CYAN + f'[OPERATION] Deleting resized DDS files...')
                delete_paths = [os.path.join(bg3_data, 'Mods', mod, 'GUI', 'AssetsLowRes', 'ControllerUIIcons', 'items_png', f'{mapkey}.dds'), os.path.join(bg3_data, 'Mods', mod, 'GUI', 'Assets', 'ControllerUIIcons', 'items_png', f'{mapkey}.dds'), os.path.join(bg3_data, 'Mods', mod, 'GUI', 'AssetsLowRes', 'Tooltips', 'ItemIcons', f'{mapkey}.dds'), os.path.join(bg3_data, 'Mods', mod, 'GUI', 'Assets', 'Tooltips', 'ItemIcons', f'{mapkey}.dds'), os.path.join(bg3_data, 'Mods', mod, 'GUI', 'AssetsLowRes', 'ControllerUIIcons', 'skills_png', f'{mapkey}.dds'), os.path.join(bg3_data, 'Mods', mod, 'GUI', 'Assets', 'ControllerUIIcons', 'skills_png', f'{mapkey}.dds'), os.path.join(bg3_data, 'Mods', mod, 'GUI', 'AssetsLowRes', 'Tooltips', 'SkillIcons', f'{mapkey}.dds'), os.path.join(bg3_data, 'Mods', mod, 'GUI', 'Assets', 'Tooltips', 'SkillIcons', f'{mapkey}.dds')]
                deleted_count = 0
                for path in delete_paths:
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                            print(Fore.GREEN + f'✓ Deleted: {path}')
                            deleted_count += 1
                        except Exception as e:
                            print(Fore.RED + f'[ERROR] Failed to delete {path}: {e}')
                print(Fore.GREEN + f'✓ Deleted {deleted_count} resized DDS file(s)')
        self.dom_modified = True
        self.update_preview()
        print(Fore.GREEN + f"\n{'=' * 60}")
        print(Fore.GREEN + f'ICON DELETED SUCCESSFULLY')
        print(Fore.GREEN + f"{'=' * 60}\n")
        success_msg = f"Icon '{mapkey}' has been deleted from the atlas and all resized versions removed."
        print(Fore.GREEN + f'[POPUP] Showing success: {success_msg}')
        QMessageBox.information(self, 'Deleted', success_msg)

    def load_preferences(self):
        prefs_file = os.path.join(os.path.dirname(__file__), 'preferences.json')
        if os.path.exists(prefs_file):
            with open(prefs_file, 'r', encoding='utf-8') as f:
                prefs = json.load(f)
                prefs.setdefault('log_enabled', True)
                prefs.setdefault('log_directory', os.path.join(os.path.dirname(__file__), 'logs'))
                prefs.setdefault('log_level', 'DEBUG')
                prefs.setdefault('max_log_files', 10)
                prefs.setdefault('texconv_path', '')
                return prefs
        return {'log_enabled': True, 'log_directory': os.path.join(os.path.dirname(__file__), 'logs'), 'log_level': 'DEBUG', 'max_log_files': 10, 'texconv_path': ''}

    def save_preferences(self):
        global TEXCONV_PATH
        prefs = {'bg3_data': self.bg3_prefs_edit.text(), 'temp_dir': self.temp_edit.text(), 'output_path': self.output_edit.text(), 'zip_output_path': self.zip_edit.text(), 'preview_size': self.preview_combo.currentText(), 'log_enabled': self.log_enabled_checkbox.isChecked(), 'log_directory': self.log_dir_edit.text(), 'log_level': self.log_level_combo.currentText(), 'max_log_files': self.max_log_files_spinbox.value(), 'texconv_path': self.texconv_path_edit.text()}
        prefs_file = os.path.join(os.path.dirname(__file__), 'preferences.json')
        with open(prefs_file, 'w', encoding='utf-8') as f:
            json.dump(prefs, f, indent=2)
        TEXCONV_PATH = find_texconv(prefs['texconv_path'])
        self.update_texconv_status()
        QMessageBox.information(self, 'Success', 'Preferences saved.\n\nNote: Logging changes will take effect on next application start.')

    def show_console_viewer(self):
        global CONSOLE_CAPTURE
        if CONSOLE_CAPTURE is None:
            QMessageBox.warning(self, 'Console Unavailable', "Console capture is not initialized.\n\nThis is likely because the application started in a mode that doesn't support console capture.\n\nTry running the application from the command line to see output.")
            return
        try:
            dialog = ConsoleViewerDialog(CONSOLE_CAPTURE, self)
            dialog.show()
        except Exception as e:
            QMessageBox.critical(self, 'Console Viewer Error', f'Failed to open console viewer:\n\n{str(e)}')
if __name__ == '__main__':
    main()