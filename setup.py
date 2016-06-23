from setuptools import setup

setup(
    install_requires=['xigt>=1.0', 'nltk>=3.0.0', 'lxml>=3.4.1', 'nose>=1.3.0'],
    dependency_links=[
        "git+ssh://git@github.com:goodmami/xigt.git"
    ],
    version='1.0',
    description='INterlinear Text ENrichment Toolkit',
    author_email='rgeorgi@uw.edu',
    url='https://github.com/rgeorgi/intent',
    packages=['intent']
)