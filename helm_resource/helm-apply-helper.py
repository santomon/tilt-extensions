# Helper script for the Tiltfile's apply cmd. Not intended to be called independently.
#
# Usage:
# python3 helm-apply-helper.py ... [image config keys in order]

import os
import subprocess
import sys
from typing import Dict
from namespacing import add_default_namespace

def _parse_image_string(image: str) -> Dict:
  if '.' in image or 'localhost' in image or image.count(":") > 1:
    registry, repository = image.split('/', 1)
    repository, tag = repository.rsplit(':', 1)
    return {"registry": registry, "repository": repository, "tag": tag}
  repository, tag = image.rsplit(':', 1)
  return {"registry": None, "repository": repository, "tag": tag}

flags = sys.argv[1:]

image_count = int(os.environ['TILT_IMAGE_COUNT'])
for i in range(image_count):
  image = os.environ['TILT_IMAGE_%s' % i]
  key = os.environ.get('TILT_IMAGE_KEY_%s' % i, '')
  if key:
    flags.extend(['--set', '%s=%s' % (key, image)])
    continue

  image_parts = _parse_image_string(image)
  key0 = os.environ.get('TILT_IMAGE_KEY_REGISTRY_%s' % i, '')
  key1 = os.environ.get('TILT_IMAGE_KEY_REPO_%s' % i, '')
  key2 = os.environ.get('TILT_IMAGE_KEY_TAG_%s' % i, '')

  if image_parts['registry']:
    if key0 != '':
      # Image has a registry AND a specific helm key for the registry
      flags.extend(['--set', '%s=%s' % (key0, image_parts["registry"]),
                    '--set', '%s=%s' % (key1, image_parts["repository"])])
    else:
      # Image has a registry but does not have a specific helm key for registry
      flags.extend(['--set', '%s=%s/%s' % (key1, image_parts["registry"], image_parts["repository"])])
  else:
    # Image does NOT have a registry component
    flags.extend(['--set', '%s=%s' % (key1, image_parts["repository"])])
  flags.extend(['--set', '%s=%s' % (key2, image_parts["tag"])])

install_cmd = ['helm', 'install']
install_cmd.extend(flags)

get_cmd = ['helm', 'get', 'manifest']
kubectl_cmd = ['kubectl', 'get']

release_name = os.environ['RELEASE_NAME']
chart = os.environ['CHART']
namespace = os.environ.get('NAMESPACE', '')
if namespace:
  install_cmd.extend(['--namespace', namespace])
  get_cmd.extend(['--namespace', namespace])

install_cmd.extend([release_name, chart])
get_cmd.extend([release_name])
kubectl_cmd.extend(['-oyaml', '-f', '-'])

print("Running cmd: %s" % install_cmd, file=sys.stderr)
subprocess.check_call(install_cmd, stdout=sys.stderr)

print("Running cmd: %s" % get_cmd, file=sys.stderr)
out = subprocess.check_output(get_cmd).decode('utf-8')
is_windows = True if os.name == 'nt' else False
out_with_right_line_endings = out.replace(os.linesep, '\n') if is_windows else out

input = add_default_namespace(out_with_right_line_endings, namespace).encode('utf-8')

print("Running cmd: %s" % kubectl_cmd, file=sys.stderr)
completed = subprocess.run(kubectl_cmd, input=input)
completed.check_returncode()
