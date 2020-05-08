# -*- coding: utf-8 -*-

# DO NOT EDIT THIS FILE!
# This file has been autogenerated by dephell <3
# https://github.com/dephell/dephell

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import os.path

readme = ''
here = os.path.abspath(os.path.dirname(__file__))
readme_path = os.path.join(here, 'README.rst')
if os.path.exists(readme_path):
    with open(readme_path, 'rb') as stream:
        readme = stream.read().decode('utf8')

setup(
    long_description=readme,
    name='fn_graph_studio',
    version='0.5.3',
    description='A web based explorer for fn_graph function composers',
    python_requires='==3.*,>=3.7.0',
    project_urls={
        "homepage": "https://github.com/BusinessOptics/fn_graph_studio",
        "repository": "https://github.com/BusinessOptics/fn_graph_studio"
    },
    author='James Saunders',
    author_email='james@businessoptics.biz',
    license='MIT',
    entry_points={
        "console_scripts": ["fn_graph_studio = fn_graph_studio.cli:cli"]
    },
    packages=['fn_graph_studio'],
    package_dir={"": "."},
    package_data={"fn_graph_studio": ["*.css", "assets/*.ico"]},
    install_requires=[
        'dash==1.*,>=1.7.0', 'dash-ace-persistent==0.*,>=0.3.4',
        'dash-core-components==1.*,>=1.6.0', 'dash-cytoscape==0.*,>=0.1.1',
        'dash-dangerously-set-inner-html==0.*,>=0.0.2',
        'dash-interactive-graphviz==0.*,>=0.2.0',
        'dash-split-pane==1.*,>=1.0.0', 'dash-treebeard==0.*,>=0.0.1',
        'fn-graph>=0.7.2', 'matplotlib==3.*,>=3.2.1', 'networkx==2.*,>=2.4.0',
        'pandas>=0.25.3', 'plotly==4.*,>=4.4.0', 'pygments==2.*,>=2.6.1',
        'seaborn==0.*,>=0.10.0', 'sh==1.*,>=1.0.0', 'statsmodels==0.*,>=0.11.1'
    ],
    extras_require={"dev": ["black==18.*,>=18.3.0"]},
)
