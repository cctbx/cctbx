import os
import shutil
import sys

from pathlib import Path
from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext
from subprocess import check_output

# =============================================================================
class CCTBXExtension(Extension):
  def __init__(self, name, **kwargs):
    super().__init__(name, sources=['dummy.c'])
    self.__dict__.update(kwargs)
    self.filename = name
    self.name = 'dummy'

# =============================================================================
class BuildCCTBX(build_ext):

  def run(self):
    for extension in self.extensions:
      self.copy_extension(extension)
      if sys.platform == 'darwin':
        self.fixed_dylib = []
        self.fix_rpaths(extension.filename)
    super().run()

  def copy_extension(self, extension):
    shutil.copyfile(Path('.') / 'lib' / extension.filename,
                    Path(self.build_lib) / extension.filename)

  def fix_rpaths(self, filename):
    # replace @rpath with CONDA_PREFIX
    new_rpath = os.environ.get('CONDA_PREFIX', None)
    assert new_rpath is not None, 'The conda environment must be active.'
    new_rpath = Path(new_rpath) / 'lib'

    if filename.endswith('dylib'):
      file_path = new_rpath /filename
    else:
      file_path = Path(self.build_lib) / filename
    assert file_path.exists()

    # get library links
    otool_lines = check_output(['otool', '-L', file_path]).decode('utf8').split('\n')
    print('Fixing', filename)
    print('='*79)
    print('\n'.join(otool_lines))
    print('-'*79)

    for line in otool_lines:
      if line.strip().startswith('@rpath'):
        rpath_line = line.split()[0]
        library = rpath_line.split('/')[-1]
        if library == filename:
          continue
        new_lib = new_rpath / library
        assert new_lib.exists()
        output = check_output(['install_name_tool', '-change', rpath_line, new_lib, file_path])
        print('\n'.join(output))
        if library.endswith('dylib') and library not in self.fixed_dylib:
          self.fix_rpaths(library)
          self.fixed_dylib.append(library)
          print(self.fixed_dylib)

    # check updated library links
    print('-'*79)
    otool_lines = check_output(['otool', '-L', file_path]).decode('utf8').split('\n')
    print('\n'.join(otool_lines))
    print('='*79)
    print('\n')

    # sign file
    output = check_output(['codesign', '--continue', '-s', '-', '-f', file_path]).decode('utf8').split('\n')
    print('\n'.join(output))

# =============================================================================
if __name__ == '__main__':
  ext_modules = [CCTBXExtension(Path(f).name) for f in os.listdir(Path('.') / 'lib')]
  scripts = [str(os.path.join('.', 'bin', f)) for f in os.listdir(Path('.') / 'bin')]
  setup(ext_modules=ext_modules,
        cmdclass={'build_ext' : BuildCCTBX},
        scripts=scripts)
