'''
Store the constants that are used in the XIGT formats.
'''


#===============================================================================
# String Conventions ---
#===============================================================================

# Lines ------------------------------------------------------------------------
ODIN_TIER_TYPE  = 'odin'

STATE_ATTRIBUTE = 'state'

RAW_STATE, RAW_ID     = 'raw', 'r'
CLEAN_STATE, CLEAN_ID = 'cleaned', 'c'
NORM_STATE, NORM_ID   = 'normalized', 'n'

# Words ------------------------------------------------------------------------

WORDS_TYPE = 'words'

TRANS_WORD_TYPE = 'words'
GLOSS_WORD_TYPE = 'glosses'
LANG_WORD_TYPE  = 'words'

LANG_WORD_ID = 'w'
GLOSS_WORD_ID = 'gw'
TRANS_WORD_ID = 'tw'

# Phrases ----------------------------------------------------------------------

TRANS_PHRASE_TYPE = 'translations'
LANG_PHRASE_TYPE  = 'phrases'

TRANS_PHRASE_ID = 't'
LANG_PHRASE_ID = 'p'

# Morphemes --------------------------------------------------------------------

LANG_MORPH_TYPE = 'morphemes'
GLOSS_MORPH_TYPE = 'glosses'

LANG_MORPH_ID = 'm'
GLOSS_MORPH_ID= 'g'

# POS --------------------------------------------------------------------------
POS_TIER_TYPE = 'pos'
POS_TIER_ID   = 'pos'

# Alignments -------------------------------------------------------------------

ALN_TIER_TYPE = 'bilingual-alignments'

L_T_ALN_ID = 'a'
G_T_ALN_ID = 'a'

SOURCE_ATTRIBUTE = 'source'
TARGET_ATTRIBUTE = 'target'

# Phrase structures ------------------------------------------------------------

PS_TIER_TYPE = 'phrase-structure'
PS_TIER_ID   = 'ps'


PS_CHILD_ATTRIBUTE = 'children'

# Dependencies -----------------------------------------------------------------

DS_TIER_TYPE = 'dependencies'
DS_TIER_ID   = 'ds'

DS_DEP_ATTRIBUTE = 'dep'
DS_HEAD_ATTRIBUTE = 'head'

# ODIN Line Tags ---------------------------------------------------------------
ODIN_TAG_ATTRIBUTE = 'tag'
ODIN_JUDGMENT_ATTRIBUTE = 'judgment'
ODIN_LANG_TAG = 'L'
ODIN_GLOSS_TAG = 'G'
ODIN_TRANS_TAG = 'T'
ODIN_CORRUPT_TAG = 'CR'

#===============================================================================
# Metadata
#===============================================================================

# The overall types for intent-specific meta
# and xigt-general meta.
XIGT_META_TYPE   = 'xigt-meta'
INTENT_META_TYPE = 'intent-meta'

# Define the strings for data source and data method

DATA_PROV = 'data-provenance'
DATA_METH_ATTR = 'method'             # The attribute for marking which method was used
DATA_SRC_ATTR  = 'source'             # The attribute for marking that this was INTENT
DATA_FROM_ATTR = 'projected-from'     # The attribute for marking which tier was used to make this one (for projection)
DATA_ALNF_ATTR = 'projection-alignment'       # The attribute for marking the alignment used for projection.
DATA_DATE_ATTR = 'date'               # The attribute for marking


# Now, define intent as the data-source provider...
INTENT_META_SOURCE = 'intent'
EDITOR_META_SOURCE = 'manual'

# Let's also add a string for the intent extended information
INTENT_EXTENDED_INFO = 'extended-data'

# Now, for intent-specific data, let's identify
# the strings to use for identifying the tier's
# token type.
INTENT_TOKEN_TYPE  = 'token-type'
INTENT_GLOSS_WORD  = 'word'
INTENT_GLOSS_MORPH = 'sub-word'

# =============================================================================
# Statistical aligners
# =============================================================================
ALIGNER_GIZA = 'giza'
ALIGNER_FASTALIGN = 'fast_align'

