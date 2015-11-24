from setuptools import setup

setup(
    install_requires=['xigt>=1.0', 'nltk>=3.0.0', 'lxml>=3.4.1'],
    dependency_links=[
        "git+ssh://git@github.com:goodmami/xigt.git"
    ],
    version='0.4',
    description='INterlinear Text ENrichment Toolkit',
    author_email='rgeorgi@uw.edu',
    url='https://github.com/rgeorgi/intent',
    packages=['intent']
)