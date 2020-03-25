# -*- coding: utf-8 -*-

# DO NOT EDIT THIS FILE!
# This file has been autogenerated by dephell <3
# https://github.com/dephell/dephell

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

readme = ''

setup(
    long_description=readme,
    name='fn_graph_studio',
    version='0.2.10',
    description='A web based explorer for fn_graph function composers',
    python_requires='==3.*,>=3.7.0',
    author='James Saunders',
    author_email='james@businessoptics.biz',
    license='MIT',
    entry_points={
        "console_scripts": [
            "run_graph_studio = fn_graph_studio.cli:run_studio_command"
        ]
    },
    packages=['fn_graph_studio'],
    package_dir={"": "."},
    package_data={"fn_graph_studio": ["*.css"]},
    install_requires=[
        'dash==1.*,>=1.7.0', 'dash-core-components==1.*,>=1.6.0',
        'dash-interactive-graphviz==0.*,>=0.1.0',
        'dash-split-pane==1.*,>=1.0.0', 'dash-treebeard==0.*,>=0.0.1',
        'fn-graph>=0.5.0', 'pandas==0.*,>=0.25.3', 'plotly==4.*,>=4.4.0',
        'sh==1.*,>=1.12.14'
    ],
    extras_require={"dev": ["black==18.*,>=18.3.0"]},
)