SYMMETRIC_INTERSECT       = 'intersection'
SYMMETRIC_UNION           = 'union'
SYMMETRIC_GROW_DIAG       = 'grow_diag'
SYMMETRIC_GROW_DIAG_FINAL = 'grow_diag_final'

#===============================================================================
# Methods
#===============================================================================

INTENT_ALN_GIZA = 'mgiza'
INTENT_ALN_GIZAHEUR = 'mgiza+heur'
INTENT_ALN_HEUR = 'heur'
INTENT_ALN_HEURPOS = 'heur+pos'
INTENT_ALN_MANUAL = 'manual'

INTENT_ALN_1TO1   = '1to1'

INTENT_POS_CLASS  = 'classifier'
INTENT_POS_PROJ   = 'projection'
INTENT_POS_TAGGER = 'stanford-tagger'
INTENT_POS_MANUAL = 'supervised'

INTENT_PS_PARSER  = 'stanford-parser'
INTENT_PS_PROJ    = 'projection'

INTENT_DS_PARSER  = 'stanford-parser'
INTENT_DS_PROJ    = 'projection'
INTENT_DS_MANUAL  = 'manual'




# ===============================================================================
# ID STYLES
# ===============================================================================
ID_DEFAULT                   = 'default'    # e.g. "t1"
ID_SAME_TYPE_DIFFERENT_TIERS = 'diff-tiers' # e.g. "t-w"
ID_SAME_TYPE_DIFFERENT_ITEMS = 'diff-items' # e.g. "t1-w"
ID_SAME_TYPE_ALTERNATE       = 'alternate'  # e.g. "pos_a"

# ===============================================================================
# ARGUMENT Stuff
# ===============================================================================

ARG_INFILE = 'IN_FILE'
ARG_OUTFILE= 'OUT_FILE'

# -------------------------------------------
# Alignment types
# -------------------------------------------
ARG_ALN_GIZA = 'giza'
ARG_ALN_GIZAHEUR = 'gizaheur'
ARG_ALN_HEUR = 'heur'
ARG_ALN_HEURPOS = 'heurpos'
ARG_ALN_MANUAL = 'manual'
ARG_ALN_ANY = 'any'

# Map from the argument form of alignment to
# the metadata form.
ALN_ARG_MAP = {ARG_ALN_GIZA:INTENT_ALN_GIZA,
               ARG_ALN_GIZAHEUR:INTENT_ALN_GIZAHEUR,
               ARG_ALN_HEUR:INTENT_ALN_HEUR,
               ARG_ALN_HEURPOS:INTENT_ALN_HEURPOS,
               ARG_ALN_MANUAL:INTENT_ALN_MANUAL,
               ARG_ALN_ANY:None}

ARG_ALN_METHODS_ALL = [ARG_ALN_GIZA, ARG_ALN_GIZAHEUR, ARG_ALN_HEUR, ARG_ALN_HEURPOS, ARG_ALN_MANUAL, ARG_ALN_ANY]
ARG_ALN_METHODS     = [ARG_ALN_GIZA, ARG_ALN_GIZAHEUR, ARG_ALN_HEUR, ARG_ALN_HEURPOS]
ALN_VAR = 'alignment_list'

# -------------------------------------------
# Symmetricization algorithms.
# -------------------------------------------

ALN_SYM_VAR = 'align_symmetric'
ALN_SYM_TYPES = [None, SYMMETRIC_INTERSECT, SYMMETRIC_UNION, SYMMETRIC_GROW_DIAG_FINAL, SYMMETRIC_GROW_DIAG]

# -------------------------------------------
# POS types.
# -------------------------------------------
ARG_POS_TRANS = 'trans'
ARG_POS_CLASS = 'class'
ARG_POS_PROJ  = 'proj'
ARG_POS_NONE  = 'none'
ARG_POS_MANUAL= 'manual'
ARG_POS_ANY   = 'any'

ARG_POS_ENRICH_METHODS = [ARG_POS_CLASS, ARG_POS_PROJ, ARG_POS_TRANS]
ARG_POS_EXTRACT_METHODS= [ARG_POS_CLASS, ARG_POS_PROJ, ARG_POS_NONE, ARG_POS_MANUAL, ARG_POS_ANY]

