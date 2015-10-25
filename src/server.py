#!/usr/bin/env python3

import json
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import tornado.gen
import tornado.ioloop
import tornado.log
import tornado.process
import tornado.web


GITHUB_USER_MAP = {
    "m13253": "Star Brilliant",
    "Jamesits": "James Swineson",
    "luvletter": "Luv Letter"
}


class PullRequestHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def post(self):
        self.set_status(204)
        self.finish()
        payload = json.loads(self.request.body.decode('utf-8', 'replace'))
        if 'pull_request' not in payload:
            logging.warn('not a pull request, ignore')
            return

        user = payload['pull_request']['user']['login']
        head = payload['pull_request']['head']
        url = head['html_url'] + '/tree/' + head['sha']

        clone_dest = tempfile.mkdtemp()
        try:
            clone_url = head['repo']['clone_url']
            clone_branch = head['ref']
            clone_command = [
                'git', 'clone', '--progress', '-b', clone_branch, '--depth', '1', clone_url, 'repo'
            ]
            clone_ret = 1
            clone_count = 3
            while clone_ret and clone_count:
                clone_process = tornado.process.Subprocess(clone_command, cwd=clone_dest, stdin=subprocess.DEVNULL)
                clone_ret = yield clone_process.wait_for_exit()
                clone_count -= 1
            if clone_ret:
                clone_stdout = clone_process.stdout.read()
                clone_stderr = clone_process.stderr.read()
                return (yield self.report(user, url, 'Unable to download source code', clone_stdout, clone_stderr))

            logging.info('Clone OK')

            repo_dir = os.path.join(clone_dest, 'repo')
            build_command = ['make', 'all']
            build_process = tornado.process.Subprocess(build_command, cwd=repo_dir, stdin=subprocess.DEVNULL)
            build_ret = yield build_process.wait_for_exit()
            if build_ret:
                build_stdout = build_process.stdout.read()
                build_stderr = build_process.stderr.read()
                return (yield self.report(user, url, 'Build error', build_stdout, build_stderr))

            logging.info('Build OK')

            input_file = os.path.join(repo_dir, 'stdin.txt')
            output_file = os.path.join(repo_dir, 'stdout.txt')
            run_command = ['make', '-s', 'run']
            with open(input_file, 'rb') as fin:
                run_process = tornado.process.Subprocess(run_command, cwd=repo_dir, stdin=fin, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            run_ret = yield run_process.wait_for_exit()
            run_stdout = run_process.stdout.read()
            run_stderr = run_process.stderr.read()
            logging.info('Run OK')
            if run_ret:
                return (yield self.report(user, url, 'Program exited abnormally', run_stdout, run_stderr))
            else:
                with open(output_file, 'rb') as fout:
                    result_correct = run_stdout == fout.read() 
                return (yield self.report(user, url, None if result_correct else 'Wrong answer', run_stdout, run_stderr))
        finally:
            shutil.rmtree(clone_dest, True)

    @tornado.gen.coroutine
    def report(self, user, url, error, stdout, stderr):
        sys.stderr.write(repr(payload))
        sys.stderr.write('\n')
        self.application.db.con.execute(
            'INSERT INTO records (user, url, iserror, error, stdout, stderr) VALUES (?, ?, ?, ?, ?);', (
                GITHUB_USER_MAP.get(user, user),
                url,\
                error is not None,
                error or '',
                stdout.decode('utf-8', 'replace'),
                stdout.decode('utf-8', 'replace')
            )
        )


class DBMan:
    def __init__(self):
        self.con = sqlite3.connect(':memory:')
        self.con.execute('CREATE TABLE records (id INTEGER PRIMARY KEY AUTOINCREMENT, user STRING, url STRING, iserror BOOL, error STRING, stdout STRING, stderr STRING);')

    def __del__(self):
        self.con.close()


application = tornado.web.Application([
    (r"/pr", PullRequestHandler),
])


if __name__ == '__main__':
    tornado.log.enable_pretty_logging()
    application.db = DBMan()
    application.listen(8080)
    tornado.ioloop.IOLoop.current().start()
