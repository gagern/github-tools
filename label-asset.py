#!/usr/bin/python3

import argparse
import os.path
import sys
import urllib.parse

from gagern.githubtools.common import readAccessToken, jsonDialog

def chooseRelease():
    url = 'https://api.github.com/repos/{owner}/{repo}/releases'
    url = url.format(owner=args.owner, repo=args.repository)
    releases = jsonDialog(url)
    for r in releases:
        if r['tag_name'] == args.tag:
            return r
    print('Release does not exist', file=sys.stderr)
    sys.exit(2)

def chooseAsset(assets):
    if args.asset_id is not None:
        i = int(args.asset_id)
        for a in assets:
            if a['id'] == i:
                return a
    else:
        for a in assets:
            if a['name'] == args.filename:
                return a
    print('Asset does not exist', file=sys.stderr)
    sys.exit(2)

def label():
    release = chooseRelease()
    asset = chooseAsset(release['assets'])
    url = asset['url']
    body = {'name': args.filename, 'label': args.label}
    print(jsonDialog(url, body, method='PATCH'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Upload files for GitHub')
    parser.add_argument('-u', '--owner', required=True,
                        help="Github user name")
    parser.add_argument('-r', '--repository', required=True,
                        help="Name of the repository")
    parser.add_argument('-p', '--password', help="GitHub password",
                        default=None)
    parser.add_argument('-i', '--asset-id', help="Asset ID",
                        default=None)
    parser.add_argument('-t', '--tag', required=True,
                        help="Tag name of the release")
    parser.add_argument('filename')
    parser.add_argument('label')
    args = parser.parse_args()
    readAccessToken(args.password)
    label()
