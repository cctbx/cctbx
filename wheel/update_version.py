"""
Script for updating the version in pyproject.toml
"""
import argparse
import os

def update_version(filename, version):
  with open(filename, 'r') as f:
    lines = f.readlines()

  with open(filename, 'w') as f:
    for line in lines:
      line = line.rstrip()
      if 'REPLACEME' in line:
        line = line.replace('REPLACEME', version)
      f.write(line)
      f.write('\n')

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description=__doc__)

  parser.add_argument('--filename', default='pyproject.toml', type=str,
    help='The file to be patched')
  parser.add_argument('--version', default=None, type=str,
    help='The version', required=True)

  namespace = parser.parse_args()

  update_version(filename=namespace.filename, version=namespace.version)
