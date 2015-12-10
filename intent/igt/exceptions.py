#===============================================================================
# Exceptions
#===============================================================================

class RGXigtException(Exception): pass

# • Format Exceptions ------------------------------------------------------------

class XigtFormatException(RGXigtException): pass
class NoNormLineException(XigtFormatException): pass
class MultipleNormLineException(XigtFormatException): pass

class NoTransLineException(XigtFormatException): pass
class NoLangLineException(XigtFormatException):	pass
class NoGlossLineException(XigtFormatException): pass
class EmptyGlossException(XigtFormatException): pass

class NoODINRawException(XigtFormatException):	pass

class RawTextParseError(RGXigtException): pass

# • Alignment and Projection Exceptions ------------------------------------------

class GlossLangAlignException(RGXigtException):	pass

class ProjectionException(RGXigtException): pass

class ProjectionTransGlossException(ProjectionException): pass

class PhraseStructureProjectionException(RGXigtException): pass


def project_creator_except(msg_start, msg_end, created_by):

    if created_by:
        msg_start += ' by the creator "%s".' % created_by
    else:
        msg_start += '.'
    raise ProjectionException(msg_start + ' ' + msg_end)
