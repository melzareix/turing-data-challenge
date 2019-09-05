"""
Main Module to clone repo, load files and run analysis.
"""
from __future__ import absolute_import
from analyzer import Analyzer
import string
import git
import json
import sys
import random
import os
import re
import ast


# regex for python2 print to python3 print.
rgx = re.compile(r'print ([/s]?(?! e)(.)+)')


def get_files(path, ext='.py'):
    """
    Get all .py files in the repo directory.
    """
    filteredFiles = []
    for root, _, files in os.walk(path):
        filteredFiles += map(lambda f: os.path.join(root, f),
                             (filter(lambda x: x.strip().endswith(ext),
                                     files)))
    return filteredFiles


def process_file(file):
    """
    Process the file.
    1. Load the file
    2. Replace python2 print with python3 print.
    3. Remove empty Lines.
    4. Parse the code into AST.
    5. Visit the ast nodes to collect statistics.
    """
    with open(file, "r") as source:
        lines = rgx.sub(r'print(\1)', source.read())
        text = os.linesep.join(
            [s for s in lines.splitlines() if s.strip()])
        if (len(text) <= 0):
            return None
        tree = ast.parse(text)
        for node in ast.walk(tree):
            node.depth = 0
            for child in ast.iter_child_nodes(node):
                child.parent = node
                child.depth = 0

        analyzer = Analyzer()
        analyzer.visit(tree)
        analyzer.calc_duplicates(text)
        return analyzer.stats()


def clone(repo):
    """
    Clone the repo in a temp path.
    """
    repo_path = ''.join(random.choice(
        string.ascii_uppercase + string.digits) for _ in range(20))
    script_path = os.path.abspath(os.path.dirname(__file__))
    repo_path = os.path.join(script_path, '../repos', repo_path)
    git.Git().clone(repo.strip(), repo_path)
    return repo_path


def merge_stats(repo, stats):
    """
    Merge the stats from all the files to a single result
    for that repository.
    """
    result = {
        'repository_url': repo,
        'number of lines': 0,
        'libraries': [],
        'nesting factor': 0,
        'code duplication': 0,
        'average parameters': 0,
        'average variables': 0
    }

    num_of_files = len(stats)

    if num_of_files == 0:
        return json.dumps(result)

    sum_funcs = 0
    sum_func_params = 0
    sum_vars = 0
    sum_dup_ratio = 0
    sum_loop_depth = 0
    sum_num_loops = 0

    for stat in stats:
        result['number of lines'] += stat['num_lines']
        result['libraries'] += stat['libraries']

        sum_vars += stat['num_vars']

        sum_funcs += stat['funcs']['num_funcs']
        sum_func_params += stat['funcs']['num_params']

        sum_dup_ratio += stat['duplicate_code']['ratio']

        sum_num_loops += stat['loop_depth']['number_of_loops']
        sum_loop_depth += stat['loop_depth']['sum_of_loops']

    result['average variables'] = sum_vars / num_of_files
    result['libraries'] = list(set(result['libraries']))

    if sum_funcs == 0:
        result['average parameters'] = 0
    else:
        result['average parameters'] = sum_func_params / sum_funcs

    result['code duplication'] = sum_dup_ratio / num_of_files

    if sum_num_loops == 0:
        result['nesting factor'] = 0
    else:
        result['nesting factor'] = sum_loop_depth / sum_num_loops

    return json.dumps(result)


def analyze_repo(repo):
    """
    Clone the repo and process all python code files.
    """
    try:
        path = clone(repo)
    except Exception:
        return merge_stats(repo, [])

    files = get_files(path)
    stats = {}
    global_stats = []
    print('processing', repo)
    failed_files = 0
    for file in files:
        try:
            stats = process_file(file)
        except Exception:
            failed_files += 1

        if stats is not None and len(stats.keys()) > 0:
            global_stats.append(stats)
    print('done ..', len(files) - failed_files, 'out of', len(files))
    return merge_stats(repo, global_stats)


if __name__ == "__main__":
    # Testing
    print(analyze_repo('https://github.com/fepegar/slicer-blockmatching/'))
