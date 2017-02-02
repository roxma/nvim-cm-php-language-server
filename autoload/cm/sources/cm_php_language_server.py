#!/usr/bin/env python
# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

import os
import json
import base64
import subprocess
import sys
import logging
import threading
import os
import re
import logging
import tempfile
import cm_utils
from neovim.api import Nvim

logger = logging.getLogger(__name__)

directory =  os.path.abspath(os.path.dirname(__file__))

# this client should be put into complete-manager, but I havn't locked down the
# api yet, just place it here, using existing api to get the job done.
class LanguageServerClient(threading.Thread):

    def __init__(self):
        self._id = 0
        self._request_cv = {}
        self._stdin_lock = threading.Lock()
        threading.Thread.__init__(self)

    def start(self,args):

        self._args = args
        self._proc = subprocess.Popen(args=args,stdin=subprocess.PIPE,stdout=subprocess.PIPE) # ,stderr=subprocess.DEVNULL

        threading.Thread.start(self)

        req = {
            'method': "initialize",
            'params': {
                'rootPath': os.getcwd(),
                'capabilities': {
                },
            }
        }

        self.request(req)
        # logger.info('initialize result: %s',self.request(req))

    def run(self):

        while True:

            headers = {}
            # parsing headers
            while  True:
                line = self._proc.stdout.readline()
                txt = line.decode()
                # process has already terminated
                if self._proc.poll():
                    logging.error('process has already terminated')
                    break
                if txt=="":
                    continue
                # header section ended
                if txt=="\r\n":
                    break
                # parse header
                try:
                    name,val = txt.strip().split(':')
                    name = name.strip()
                    val = val.strip()
                    headers[name] = val
                except Exception as ex:
                    logger.error('failed to parse header: %s', line)
                    raise

            if 'Content-Length' not in headers:
                if self._proc.poll():
                    logging.error('process has already terminated')
                    break
                else:
                    logger.error('failed parsing headers: %s', headers)
                    continue

            content_length = int(headers['Content-Length'])
            body = self._proc.stdout.read(content_length).decode()
            content = json.loads(body)

            if self.is_response(content):
                id = str(content['id'])
                if id in self._request_cv:
                    cv = self._request_cv[id]['condition']
                    with cv:
                        self._request_cv[id]['response'] = content
                        cv.notify()
                else:
                    logger.error("unhandled response :%s", content)
            elif self.is_notify(content):
                logger.debug('ignoring notification')
            else:
                logger.error('unhandled content: %s', content)

    def is_request(self,req):
        return 'params' in req and 'id' in req

    def is_notify(self,notify):
        return 'params' in notify and 'id' not in notify

    def is_response(self,rsp):
        return ('result' in rsp or 'error' in rsp) and 'id' in rsp

    def _send_request(self,req):

        with self._stdin_lock:
            # increment id
            logger.info('send_request: %s', req)

            body = json.dumps(req).encode('utf-8')

            content_length = len(body)+2

            self._proc.stdin.write(b'Content-Type: application/vscode-jsonrpc; charset=utf8\r\n')
            self._proc.stdin.write(("Content-Length: %s\r\n\r\n" % (content_length)).encode('utf-8'))
            self._proc.stdin.write(body)
            self._proc.stdin.write(b'\r\n')

            self._proc.stdin.flush()

    def request(self,request):
        self._id+=1
        id = self._id
        try:
            cv = threading.Condition()
            with cv:
                # Note: asumming the user's using CPython with GIL to ensure thread
                # safe operation on dictionary
                self._request_cv[str(id)] = dict(condition=cv)
                request['id'] = id
                request['jsonrpc'] = "2.0"
                self._send_request(request)
                logger.info('waiting response')
                cv.wait()
                response = self._request_cv[str(id)]['response']
                logger.info('response: %s', response)
                return response
        finally:
            # cleanup remove tmp storage from _request_cv
            del self._request_cv[str(id)]

    def shutdown(self):
        if self._proc:
            self._proc.terminate()
            self.join()


class Handler:

    def __init__(self,nvim):

        """
        @type nvim: Nvim
        """

        self._nvim = nvim

        args = ['php', os.path.join(directory,'../../../vendor/bin/php-language-server.php')]

        self._php_client = LanguageServerClient()

        self._php_client.start(args=args)

    def cm_refresh(self,info,ctx):

        lnum = ctx['lnum']
        col = ctx['col']
        typed = ctx['typed']
 
        kwtyped = re.search(r'[0-9a-zA-Z_]*?$',typed).group(0)
        startcol = col-len(kwtyped)

        path, filetype = self._nvim.eval('[expand("%:p"),&filetype]')
        if filetype not in ['php','markdown']:
            logger.info('ignore filetype: %s', filetype)
            return

        src = "\n".join(self._nvim.current.buffer[:])

        if filetype=='markdown':
            result = cm_utils.check_markdown_code_block(src,['php'],lnum, col)
            logger.info('try markdown, %s,%s,%s, result: %s', src, col, col, result)
            if result is None:
                return
            src = result['src']
            col = result['col']
            lnum = result['lnum']

        # completion pattern
        if (re.search(r'^(using|use|require|include)', typed) 
            or re.search(r'[\w_]{2,}$',typed)
            or re.search(r'-\>[\w_]*$',typed)
            or re.search(r'::[\w_]*$',typed)
            ):
            pass
        else:
            return

        # create temp file
        path = ''
        with tempfile.NamedTemporaryFile(prefix='cm_php_',delete=False) as f:
            path = f.name
            f.write(src.encode('utf-8'))

        try:
            req = {
                'method': 'textDocument/completion',
                'params': {
                    'textDocument': {
                        'uri': 'file://localhost/' + path
                    },
                    'position': {
                        'line': lnum-1,
                        'character': col-1,
                    },
                }
            }
            response = self._php_client.request(req)
            if not response or not response['result'] or not response['result']['items']:
                logger.info('response empty: %s', response)
                return

            matches = []
            for item in response['result']['items']:
                e = {}
                e['icase'] = 1
                e['word'] = item['label']
                if 'insertText' in item and item['insertText']:
                    e['abbr'] = item['insertText']
                e['dup'] = 1
                if 'documentation' in item and item['documentation'] and len(item['documentation']) < 70:
                    e['menu'] = item['documentation']
                e['info'] = item['documentation']
                matches.append(e)

            # {'additionalTextEdits': None,
            # 'insertText': 'array_walk()',
            # 'label': 'array_walk',
            # 'command': None,
            # 'data': None,
            # 'sortText': None,
            # 'detail': 'bool',
            # 'textEdit': None,
            # 'filterText': None,
            # 'kind': 3, 
            # 'documentation': 'Apply a user function to every member of an array'}

            self._nvim.call('cm#complete', info['name'], ctx, startcol, matches, async=True)

        finally:
            os.remove(path)

    def cm_shutdown(self):
        self._php_client.shutdown()

