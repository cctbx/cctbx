import json
import os
import shutil
import sys

from pathlib import Path

# =============================================================================
def create_wheel(package_path):
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
  src_path = Path('.') / 'src'
  os.makedirs(src_path, exist_ok=True)
  bin_path = Path('.') / 'bin'
  os.makedirs(bin_path, exist_ok=True)
  core_path = src_path / 'libtbx' / 'core'
  os.makedirs(core_path, exist_ok=True)

  # counters
  n_ignored = 0
  n_copied = 0

  # copy files
  for file_json in paths_list['paths']:
    copied = copy_file(file_json, package_path, src_path)
    if copied:
      n_copied += 1
    else:
      n_ignored += 1
  n_processed = n_copied + n_ignored

  # summary
  print()
  print(f'Copied   {n_copied} files')
  print(f'Ignored  {n_ignored} files')
  print(f'Total    {n_processed} files')
  print(f'Original {len(file_list)} files')

  return n_processed == len(file_list)

# -----------------------------------------------------------------------------
def copy_file(file_json, src_path, dest_path):
  # source file
  relative_path = Path(file_json['_path'])
  file_path = (src_path / relative_path).resolve()

  # destination
  bin_path = (dest_path / '..' / 'bin').resolve()
  lib_path = (dest_path / '..' / 'lib').resolve()
  core_path = (dest_path / 'libtbx' / 'core').resolve()
  dest = None

  # ignore __pycache__ files
  # ignore existing .egg-info and .dist-info directories
  if '__pycache__' in relative_path.parent.parts \
    or 'egg-info' in os.fspath(relative_path.parent) \
    or 'dist-info' in os.fspath(relative_path.parent):
    pass
  # copy all dispatchers in bin
  elif 'bin' in relative_path.parent.parts[0]:
    dest = bin_path / relative_path.name
  # copy site-packages files to src
  elif 'site-packages' in relative_path.parent.parts:
    dest = (dest_path / Path(os.fspath(file_path).split('site-packages')[-1][1:])).resolve()
  # copy share files to libtbx/core
  elif 'share' in relative_path.parent.parts[0]:
    dest = (core_path / relative_path)
  elif relative_path.suffix == '.so':
    dest = (lib_path / relative_path.name)

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
if __name__ == '__main__':
  # create_wheel('../cctbx-base-2025.4-py311h92c6074_0')
  sys.exit(create_wheel('../cctbx-base-2025.4-py313h661d2d4_0'))
