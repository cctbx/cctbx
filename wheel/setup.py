import os
from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext

# =============================================================================
class CCTBXExtension(Extension):
  def __init__(self, name, **kwargs):
    super().__init__(name, sources=[])
    self.__dict__.update(kwargs)

# =============================================================================
class BuildCCTBX(build_ext):

  def run(self):
    for extension in self.extensions:
      self.copy_extension(extension)
    super().run()

  def copy_extension(self, extension):
    build_path = self.build_temp

# =============================================================================
if __name__ == '__main__':
  ext_modules = []
  setup(ext_modules=ext_modules,
        cmdclass={'build_ext' : BuildCCTBX},)
