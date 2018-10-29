#!/usr/bin/env python

from setuptools import setup

setup(
    name='cards',
    version='0.1',
    description="Server to respond to Facebook's crawler, " +
                "Twitter's crawler, etc.",
    author='Troy McConaghy',
    author_email='troy@ascribe.io',
    packages=['ascribe_cards'],
    license='LGPLv3',
    classifiers=[
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
    ],
)
