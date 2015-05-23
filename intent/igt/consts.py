'''
Store the constants that are used in the XIGT formats.
'''


#===============================================================================
# String Conventions ---
#===============================================================================

# Lines ------------------------------------------------------------------------
ODIN_TYPE  = 'odin'

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
ODIN_LANG_TAG = 'L'
ODIN_GLOSS_TAG = 'G'
ODIN_TRANS_TAG = 'T'
ODIN_CORRUPT_TAG = 'CR'

#===============================================================================
# Metadata
#===============================================================================

# The overall types for intent-specific meta
# and xigt-general meta.
XIGT_META_TYPE     = 'xigt-meta'
INTENT_META_TYPE   = 'intent-meta'

# Define the strings for data source and data method

XIGT_DATA_PROV='data-provenance'
XIGT_DATA_METH='method'             # The attribute for marking which method was used
XIGT_DATA_SRC ='source'             # The attribute for marking that this was INTENT
XIGT_DATA_FROM='projected-from'     # The attribute for marking which tier was used to make this one (for projection)
XIGT_DATA_ALNF='aligned-with'       # The attribute for marking the alignment used for projection.
XIGT_DATA_DATE='date'               # The attribute for marking


# Now, define intent as the data-source provider...
INTENT_META_SOURCE = 'intent'

# Let's also add a string for the intent extended information
INTENT_EXTENDED_INFO = 'extended-data'

# Now, for intent-specific data, let's identify
# the strings to use for identifying the tier's
# token type.
INTENT_TOKEN_TYPE  = 'token-type'
INTENT_GLOSS_WORD  = 'word'
INTENT_GLOSS_MORPH = 'sub-word'

#===============================================================================
# Methods
#===============================================================================



INTENT_ALN_GIZA = 'mgiza'
INTENT_ALN_HEUR = 'heur'

INTENT_POS_CLASS  = 'classifier'
INTENT_POS_PROJ   = 'projection'
INTENT_POS_TAGGER = 'stanford-tagger'

INTENT_PS_PARSER  = 'stanford-parser'
INTENT_PS_PROJ    = 'projection'

INTENT_DS_PARSER  = 'stanford-parser'
INTENT_DS_PROJ    = 'projection'

MANUAL_POS        = 'supervised'


# ===============================================================================
# ID STYLES
# ===============================================================================
ID_DEFAULT                   = 'default'    # e.g. "t1"
ID_SAME_TYPE_DIFFERENT_TIERS = 'diff-tiers' # e.g. "t-w"
ID_SAME_TYPE_DIFFERENT_ITEMS = 'diff-items' # e.g. "t1-w"
ID_SAME_TYPE_ALTERNATE       = 'alternate'  # e.g. "pos_a"