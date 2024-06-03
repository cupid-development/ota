#!/usr/bin/env python
import hashlib
import json
import os
import shutil
import sys
import zipfile

from collections import defaultdict
from datetime import datetime
from time import mktime

if len(sys.argv) < 2:
    print("usage python {} /path/to/mirror/base/url".format(sys.argv[0]))
    sys.exit()

FILE_BASE = sys.argv[1]
BUILDS = defaultdict(lambda: [])

# We serve only full OTAs for now
PREFIX = "full"
# Amount of builds to keep per device
BUILDS_TO_KEEP = 3

DEVICES = os.listdir(os.path.join(FILE_BASE, PREFIX))

for device in DEVICES:
    # Each device directory contains a directory with a build date
    # Let's delete extraneous builds (i.e. old ones).
    builds = os.listdir(os.path.join(FILE_BASE, PREFIX, device))
    # Sorting them like this allows us to have the newer builds last
    to_keep = sorted(builds)[-BUILDS_TO_KEEP:]
    to_delete = sorted(builds)[::-1][BUILDS_TO_KEEP:]

    for directory in to_delete:
        shutil.rmtree(os.path.join(FILE_BASE, PREFIX, device, directory), ignore_errors=True)

    for build in to_keep:
        build_dir = os.path.join(FILE_BASE, PREFIX, device, build)
        files = os.listdir(build_dir)
        otapackage = next(file for file in files if file.endswith('.zip'))
        extra_imgs = [file for file in files if file.endswith('.img')]
        _, version, builddate, buildtype, device = os.path.splitext(otapackage)[0].split('-')

        files = []
        for file in (otapackage, *extra_imgs):
            file_path = os.path.join(build_dir, file)
            with open(file_path, "rb") as f:
                sha256 = hashlib.sha256()
                sha1 = hashlib.sha1()
                for buf in iter(lambda : f.read(128 * 1024), b''):
                    sha256.update(buf)
                    sha1.update(buf)
            size = os.path.getsize(file_path)

            files.append({
                'filename': file,
                'filepath': os.path.join('/', PREFIX, device, build, file),
                'sha1': sha1.hexdigest(),
                'sha256': sha256.hexdigest(),
                'size': size
            })

        with open(os.path.join(build_dir, "metadata.json")) as build_metadata_file:
            build_metadata = json.load(build_metadata_file)
            
            BUILDS[device].append({
                'date': '{}-{}-{}'.format(builddate[0:4], builddate[4:6], builddate[6:8]),
                'datetime': build_metadata['timestamp'],
                'files': files,
                'os_patch_level': build_metadata['os_patch_level'],
                'type': buildtype.lower(),
                'version': version
            })

print(json.dumps(BUILDS, indent=4))
