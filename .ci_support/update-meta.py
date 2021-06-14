"""
Script for updating the artifact URL for the source tarball
"""
import argparse
import sys

import requests

from urllib.parse import urlsplit, urlunsplit

# =============================================================================
# def construct_url(organization, pipelineId, project, runId, api_version, artifactName):
def construct_url(organization, project, runId, api_version):
  # https://docs.microsoft.com/en-us/rest/api/azure/devops/pipelines/artifacts/get?view=azure-devops-rest-6.0
  # url = f'https://dev.azure.com/{organization}/{project}/_apis/pipelines/{pipelineId}/runs/{runId}/artifacts?artifactName={artifactName}&$expand=signedContent&api-version={api_version}'

  # https://docs.microsoft.com/en-us/rest/api/azure/devops/build/artifacts/list?view=azure-devops-rest-6.0
  # url = f'https://dev.azure.com/{organization}/{project}/_apis/build/builds/{buildId}/artifacts?artifactName={artifactName}&api-version=6.0'
  url = f'https://dev.azure.com/{organization}/{project}/_apis/build/builds/{runId}/artifacts?api-version={api_version}'
  return url

# =============================================================================
def run():
  parser = argparse.ArgumentParser(description=__doc__)

  parser.add_argument('--organization', default=None, type=str,
    help='The name of the Azure DevOps organization.')
  # parser.add_argument('--pipelineId', default=None, type=int,
  #   help='ID of the pipeline')
  parser.add_argument('--project', default=None, type=str,
    help='Project ID or project name')
  parser.add_argument('--runId', default=None, type=int,
    help='ID of the run of that pipeline, also called the build id')
  # parser.add_argument('--api-version', default='6.0-preview.1', type=str,
  parser.add_argument('--api-version', default='6.0', type=str,
    help='Version of the API to use')
  # parser.add_argument('--artifactName', default=None, type=str,
  #   help='Name of the artifact')
  parser.add_argument('--accessToken', default=None, type=str,
    help='Azure Pipelines access token for accessing the resource')
  parser.add_argument('--new-version', default=None, type=str,
    help='The version of the artifact')
  parser.add_argument('--meta-path', default=None, type=str,
    help='The path to meta.yaml')

  # show help if no arguments are provided
  if len(sys.argv) == 1:
    parser.print_help()
    parser.exit()

  namespace = parser.parse_args()

  # get URL for downloading artifact
  url = construct_url(
    organization=namespace.organization,
    # pipelineId=namespace.pipelineId,
    project=namespace.project,
    runId=namespace.runId,
    # artifactName=namespace.artifactName,
    api_version=namespace.api_version
  )
  print(url)
  if namespace.accessToken is not None:
    r = requests.get(url, auth=('user', namespace.accessToken))
  else:
    r = requests.get(url)
  print(r.status_code)
  raw_url = None
  if r.status_code == 200:
    j = r.json()
    # use first artifact
    raw_url = j['value'][0]['resource']['downloadUrl']
    print(raw_url)
  else:
    print('URL did not succeed')
    print(r.text)
    sys.exit(1)

  # modify URL to get file
  unix_url = None
  win_url = None
  if raw_url is not None:
    file_url = urlsplit(raw_url)
    new_url = list(file_url)
    new_url[3] = 'file&subPath=%2Fcctbx-{{ version }}.tar.gz'
    unix_url = urlunsplit(new_url)
    # Windows does not like the %2F
    new_url[3] = 'file&subPath=/cctbx-{{ version }}.tar.gz'
    win_url = urlunsplit(new_url)

  # modify meta.yaml to use new version and URL
  if (namespace.new_version is not None
      and unix_url is not None
      and win_url is not None):
    with open(namespace.meta_path, 'r') as f:
      lines = f.readlines()
    for i, line in enumerate(lines):
      if i == 0:
        print('Old: ', line)
        lines[i] = r'{% set version = "' + namespace.new_version + r'" %}'
        print('New: ', lines[i])
      if line.startswith('  url:') and line.endswith('[unix]\n'):
        print('Old: ', line)
        lines[i] = f'  url: {unix_url}  # [unix]\n'
        print('New: ', lines[i])
      if line.startswith('  url:') and line.endswith('[win]\n'):
        print('Old: ', line)
        lines[i] = f'  url: {win_url}  # [win]\n'
        print('New: ', lines[i])
    with open(namespace.meta_path, 'w') as f:
      for line in lines:
        f.write(line)

# =============================================================================
if __name__ == '__main__':
  sys.exit(run())

# https://dev.azure.com/phenix-release/phenix-installer/_apis/pipelines/9/runs/1055/artifacts?artifactName=phenix-2021.05.a24&api-version=6.0-preview.1
# https://artprodcus3.artifacts.visualstudio.com/Ae7d56bcd-6398-4fef-808d-577536b26a95/67feccdf-8c7f-4afe-8ff5-f21e77cdbf9d/_apis/artifact/cGlwZWxpbmVhcnRpZmFjdDovL2NjdGJ4LXJlbGVhc2UvcHJvamVjdElkLzY3ZmVjY2RmLThjN2YtNGFmZS04ZmY1LWYyMWU3N2NkYmY5ZC9idWlsZElkLzE2NS9hcnRpZmFjdE5hbWUvY2N0YngtMjAyMS42YTE00/content?format=file&subPath=%2Fcctbx-2021.6a14.tar.gz