ARG_POS_MAP = {ARG_POS_CLASS:INTENT_POS_CLASS,
               ARG_POS_PROJ:INTENT_POS_PROJ,
               ARG_POS_NONE:ARG_POS_NONE,
               ARG_POS_MANUAL:INTENT_POS_MANUAL,
               ARG_POS_ANY:None}


POS_VAR = 'pos_list'

# -------------------------------------------
# Classifier Feature list
# -------------------------------------------
CLASS_FEATS_SW    = 'sw'
CLASS_FEATS_ALN   = 'aln'
CLASS_FEATS_NUM   = 'num'
CLASS_FEATS_SUF   = 'suf'
CLASS_FEATS_PRE   = 'pre'
CLASS_FEATS_NUMSW = 'numsw'
CLASS_FEATS_PRESW = 'prevsw'
CLASS_FEATS_NEXSW = 'nextsw'
CLASS_FEATS_DICT  = 'dict'
CLASS_FEATS_NDICT = 'nextdict'
CLASS_FEATS_PDICT = 'prevdict'

CLASS_FEATS_CONTEXT = [CLASS_FEATS_PRESW, CLASS_FEATS_NEXSW]
CLASS_FEATS_DICTS   = [CLASS_FEATS_DICT, CLASS_FEATS_NDICT, CLASS_FEATS_PDICT]
CLASS_FEATS_AFFIX   = [CLASS_FEATS_PRE, CLASS_FEATS_SUF]
CLASS_FEATS_BASIC   = [CLASS_FEATS_SW, CLASS_FEATS_ALN, CLASS_FEATS_NUM]

CLASS_FEATS_DEFAULT = CLASS_FEATS_AFFIX + [CLASS_FEATS_DICT, CLASS_FEATS_SW]

CLASS_FEATS_ALL     = CLASS_FEATS_BASIC + CLASS_FEATS_AFFIX + [CLASS_FEATS_NUMSW] + CLASS_FEATS_CONTEXT + CLASS_FEATS_DICTS


# -------------------------------------------
# Parse Stuff
# -------------------------------------------
ARG_PARSE_TRANS = 'trans'
ARG_PARSE_PROJ = 'proj'

PARSE_TYPES = [ARG_PARSE_TRANS, ARG_PARSE_PROJ]

PARSE_VAR = 'parse_list'

# ===============================================================================
# GRAMMATICAL
# ===============================================================================
morpheme_boundary_chars = ['-','=']
morpheme_interior_chars = ['.',':']

punc_chars   = '\.,\?!\]\[\(\)\;\{\}\xbf\xa1\u2026'
quote_chars  = '\"\'\`\xab\xbb\x8b\x9b'
other_chars  = ':-=<>/\\\*\+_'
paren_chars  = '\[\]\{\}\(\)'

all_punc_chars = punc_chars+quote_chars+other_chars
all_punc_re = '[{}]'.format(all_punc_chars)
all_punc_re_mult = '{}+'.format(all_punc_re)
entirely_punctuation = '^'+all_punc_re_mult+'$'

punc_re      = '[{}]'.format(punc_chars)
punc_re_mult = '{}+'.format(punc_re)

no_punc_re   = '[^{}]'.format(punc_chars)
word_re      = '[^{}\s]+'.format(punc_chars)

list_re = '(?:[0-9]+|[a-z]|i+)'
quote_re = '[\'"\`]'

PUNC_TAG = 'PUNC'
UNKNOWN_TAG  = 'UNK'

# -------------------------------------------
# For extraction
# -------------------------------------------
SENT_TYPE_T_G = 'tg'
SENT_TYPE_T_L = 'tl'

NORM_LEVEL = 1000

# -------------------------------------------
# For reproduction
# -------------------------------------------
REPRO_DS       = 'ds'
REPRO_POS_IGT  = 'pos-igt'
REPRO_POS_MONO = 'pos-mono'
REPRO_CHOICES = [REPRO_DS, REPRO_POS_IGT, REPRO_POS_MONO]