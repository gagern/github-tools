#!/usr/bin/python3

import argparse
import os.path
import urllib.parse

from gagern.githubtools.common import readAccessToken, jsonDialog

def chooseRelease():
    url = 'https://api.github.com/repos/{owner}/{repo}/releases'
    url = url.format(owner=args.owner, repo=args.repository)
    releases = jsonDialog(url)
    for r in releases:
        if r['tag_name'] == args.tag:
            return r
    if args.create_release:
        r = jsonDialog(url, {'tag_name': args.tag})
        return r
    else:
        print('Release does not exist, perhaps create it with --create-release',
              file=sys.stderr)
        sys.exit(2)

def upload():
    release = chooseRelease()
    print('Release is {}'.format(release['html_url']))
    rid = release['id']
    name = os.path.basename(args.file)
    qname = urllib.parse.quote(name, safe='')
    url = release['upload_url'].split('{', 1)[0] + '?name=' + qname
    contenttype = args.type
    if contenttype is None:
        contenttype = 'application/octet-stream'
    with open(args.file, 'rb') as f:
        body = f.read()
    print('Uploading {} to {}'.format(name, url))
    resp = jsonDialog(url, body, {'Content-Type': contenttype})
    body = {'name': name}
    if args.description is not None:
        body['label'] = args.description
    url = resp['url']
    jsonDialog(url, body) # method='PATCH' ?

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Upload files for GitHub')
    parser.add_argument('-u', '--owner', required=True,
                        help="Github user name")
    parser.add_argument('-r', '--repository', required=True,
                        help="Name of the repository")
    parser.add_argument('-p', '--password', help="GitHub password",
                        default=None)
    parser.add_argument('-t', '--tag', required=True,
                        help="Tag name of the release")
    parser.add_argument('-c', '--create-release', help="Create the release",
                        default=False, action='store_true')
    parser.add_argument('-d', '--description', help="Description for the file",
                        default=None)
    parser.add_argument('-m', '--type', help="MIME type of the file",
                        default=None)
    parser.add_argument('file')
    args = parser.parse_args()
    readAccessToken(args.password)
    upload()
