from setuptools import setup

MODULE = 'elife_ga_metrics' # name of the subdirectory your code resides in
NAME = 'elife-ga-metrics' # project name
AUTHORS = ["Luke Skibinski <l.skibinski@elifesciences.org>"] # list of all contributing authors
LICENCE = 'GPLv3' # licence short name
COPYRIGHT = 'eLife Sciences' # copyright owner
VERSION = '2016.02.29' # some sort of natural ordering key
DESCRIPTION = 'google analytics wrangling for elifesciences.org' # long description


def groupby(f, l):
    x, y = [], []
    for v in l:
        (x if f(v) else y).append(v)        
    return x, y

def requirements():
    requisites = open('requirements.txt', 'r').read().splitlines()
    pypi, non_pypi = groupby(lambda r: not r.startswith('-e '), requisites)
    non_pypi = map(lambda v: v[len('-e '):], non_pypi)
    return {
        'install_requires': pypi,
        'dependency_links': non_pypi,
    }

setup(
    name = NAME,
    version = VERSION,
    description = DESCRIPTION,
    long_description = open('README.md', 'r').read(),
    packages = [MODULE],
    package_data={MODULE: ['output/views/*.json', 'output/downloads/*.json']},
    include_package_data=True,
    license = open('LICENCE.txt', 'r').read(),
    **requirements()
)
