import json
import os
import shutil
import sys

from pathlib import Path

# =============================================================================
class CondaWheelConverter():
  def __init__(self):

    # python package locations
    self.src_path = (Path('.') / 'src').resolve()
    self.bin_path = (Path('.') / 'bin').resolve()
    self.lib_path = (Path('.') / 'lib').resolve()
    self.core_path = (self.src_path / 'libtbx' / 'core').resolve()

    # copied files
    self.src_files = []
    self.bin_files = []
    self.lib_files = []

  # ---------------------------------------------------------------------------
  def copy_files(self, package_path):
    # load file metadata from conda package
    package_path = Path(package_path)
    with (package_path / 'info' / 'files').open() as f:
      file_list = f.readlines()
    with (package_path / 'info' / 'paths.json').open() as f:
      paths_list = json.load(f)

    paths_file_list = []
    for f in paths_list['paths']:
      paths_file_list.append(f['_path'])

    file_list = sorted(file_list)
    paths_file_list = sorted(paths_file_list)

    # check internal consistency
    assert len(file_list) == len(paths_file_list)
    for i in range(len(file_list)):
      assert file_list[i].strip() == paths_file_list[i].strip(), \
        (file_list[i].strip(), paths_file_list[i].strip())

    # create directories
    # os.makedirs(self.src_path, exist_ok=True)
    # os.makedirs(self.bin_path, exist_ok=True)
    # os.makedirs(self.core_path, exist_ok=True)

    # counters
    n_ignored = 0
    n_copied = 0

    # copy files
    for file_json in paths_list['paths']:
      copied = self._copy_file(file_json, package_path)
      if copied:
        n_copied += 1
      else:
        n_ignored += 1
    n_processed = n_copied + n_ignored

    assert n_copied == len(self.bin_files) + len(self.lib_files) + len(self.src_files)

    # summary
    print()
    print(f'Copied   {n_copied} files')
    print(f'Ignored  {n_ignored} files')
    print(f'Total    {n_processed} files')
    print(f'Original {len(file_list)} files')

    return n_processed == len(file_list)

  # ---------------------------------------------------------------------------
  def _copy_file(self, file_json, package_path):
    # source file
    relative_path = Path(file_json['_path'])
    file_path = (package_path / relative_path).resolve()

    # destination
    dest = None

    # ignore __pycache__ files
    # ignore existing .egg-info and .dist-info directories
    if '__pycache__' in relative_path.parent.parts \
      or 'egg-info' in os.fspath(relative_path.parent) \
      or 'dist-info' in os.fspath(relative_path.parent):
      pass
    # copy all dispatchers in bin
    elif 'bin' in relative_path.parent.parts[0]:
      dest = self.bin_path / relative_path.name
      self.bin_files.append(dest)
    # copy site-packages files to src
    elif 'site-packages' in relative_path.parent.parts:
      dest = (self.src_path / Path(os.fspath(file_path).split('site-packages')[-1][1:])).resolve()
      self.src_files.append(dest)
    # copy share files to libtbx/core
    elif 'share' in relative_path.parent.parts[0]:
      dest = (self.core_path / relative_path)
      self.src_files.append(dest)
    elif relative_path.suffix == '.so':
      dest = (self.lib_path / relative_path.name).resolve()
      self.lib_files.append(dest)

    if dest is not None:
      os.makedirs(dest.parent, exist_ok=True)
      shutil.copyfile(file_path, dest)
      print(f'''\
    Copying {file_path}
            {dest}\
    ''')
      return True
    else:
      return False

# =============================================================================
def create_wheel(prefix_path):
  converter = CondaWheelConverter()
  result = converter.copy_files(prefix_path)

  return result

# =============================================================================
if __name__ == '__main__':
  # create_wheel('../cctbx-base-2025.4-py311h92c6074_0')
  sys.exit(create_wheel('../cctbx-base-2025.4-py313h661d2d4_0'))
