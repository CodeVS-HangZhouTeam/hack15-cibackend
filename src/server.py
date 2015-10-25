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
    def get(self):
        self.set_status(404)
        self.finish('404: Not Found')


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
        url = head['repo']['html_url'] + '/tree/' + head['sha']

        clone_dest = tempfile.mkdtemp()
        try:
            clone_url = head['repo']['clone_url']
            clone_branch = head['ref']
            clone_command = [
                'git', 'clone', '-b', clone_branch, '--depth', '1', clone_url, 'repo'
            ]
            clone_count = 3
            for clone_count in range(4, 0, -1):
                logging.info('Start cloning')
                clone_process = tornado.process.Subprocess(clone_command, cwd=clone_dest, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                clone_ret = yield clone_process.wait_for_exit(False)
                if clone_ret:
                    if clone_count == 1:
                        clone_stdout = clone_process.stdout.read()
                        clone_stderr = clone_process.stderr.read()
                        return (yield self.report(user, url, 'Unable to download source code', clone_stdout, clone_stderr))
                else:
                    break

            logging.info('Clone OK')

            repo_dir = os.path.join(clone_dest, 'repo')
            build_command = ['make', 'all']
            build_process = tornado.process.Subprocess(build_command, cwd=repo_dir, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            build_ret = yield build_process.wait_for_exit(False)
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
            run_ret = yield run_process.wait_for_exit(False)
            logging.info('Run OK')
            run_stdout = run_process.stdout.read()
            run_stderr = run_process.stderr.read()
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
        args = (
            GITHUB_USER_MAP.get(user, user),
            url,
            error is not None,
            error or '',
            stdout.decode('utf-8', 'replace'),
            stderr.decode('utf-8', 'replace')
        )
        self.application.db.con.execute('INSERT INTO records (user, url, iserror, error, stdout, stderr) VALUES (?, ?, ?, ?, ?, ?);', args)
        logging.info(repr(args))


class QueryAllHandler(tornado.web.RequestHandler):
    def get(self):
        self.add_header('Access-Control-Allow-Origin', '*')
        cursor = self.application.db.con.cursor()
        cursor.execute('SELECT id, user, url, iserror, error, stdout, stderr FROM records;')
        result = cursor.fetchall()
        self.finish({'meta': {'title': 'C 语言第二课作业：两个数的加法及 if 语句的使用', 'user_total': len(GITHUB_USER_MAP)+1}, 'd': [{'id': c_id, 'user': c_user, 'url': c_url, 'iserror': bool(c_iserror), 'error': c_error, 'stdout': c_stdout, 'stderr': c_stderr} for c_id, c_user, c_url, c_iserror, c_error, c_stdout, c_stderr in result]})


class DBMan:
    def __init__(self):
        self.con = sqlite3.connect(':memory:')
        self.con.execute('CREATE TABLE records (id INTEGER PRIMARY KEY AUTOINCREMENT, user STRING, url STRING, iserror BOOL, error STRING, stdout STRING, stderr STRING);')
        self.con.executemany('INSERT INTO records (user, url, iserror, error, stdout, stderr) VALUES (?, ?, ?, ?, ?, ?);', [
            ('Star Brilliant', 'https://github.com/m13253/hack15-coderepo-submit/tree/63352cd181d593af66143dd46649ceb303ee53e3', False, '', '56 + (-42) = 14\n', 'Please input number A: Please input number B: '),
            ('Star Brilliant', 'https://github.com/m13253/hack15-coderepo-submit/tree/2e513181bca6afe4873a756e41258780c33acbd3', True, 'Build error', "cc     main.c   -o main\n<builtin>: recipe for target 'main' failed\n", "main.c: In function 'main':\nmain.c:4:12: error: 'b' undeclared (first use in this function)\n     int a; b; /*\n            ^\nmain.c:4:12: note: each undeclared identifier is reported only once for each function it appears in\nmake: *** [main] Error 1\n"),
            ('Star Brilliant', 'https://github.com/m13253/hack15-coderepo-submit/tree/623da884dce3672dd33d1345570a1026249a19bc', True, 'Wrong answer', '56 + -42 = 14\n', 'Please input number A: Please input number B: ')
        ])

    def __del__(self):
        self.con.close()


application = tornado.web.Application([
    (r"/pr", PullRequestHandler),
    (r'/query/all', QueryAllHandler)
])


if __name__ == '__main__':
    tornado.log.enable_pretty_logging()
    application.db = DBMan()
    application.listen(8080)
    tornado.ioloop.IOLoop.current().start()
