import base64
import json
import os.path
import sys
import urllib.error
import urllib.request

# Create access-token file using https://github.com/settings/applications
# and store it in a file "access-token" in the same directory as this script
access_token = None
password = None

def readAccessToken(pwd):
    global access_token, password
    if pwd is not None:
        password = pwd
        return
    fn = __file__
    fn = os.path.dirname(fn)
    fn = os.path.dirname(fn)
    fn = os.path.dirname(fn)
    fn = os.path.join(fn, 'access-token')
    if os.path.exists(fn):
        with open(fn, 'r') as f:
            access_token = f.read().strip()
            return

def urlopen(req):
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
    elif password is not None:
        auth = owner + ':' + password
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
    with urlopen(req) as con:
        resp = con.read()
        cs = con.info().get_param('charset', 'ascii')
        resp = resp.decode(cs)
    resp = json.loads(resp)
    return resp
