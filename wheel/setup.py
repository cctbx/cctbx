import os
import shutil
import sys

from pathlib import Path
from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext

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
    super().run()

  def copy_extension(self, extension):
    shutil.copyfile(Path('.') / 'lib' / extension.filename,
                    Path(self.build_lib) / extension.filename)

# =============================================================================
if __name__ == '__main__':
  ext_modules = [CCTBXExtension(Path(f).name) for f in os.listdir(Path('.') / 'lib')]
  scripts = [str(os.path.join('.', 'bin', f)) for f in os.listdir(Path('.') / 'bin')]
  setup(ext_modules=ext_modules,
        cmdclass={'build_ext' : BuildCCTBX},
        scripts=scripts)
