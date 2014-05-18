#!/usr/bin/env python
import os
import re
import glob
import json
import shutil
import codecs
import hashlib
import datetime
import subprocess
from jinja2 import Template

languages = {
    '.py': 'Python',
    '.rb': 'Ruby',
    '.clj': 'Clojure',
    '.c': 'C',
    '.scm': 'Scheme',
    '.go': 'Go',
    '.hs': 'Haskell',
}

lexers = {
    '.py': 'python',
    '.rb': 'ruby',
    '.clj': 'clojure',
    '.c': 'c',
    '.scm': 'scheme',
    '.go': 'go',
    '.hs': 'haskell',
}

interpreters = {
    '.py': 'python2',
    '.rb': 'ruby',
    '.clj': 'clojure',
    '.scm': 'mit-scheme-native --quiet <',
    '.go': 'go run',
}

compilers = {
    '.c': 'gcc -Ofast -std=c11 -o a.out',
    '.hs': 'ghc -O2 -o a.out -outputdir /tmp',
}

post_template = Template('''\
---
date: {{ problem.last_modified }}
title: Project Euler Problem {{ problem.number }} Solution
excerpt: {{ problem.excerpt }}
math: true
---

{% if problem.question or problem.answer %}
## Overview

{% if problem.question %}
### Question

{{ problem.question }}
{% endif %}
{% endif %}

{% if problem.commentary %}
## Commentary

{{ problem.commentary }}
{% endif %}

## Solutions
{% for solution in problem.solutions %}
### {{ solution.language }}

{{ solution }}
{% if solution.execution_time %}
{{ solution.execution_time }}
{% endif %}
{% endfor %}
''')

index_template = Template('''\
---
title: Project Euler Solutions
excerpt: Solutions to {{ problems | length }} Project Euler problems in Python, Ruby, Haskell, Clojure, Go, and Scheme.
---

Welcome to my solutions for [Project Euler](http://projecteuler.net/).
The solutions are [hosted on GitHub](http://github.com/zacharydenton/euler).
If you want to make a contribution, feel free to fork the repository and
submit a pull request.

This directory of solutions is generated by a Python script. It scans through
the aforementioned git repository and compiles it all into the posts you see
below. If you want, you can take a look at [this script's source code](https://github.com/zacharydenton/zacharydenton.com/blob/master/bin/euler.py).
In fact, [this entire website is open source](http://github.com/zacharydenton/zacharydenton.com).

------

{% for problem in problems %}
## [Project Euler Problem {{ problem.number }} Solution]({{ problem.number }}/)

{% for language in problem.languages %}<span class="label label-info">{{ language }}</span> {% endfor %}

Updated: <time datetime="{{ problem.last_modified }}" data-updated="true">{{ problem.last_modified.strftime("%B %d, %Y") }}</time>

------
{% endfor %}
''')

cache_dir = os.path.join(os.path.dirname(__file__), ".cache")
if not os.path.isdir(cache_dir):
    os.makedirs(cache_dir)

class Problem(object):
    def __init__(self, path):
        self.path = path
        self.dirname = os.path.split(self.path)[-1]
        self.solutions = []

        for solution in os.listdir(self.path):
            basename, filetype = os.path.splitext(solution)
            if filetype in languages.keys():
                solution = Solution(os.path.join(self.path, solution))
                if solution.test():
                    self.solutions.append(solution)

        if not self.solutions: return

        self.solutions.sort(key = lambda s: s.language)

        # set last_modified to the latest modification date of any of the solutions
        self.last_modified = sorted([solution.last_modified for solution in self.solutions])[-1]

        # strip zeros from directory
        self.number = int(re.sub('^0+', '', self.dirname))

        # generate a filename for the post
        self.filename = '%s.md' % (self.number)

        # grab the question from question.markdown
        try:
            question_file = glob.glob(os.path.join(self.path, 'question.*'))[0]
            basename, extension = os.path.splitext(question_file)
            self.question = codecs.open(question_file, 'r', 'utf-8').read()
        except Exception as e:
            self.question = ''

        # grab the answer from answer.markdown
        try:
            answer_file = glob.glob(os.path.join(self.path, 'answer.*'))[0]
            basename, extension = os.path.splitext(answer_file)
            self.answer = codecs.open(answer_file, 'r', 'utf-8').read()
        except Exception as e:
            self.answer = ''

        # grab the commentary from commentary.markdown
        try:
            commentary_file = glob.glob(os.path.join(self.path, 'commentary.*'))[0]
            basename, extension = os.path.splitext(commentary_file)
            self.commentary = codecs.open(commentary_file, 'r', 'utf-8').read()
        except:
            self.commentary = ''

    @property
    def title(self):
        return "Problem {number} Solution".format(number=self.number)

    @property
    def link(self):
        return '/project-euler-solutions/%s/' % self.number

    @property
    def languages(self):
        return sorted(list(set(sln.language for sln in self.solutions)))

    def save(self, directory):
        self.content = post_template.render(problem=self).encode('utf-8')
        open(os.path.join(directory, self.filename), 'w').write(self.content)

    def __unicode__(self):
        return self.content

    def __str__(self):
        return self.__unicode__()

    @property
    def excerpt(self):
        if len(self.languages) == 1 and len(self.solutions) > 1:
            output = "This page presents solutions to Project Euler Problem %s in %s." % (self.number, self.languages[0])
        elif len(self.languages) == 1:
            return "This page presents a %s solution to Project Euler Problem %s." % (self.languages[0], self.number)
        else:
            output = "This page presents solutions to Project Euler Problem %s in " % self.number
            if len(self.languages) == 2:
                return output + "%s and %s." % (self.languages[0], self.languages[1])
            else:
                return output + "%s and %s." % (', '.join(self.languages[:-1]), self.languages[-1])

