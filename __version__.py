# version file

__version = '0.1.1'

__release_info = f'Version: {__version}' + '''

Build Date: 2025/06/11
Author: M.Baeuml

Release Notes: 
- For spring stiffness test POP 2.2

'''


def version():
    return __version

def info():
    return __release_info

