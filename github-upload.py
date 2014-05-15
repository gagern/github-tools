#!/usr/bin/python3

import argparse
import base64
import json
import os.path
import sys
import urllib.error
import urllib.request

# Create access-token file using https://github.com/settings/applications
# and store it in a file "access-token" in the same directory as this script
access_token = None

def readAccessToken():
    global access_token
    fn = __file__
    while access_token is None:
        atn = os.path.join(os.path.dirname(fn), 'access-token')
        if os.path.exists(atn):
            with open(atn, 'r') as f:
                access_token = f.read().strip()
                return
        if not os.path.islink(fn):
            break
        fn = os.path.join(os.path.dirname(fn), os.readlink(fn))

def myurlopen(req):
    try:
        return urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        sys.stderr.write('URL: {}\n'.format(req.full_url))
        sys.stderr.write('HTTP error document:\n')
        sys.stderr.buffer.write(e.fp.read() + b'\n')
        raise

def authHeader():
    if access_token is not None:
        return 'token ' + access_token
    elif args.password is not None:
        auth = owner + ':' + args.password
        auth = base64.b64encode(auth.encode('utf-8'))
        auth = auth.decode('ascii').replace('\n', '')
        return auth
    else:
        print('No authorization available, specify --password or create token',
              file=sys.stderr)
        sys.exit(2)
    
def jsonDialog(url, body=None, headers=None, method=None):
    if isinstance(body, (dict, list)):
        body = json.dumps(body).encode('ascii')
    if headers is None:
        headers = dict()
    headers.setdefault('Content-Type', 'application/json')
    headers['Authorization'] = authHeader()
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with myurlopen(req) as con:
        resp = con.read()
        cs = con.info().get_param('charset', 'ascii')
        resp = resp.decode(cs)
    resp = json.loads(resp)
    return resp

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
    readAccessToken()
    upload()