class Solution(object):
    def __init__(self, path):
        basename, filetype = os.path.splitext(path)
        self.language = languages[filetype]
        self.interpreter = interpreters.get(filetype)
        self.compiler = compilers.get(filetype)
        self.lexer = lexers[filetype]
        self.path = path
        self.basename = os.path.basename(self.path)
        self.answer = open(os.path.join(os.path.dirname(self.path), 'answer.txt')).read().strip()
        self.github_link = 'https://github.com/zacharydenton/euler/blob/master' + self.path.replace(os.path.expanduser('~/code/euler'), '')
        self.raw_link = 'https://raw.github.com/zacharydenton/euler/master' + self.path.replace(os.path.expanduser('~/code/euler'), '')
        self.content = codecs.open(self.path, 'r', 'utf-8').read()
        self.last_modified = datetime.date.fromtimestamp(os.path.getmtime(self.path))
        self.sha1 = hashlib.sha1(self.content).hexdigest()
        self.execution_time = ''

    def __unicode__(self):
        output = '```%s\n' % (self.lexer)
        output += self.content 
        output += '```\n'
        return output 

    def __str__(self):
        return self.__unicode__()

    def test(self):
        output = None
        try:
            output = json.loads(open(os.path.join(cache_dir, self.sha1)).read())
        except:
            if self.compiler:
                subprocess.check_call("{} {}".format(self.compiler, self.path), shell=True)
                output = subprocess.Popen('bash -c "time ./a.out"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
                os.unlink("a.out")
            elif self.interpreter:
                output = subprocess.Popen('bash -c "time %s %s"' % (self.interpreter, self.path), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
            with open(os.path.join(cache_dir, self.sha1), 'w') as cache:
                cache.write(json.dumps(output))
        finally:
            if output:
                if self.compiler:
                    self.execution_time = '''\
```bash
$ {compiler} {filename}
$ time ./{filename}
{time}
```
'''.format(compiler=self.compiler.rsplit(' a.out')[0], filename=self.basename.rsplit('.')[0], time=output[1].strip())
                else:
                    self.execution_time = '''\
```bash
$ time %s %s
%s
```
''' % (self.interpreter, self.basename, output[1].strip())
                self.execution_time = replace_tabs(self.execution_time, 7)
                if output[0].strip() == self.answer:
                    return True
            print("failed: %s %s" % (self.interpreter, self.path))
            if os.path.exists(os.path.join(cache_dir, self.sha1)):
                os.remove(os.path.join(cache_dir, self.sha1))
            return False

def replace_tabs(s, ts=4):
    return '\n'.join(replace_tab(line, ts) for line in s.split('\n'))

def replace_tab(s, ts=4):
    result = str()
    for c in s:
        if c == '\t':
            while (len(result) % ts != 0):
                result += ' ';
        else:
            result += c    
    return result

def generate_posts(problems, output_dir):
    '''rebuild all posts.'''
    for problem in problems:
        problem.save(output_dir)
        
def generate_index(problems, output):
    problems = sorted(problems, key = lambda problem: problem.number)
    content = index_template.render(
        problems=problems,
    ).encode('utf-8')
    open(output, 'w').write(content)

def is_problem(path):
    directory = os.path.split(path)[-1]
    if not (os.path.isdir(path) and directory.isdigit()):
        return False

    for solution in os.listdir(path):
        basename, filetype = os.path.splitext(solution)
        if filetype in languages.keys():
            return True

    return False

def main():
    euler_dir = os.path.expanduser('~/code/euler')
    posts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pages', 'project-euler-solutions')
    if not os.path.isdir(posts_dir):
        os.makedirs(posts_dir)
    index = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pages', 'project-euler-solutions.md')

    problems = []
    for directory in os.listdir(euler_dir):
        path = os.path.join(euler_dir, directory)
        if is_problem(path):
            problems.append(Problem(path))

    problems = filter(lambda p: p.solutions, problems)
    problems.sort(key = lambda p: p.number)

    for i, problem in enumerate(problems):
        if i > 0:
            problem.previous = problems[i-1]
        if i < len(problems) - 1:
            problem.next = problems[i+1]

    generate_posts(problems, posts_dir)
    generate_index(problems, index)

if __name__ == "__main__":
    main()
