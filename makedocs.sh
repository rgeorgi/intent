#!/usr/bin/env bash
sphinx-apidoc-3.4 -f src -o doc/source > sphinx.log 2> sphinx.err
sphinx-build-3.4 doc/source doc/build >> sphinx.log 2>> sphinx.err
open doc/build/index.html
