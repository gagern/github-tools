#!/usr/bin/python2

import argparse
import base64
import email.utils
import io
import json
import os.path
import requests
import sys


class FormDataItem(object):

    def __init__(self, name, body = None):
        self.headers = [b'Content-Disposition: form-data']
        self.add_param('name', name)
        self.body = body

    def _fmt_param(self, name, value):
        if not any(ch in value for ch in '"\\\r\n'):
            try:
                return '{}="{}"'.format(name, value).encode('ascii')
            except UnicodeEncodeError:
                pass
        value = email.utils.encode_rfc2231(value, 'utf-8')
        return '{}*={}'.format(name, value).encode('ascii')

    def _tail_param(self, name, value):
        return b'; ' + self._fmt_param(name, value)

    def add_param(self, name, value):
        self.headers[0] += self._tail_param(name, value)

    def add_header(self, name, value, **args):
        header = '{}: {}'.format(name, value)
        header = header.encode('ascii')
        for k, v in args.items():
            header += self._tail_param(k, v)
        self.headers.append(header)

    def render(self):
        return b'\r\n'.join(self.headers + [b'', self.body])

    def __contains__(self, seq):
        return seq in self.body or any(seq in h for h in self.headers)


class FormData(object):

    def __init__(self):
        self.parts = []
        self.boundary = None

    def setText(self, name, value):
        part = FormDataItem(name, value.encode('utf-8'))
        part.add_header('Content-Type', 'text/plain', charset='utf-8')
        part.add_header('Content-Transfer-Encoding', '8bit')
        self.parts.append(part)
        return part

    def setFile(self, name, value, filename=None, mimetype=None):
        if mimetype is None:
            mimetype = 'application/octet-stream'
        part = FormDataItem(name, value)
        if filename is not None:
            part.add_param('filename', filename)
        part.add_header('Content-Type', mimetype)
        part.add_header('Content-Transfer-Encoding', 'binary')
        self.parts.append(part)
        return part

    def get_boundary(self):
        while self.boundary is None:
            boundary = b'-=' + base64.urlsafe_b64encode(os.urandom(15)) + b'=-'
            if not any(boundary in part for part in self.parts):
                self.boundary = boundary
        return self.boundary

    def get_content_type(self):
        return ('multipart/form-data; boundary="{}"'
                .format(self.get_boundary()))

    def http_headers(self):
        return {'Content-Type': self.get_content_type()}

    def http_body(self):
        boundary = b'--' + self.get_boundary()
        b = io.BytesIO()
        for part in self.parts:
            b.write(boundary)
            b.write(b'\r\n')
            b.write(part.render())
            b.write(b'\r\n')
        b.write(boundary)
        b.write(b'--\r\n')
        return b.getvalue()


req_config = {'verbose': sys.stderr}

def upload(owner, password, repo, path, description=None, mimetype=None):
    with open(path, 'rb') as fd:
        data = fd.read()
    filename = os.path.basename(path)
    tmpnam = path + '.upload.tmp'
    if os.path.exists(tmpnam):
        with open(tmpnam, 'rb') as f:
            r = f.read()
        resp = json.loads(r)
    else:
        req = dict(name=filename, size=len(data))
        if description is not None:
            req['description'] = description
        if mimetype is not None:
            req['content_type'] = mimetype
        url = 'https://api.github.com/repos/{}/{}/downloads'
        url = url.format(owner, repo)
        body = json.dumps(req).encode('ascii')
        headers = {'Content-Type': 'application/json'}
        r = requests.post(
            url,
            config=req_config,
            data=body,
            headers=headers,
            auth=(owner, password),
            )
        r.raise_for_status()
        print('Preparing {}: {} {}'.format(filename, r.status_code, r.reason))
        with open(tmpnam, 'wb') as f:
            f.write(r.content)
        print(r.text)
        resp = r.json
    resp['sas'] = 201
    mapping = [
        ('key', 'path'),
        ('acl', 'acl'),
        ('success_action_status', 'sas'),
        ('Filename', 'name'),
        ('AWSAccessKeyId', 'accesskeyid'),
        ('Policy', 'policy'),
        ('Signature', 'signature'),
        ('Content-Type', 'mime_type'),
    ]
    fd = FormData()
    for name, key in mapping:
        value = resp[key]
        fd.setText(name, str(value))
    fd.setFile('file', data, filename, mimetype)
    url = resp['s3_url']
    body = fd.http_body()
    headers = fd.http_headers()
    r = requests.post(
        url,
        config=req_config,
        data=body,
        headers=headers,
        )
    r.raise_for_status()
    print('Uploading {}: {} {}'.format(filename, r.status_code, r.reason))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Upload files for GitHub')
    parser.add_argument('-u', '--owner', required=True,
                        help="Github user name")
    parser.add_argument('-r', '--repository', required=True,
                        help="Name of the repository")
    parser.add_argument('-p', '--password', required=True,
                        help="GitHub password")
    parser.add_argument('-d', '--description', help="Description for the file")
    parser.add_argument('-t', '--type', help="MIME type of the file")
    parser.add_argument('file')
    args = parser.parse_args()
    upload(args.owner, args.password, args.repository,
           args.file, args.description, args.type)
