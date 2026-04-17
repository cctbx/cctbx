"""
Script for downloading the phenix_regression artifact
"""
import argparse
import os
import shutil
import sys
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.exceptions import ProtocolError, ReadTimeoutError
from urllib3.util.retry import Retry

# =============================================================================
# def construct_url(organization, pipelineId, project, run_id, api_version, artifactName):
def construct_url(organization, project, run_id, api_version):
  # https://docs.microsoft.com/en-us/rest/api/azure/devops/pipelines/artifacts/get?view=azure-devops-rest-6.0
  # url = f'https://dev.azure.com/{organization}/{project}/_apis/pipelines/{pipelineId}/runs/{runId}/artifacts?artifactName={artifactName}&$expand=signedContent&api-version={api_version}'

  # https://docs.microsoft.com/en-us/rest/api/azure/devops/build/artifacts/list?view=azure-devops-rest-6.0
  # url = f'https://dev.azure.com/{organization}/{project}/_apis/build/builds/{buildId}/artifacts?artifactName={artifactName}&api-version=6.0'
  url = f'https://dev.azure.com/{organization}/{project}/_apis/build/builds/{run_id}/artifacts?api-version={api_version}'
  return url

def get_run_id(organization, project, definitions, api_version):
  # https://docs.microsoft.com/en-us/rest/api/azure/devops/build/builds/list?view=azure-devops-rest-6.0
  # https://dev.azure.com/{organization}/{project}/_apis/build/builds?definitions={definitions}&queues={queues}&buildNumber={buildNumber}&minTime={minTime}&maxTime={maxTime}&requestedFor={requestedFor}&reasonFilter={reasonFilter}&statusFilter={statusFilter}&resultFilter={resultFilter}&tagFilters={tagFilters}&properties={properties}&$top={$top}&continuationToken={continuationToken}&maxBuildsPerDefinition={maxBuildsPerDefinition}&deletedFilter={deletedFilter}&queryOrder={queryOrder}&branchName={branchName}&buildIds={buildIds}&repositoryId={repositoryId}&repositoryType={repositoryType}&api-version={api_version}
  # url = f'https://dev.azure.com/{organization}/{project}/_apis/build/builds?api-version=6.0'
  url = f'https://dev.azure.com/{organization}/{project}/_apis/build/builds?definitions={definitions}&resultFilter=succeeded&statusFilter=completed&api-version={api_version}'
  return url

# =============================================================================
# https://stackoverflow.com/questions/16694907/download-large-file-in-python-with-requests
# modified to use a specific filename
def download_file(url, local_filename, max_retries=5):
  """Stream-download a URL to a local file with retry on transient failures.

  Two layered retry mechanisms are used. ``urllib3.Retry`` on the
  ``HTTPAdapter`` retries the request on retryable HTTP statuses
  (429, 500, 502, 503, 504) and connection errors during request
  setup. An outer loop with exponential backoff retries the whole
  download on streaming-time errors raised while reading the
  response body. The two retry counters do not share state.

  The download is written to ``<local_filename>.part`` and atomically
  renamed to ``local_filename`` on success, so a partial file is never
  visible to downstream tooling and any pre-existing file at
  ``local_filename`` is left untouched until the download completes.

  Parameters
  ----------
  url : str
      The URL of the file to download.
  local_filename : str
      Path where the downloaded content will be written on success.
  max_retries : int, optional
      Maximum number of retries for both the inner ``urllib3.Retry``
      and the outer streaming loop. Default is 5.

  Raises
  ------
  requests.exceptions.HTTPError
      If ``raise_for_status()`` fires on a non-retryable HTTP status.
  requests.exceptions.RetryError
      If the inner ``urllib3.Retry`` exhausts on a retryable status
      in ``status_forcelist``.
  requests.exceptions.ConnectionError
      If connection setup repeatedly fails past the inner retry
      budget (also covers ``ConnectTimeout`` and ``SSLError`` as
      subclasses).
  urllib3.exceptions.ProtocolError
      If a streaming protocol error persists past ``max_retries``
      retries on the outer loop.
  urllib3.exceptions.ReadTimeoutError
      If a streaming read timeout persists past ``max_retries``
      retries on the outer loop.
  OSError
      If the local filesystem cannot be written (e.g. ENOSPC,
      permission error, or a failed rename).
  """
  retry_strategy = Retry(
    total=max_retries,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
  )
  adapter = HTTPAdapter(max_retries=retry_strategy)
  session = requests.Session()
  session.mount('https://', adapter)
  session.mount('http://', adapter)
  tmp_filename = local_filename + '.part'
  for attempt in range(max_retries + 1):
    try:
      with session.get(url, stream=True) as r:
        r.raise_for_status()
        with open(tmp_filename, 'wb') as f:
          shutil.copyfileobj(r.raw, f)
      os.replace(tmp_filename, local_filename)
      return
    except (
      ProtocolError,
      ReadTimeoutError,
      requests.exceptions.ChunkedEncodingError,
    ) as e:
      if attempt >= max_retries:
        raise
      backoff = 2 ** attempt if attempt > 0 else 0
      print(f'{type(e).__name__} on attempt {attempt + 1}/{max_retries + 1}: {e}. Retrying in {backoff}s...')
      time.sleep(backoff)

# =============================================================================
def run():
  parser = argparse.ArgumentParser(description=__doc__)

  parser.add_argument('--organization', default=None, type=str,
    help='The name of the Azure DevOps organization.')
  parser.add_argument('--project', default=None, type=str,
    help='Project ID or project name')
  parser.add_argument('--run-id', default=None, type=int,
    help='ID of the run of that pipeline, also called the build id')
  parser.add_argument('--definitions', default=None, type=int,
    help='Build definition used if run-id is not available')
  parser.add_argument('--artifact-name', default=None, type=str,
    help='The artifact name to download')
  parser.add_argument('--local-filename', default='artifact.zip', type=str,
    help='The local filename for the downloaded artifact')
  parser.add_argument('--api-version', default='7.1', type=str,
    help='Version of the API to use')
  parser.add_argument('--accessToken', default=None, type=str,
    help='Azure Pipelines access token for accessing the resource')

  # show help if no arguments are provided
  if len(sys.argv) == 1:
    parser.print_help()
    parser.exit()

  namespace = parser.parse_args()

  # get latest runID for "Update data cache" pipeline
  run_id = namespace.run_id
  if run_id is None:
    if namespace.definitions is None:
      raise ValueError('A definitions id is needed if run-id is not available.')
    url = get_run_id(
      organization=namespace.organization,
      project=namespace.project,
      definitions=namespace.definitions,
      api_version=namespace.api_version
    )
    print(url)
    if namespace.accessToken is not None:
      r = requests.get(url, auth=('user', namespace.accessToken))
    else:
      r = requests.get(url)
    print(r.status_code)
    run_id = None
    if r.status_code == 200:
      j = r.json()
      run_id = j['value'][0]['id']
    else:
      print('URL did not succeed')
      print(r.text)
      sys.exit(1)

  # get URL for downloading artifact
  url = construct_url(
    organization=namespace.organization,
    project=namespace.project,
    run_id=run_id,
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
    phenix_regression = None
    for value in j['value']:
      if value['name'] == namespace.artifact_name:
        phenix_regression = value
        break
    raw_url = phenix_regression['resource']['downloadUrl']
    print(raw_url)
  else:
    print('URL did not succeed')
    print(r.text)
    sys.exit(1)

  # download file
  download_file(raw_url, namespace.local_filename)

# =============================================================================
if __name__ == '__main__':
  sys.exit(run())
