import logging
import os
import shutil
from pathlib import Path

FORMAT = '%(asctime)s %(levelname)s %(message)s'
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=FORMAT)
import __version__
import PyInstaller.__main__


dist_path = Path('dist')

# Remove or create dist directory
if dist_path.is_dir():
    shutil.rmtree(dist_path, ignore_errors=True)
    logger.info('Removed dist folder')
dist_path.mkdir(parents=True, exist_ok=True)
logger.info('Created empty dist folder')

# Copy source files
logger.info('Copy source dirs')
src = Path('star/global_config.json')
dst = dist_path / 'star/global_config.json'
# Ensure the destination subdirectory exists
dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(src, dst)
logger.info(f'Copied {src} to {dst}')

src = Path('star/config_file.json')
dst = dist_path / 'star/config_file.json'
# Ensure the destination subdirectory exists
dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(src, dst)
logger.info(f'Copied {src} to {dst}')


src = 'docs'
dst = 'dist/docs'
shutil.copytree(src, dst)


src = 'tests'
dst = 'dist/tests'
shutil.copytree(src, dst)

ver = __version__.version()

logger.info('run pyinstaller')
try:
    PyInstaller.__main__.run([
        'run.py',
        '--onefile',
        f'-n SmapocControl{ver}',
        '-i', 'docs/imgs/icon.ico',  # Fix the icon flag
        '--add-binary', 'drivers\\micro_epsilon\\MEDAQLib.dll;drivers\\micro_epsilon'])
finally:
    src2 = Path('dist')
    dst2 = Path(f'SMAPOC_CONTROL_V{ver}')
    if Path.is_dir(dst2):
        shutil.rmtree(dst2, ignore_errors=True)
    shutil.move(src2, dst2)




