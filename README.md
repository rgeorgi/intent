INTENT
======

The **IN**terlinear **T**ext **EN**richment **T**oolkit.
This readme will describe the aims of the INTENT package, as well as a
quickstart guide to get up and running.

Project Goals
-------------

The INTENT package is intended to take instances of Interlinear Glossed Text
(**IGT**) found in places such as the Online Databse of Interlinear Text
(**ODIN**)[^1] and use a variety of methods to enrich the instances. Currently,
INTENT:

*  Adds alignment information to IGT instances
*  Adds POS Tag information to IGT instances

And INTENT will soon:

* Add dependency structures to IGT

## Dependencies ##
Currently, INTENT is written in Python 3, and depends on several external [python modules](#python-modules) and [other tools](#other-tools).


###<a name="python-modules"></a> Python Modules ###
* [XIGT](http://goodmami.github.io/xigt/)
* [NLTK](http://www.nltk.org/)
* The [lxml](http://lxml.de/) XML library

These modules must be either installed or on the PYTHONPATH variable when running INTENT. **[pip](https://pypi.python.org/pypi/pip)** is strongly reccomended for installing NLTK and lxml.

###<a name="other-tools"></a> Other Tools ###
* [MALLET](http://mallet.cs.umass.edu/) (MAchine Learning for LanguagE Toolkit)
* [Stanford Log-linear Part-Of-Speech Tagger](http://nlp.stanford.edu/software/tagger.shtml)
* [mgiza++](http://www.kyloo.net/software/doku.php/mgiza:overview)


[^1]: Xia, F., Lewis, W. D., Goodman, M. W., & Crowgey, J. (2014). *Enriching ODIN.* Presented at the Proceedings of the Ninth International Conference on Language Resources and Evaluation, Reykjavik, Iceland.
