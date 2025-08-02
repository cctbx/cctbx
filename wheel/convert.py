import argparse
import glob
import json
import os
import shutil
import sys

from pathlib import Path
from subprocess import check_output

# =============================================================================
class CondaWheelConverter():
  def __init__(self):

    # python package locations
    self.src_path = (Path('.') / 'src').resolve()
    self.bin_path = (Path('.') / 'bin').resolve()  # regular dispatchers
    self.lib_path = (Path('.') / 'lib').resolve()  # libraries
    self.core_path = (self.src_path / 'libtbx' / 'core').resolve()  # share
    self.entry_point_path = (self.src_path / 'libtbx' / 'core' / 'dispatchers').resolve()  # binaries or dispatchers on Windows

    # create directories
    os.makedirs(self.src_path, exist_ok=True)
    os.makedirs(self.bin_path, exist_ok=True)
    os.makedirs(self.lib_path, exist_ok=True)
    os.makedirs(self.core_path, exist_ok=True)
    os.makedirs(self.entry_point_path, exist_ok=True)

    # create __init__.py
    (Path(self.entry_point_path) / '__init__.py').touch()
    (Path(self.entry_point_path.parent) / '__init__.py').touch()

    # copied files
    self.src_files = []
    self.bin_files = []
    self.lib_files = []

    # binary files cannot be scripts, so they will be wrapped as entry points
    self.binary_files = [
      'cctbx.sys_abs_equiv_space_groups',
      'cctbx.convert_ccp4_symop_lib',
      'cctbx.getting_started',
      'cctbx.sym_equiv_sites',
      'cctbx.lattice_symmetry',
      'cctbx.find_distances',
      ]

    # binary files in share that are used for testing
    self.shared_binary_files = []

    # for self.fix_rpaths
    self.fixed_dylib = []

    # template for entry point for running dispatchers/executables
    self.entry_point_template =  '''\
import os
import subprocess
import sys

from pathlib import Path

def run_command():
  import libtbx.core.dispatchers
  executable = Path(libtbx.core.dispatchers.__file__).parent / '{dispatcher_name}'
  executable = str(executable.resolve())

  sys.exit(subprocess.call([executable, *sys.argv[1:]], shell=False))
'''

  # ---------------------------------------------------------------------------
  def copy_files(self, package_path):
    print('='*79)
    print('Copying files')
    print('='*79)

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

    # find binary files in shared
    shared_binary_files = []
    core_path = str(self.core_path.resolve())
    shared_binary_files.extend(glob.glob(os.path.join(core_path, '**/tst*'), recursive=True))
    shared_binary_files.extend(glob.glob(os.path.join(core_path, '**/*test*'), recursive=True))
    shared_binary_files.extend(glob.glob(os.path.join(core_path, '**/driver?'), recursive=True))
    shared_binary_files.extend(glob.glob(os.path.join(core_path, 'fftpack_timer'), recursive=True))
    shared_binary_files.extend(glob.glob(os.path.join(core_path, 'hybrid_36_fem'), recursive=True))
    shared_binary_files.extend(glob.glob(os.path.join(core_path, 'time_trigonometry'), recursive=True))

    for binary in shared_binary_files:
      if not os.path.isdir(binary):
        self.shared_binary_files.append(binary)

    # macOS specific fixes
    if sys.platform == 'darwin':
      # fix rpaths on macOS
      print('='*79)
      print('Fixing RPATH')
      print('='*79)
      for extension in self.lib_files:
        self.fixed_dylib = []
        self.fix_rpaths(extension.name)
      for binary in self.bin_files:
        if binary.name in self.binary_files:
          self.fix_rpaths(binary.name)
      for binary in self.shared_binary_files:
        self.fix_rpaths(binary)

      # fix macOS dispatchers to remove python.app
      print('='*79)
      print('Removing python.app')
      print('='*79)
      original = 'LIBTBX_PYEXE="$LIBTBX_PREFIX/python.app/Contents/MacOS/$LIBTBX_PYEXE_BASENAME"'
      patched = 'LIBTBX_PYEXE="$LIBTBX_PREFIX/bin/$LIBTBX_PYEXE_BASENAME"\n'
      for dispatcher in self.bin_path.iterdir():
        with open(dispatcher, 'r') as f:
          lines = f.readlines()
        with open(dispatcher, 'w') as f:
          for line in lines:
            if original in line:
              line = patched
            f.write(line)

    # Windows specific fixes
    if sys.platform == 'win32':
      for dispatcher in self.entry_point_path.iterdir():
        if dispatcher.suffix == '.bat':
          with open(dispatcher, 'r') as f:
            lines = f.readlines()
          with open(dispatcher, 'w') as f:
            for line in lines:
              # correct python must already be in PATH
              if r'@set LIBTBX_PYEXE=%LIBTBX_PREFIX%\..\python.exe' in line:
                line = '@set LIBTBX_PYEXE=python.exe'
              # simplify batch file path
              elif r'@"%LIBTBX_PYEXE%" "%LIBTBX_PREFIX%\..\lib\site-packages' in line:
                python_file = line.split('site-packages')[-1].strip()
                line = r'@"%LIBTBX_PYEXE%" "%~dp0\..\..\..{python_file}"'.format(python_file=python_file)
              # do not change PATH
              elif 'PATH=' in line:
                continue
              f.write(line.strip())
              f.write('\n')

    # add entry points for some commands
    dispatchers = list(self.entry_point_path.iterdir())
    for dispatcher in dispatchers:
      # ignore __init__.py
      if dispatcher.name == '__init__.py':
        dispatchers.remove(dispatcher)
        continue
      # import modules cannot have .
      dispatcher_import = dispatcher.stem.replace('.', '_')
      if dispatcher.name in self.binary_files:
        dispatcher_import = dispatcher.name.replace('.', '_')
      entry_point_file = self.entry_point_path /  (dispatcher_import + '.py')
      entry_point = self.entry_point_template.format(dispatcher_name=dispatcher.name)
      with open(entry_point_file, 'w') as f:
        f.write(entry_point)

    # update pyproject.toml with entry points
    with open('pyproject.toml', 'r') as f:
      lines = f.readlines()

    with open('pyproject.toml', 'w') as f:
      for line in lines:
        if 'INSERT_SCRIPTS_HERE' in line:
          for dispatcher in dispatchers:
            dispatcher_stem = dispatcher.stem
            if dispatcher.name in self.binary_files:
              dispatcher_stem = dispatcher.name
            dispatcher_import = dispatcher_stem.replace('.', '_')
            line = f'"{dispatcher_stem}" = "libtbx.core.dispatchers.{dispatcher_import}:run_command"'
            f.write(line)
            f.write('\n')
          f.write('\n')
        else:
          f.write(line)

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
      or 'dist-info' in os.fspath(relative_path.parent) \
      or 'libtbx.pythonw' in relative_path.name:
      pass
    elif file_path.name in self.binary_files:
      dest = (self.entry_point_path / file_path.name)
      self.bin_files.append(dest)
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
    # Windows
    elif sys.platform == 'win32':
      if 'Library' in relative_path.parent.parts:
        library_path = Path(os.fspath(file_path).split('Library')[-1][1:])
        library_parts = library_path.parent.parts[0]
        if ('bin' in library_parts and not library_path.name.endswith('.exe')) \
          or (library_path.name[:-4]) in self.binary_files:
          dest = self.entry_point_path / library_path.name
          self.bin_files.append(dest)
        elif 'share' in library_parts \
          or 'include' in library_parts:
          dest = (self.core_path / library_path)
          self.src_files.append(dest)
        elif 'lib' in library_parts:
          dest = (self.lib_path / library_path.name).resolve()
          self.lib_files.append(dest)
      elif 'Lib' in relative_path.parent.parts:
        library_path = Path(os.fspath(file_path).split('Lib')[-1][1:])
        if '__pycache__' in library_path.parent.parts \
          or 'egg-info' in os.fspath(library_path.parent) \
          or 'dist-info' in os.fspath(library_path.parent):
          pass
        elif 'site-packages' in relative_path.parent.parts:
          dest = (self.src_path / Path(os.fspath(file_path).split('site-packages')[-1][1:])).resolve()
          self.src_files.append(dest)
        else:
          dest = (self.lib_path / library_path)
          self.lib_files.append(dest)

    if dest is not None:
      os.makedirs(dest.parent, exist_ok=True)
      shutil.copyfile(file_path, dest)
      shutil.copymode(file_path, dest)
      if dest in self.bin_files:
        os.chmod(dest, 0o755)
      print(f'''\
    Copying {file_path}
            {dest}\
    ''')
      return True
    else:
      print(f'''\
    Ignoring {file_path}\
    ''')
      return False

  # ---------------------------------------------------------------------------
  def fix_rpaths(self, filename):

    # replace @rpath with CONDA_PREFIX
    new_rpath = os.environ.get('CONDA_PREFIX', None)
    assert new_rpath is not None, 'The conda environment must be active.'
    new_rpath = Path(new_rpath) / 'lib'

    if os.path.isabs(filename):
      file_path = filename
    if filename.endswith('dylib'):
      file_path = new_rpath / filename
    else:
      file_path = Path(self.lib_path) / filename
    if not file_path.exists():
      file_path = Path(self.entry_point_path) / filename
    assert file_path.exists(), file_path

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
        if library == filename or library == filename.split('/')[-1]:
          continue
        new_lib = new_rpath / library
        assert new_lib.exists(), new_lib
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
def create_wheel(prefix_path):
  converter = CondaWheelConverter()
  result = converter.copy_files(prefix_path)

  return result

# =============================================================================
if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--conda-package-path', type=str,
                      help='The root directory of the extracted conda package.',
                      required=True)
  namespace = parser.parse_args()
  result = create_wheel(namespace.conda_package_path)
  assert result
