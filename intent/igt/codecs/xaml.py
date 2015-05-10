"""
Created on Feb 25, 2015

@author: rgeorgi
"""

#===============================================================================
# Logging
#===============================================================================
import logging
import glob
import os



logging.basicConfig()
XAML_LOG = logging.getLogger()
XAML_LOG.setLevel(logging.DEBUG)

from intent.igt.consts import *
from intent.igt.grams import write_gram

from intent.alignment.Alignment import AlignedCorpus, AlignedSent
from intent.eval.AlignEval import AlignEval
from intent.utils.env import classifier, tagger_model
from intent.interfaces.stanford_tagger import StanfordPOSTagger
from intent.interfaces.mallet_maxent import MalletMaxent, train_txt
from intent.utils.token import GoldTagPOSToken
from xigt.consts import ALIGNMENT, SEGMENTATION, CONTENT
from xigt.errors import XigtError
from xigt.ref import ids



#  -----------------------------------------------------------------------------

import lxml.etree
import sys
from intent.igt.rgxigt import RGCorpus, RGTier, RGIgt, RGItem, RGWordTier, RGWord,\
    RGBilingualAlignmentTier, RGTokenTier, RGToken, ProjectionException, gen_tier_id, RGPhraseTier, RGPhrase, \
    add_word_level_info, ProjectionTransGlossException, GlossLangAlignException, strip_pos
import re
from intent.utils.uniqify import uniqify


#===============================================================================
# Other
#===============================================================================
class XamlParseException(Exception): pass

#===============================================================================
# POS Tag
#===============================================================================

def pos(pos_tier, inst, seen_id_mapping):
    sources = [seen_id_mapping.get(xaml_ref(r)) for r in pos_tier.xpath(".//*[local-name()='TagPart']/@Source")]
    source_tiers = uniqify([inst.find(id=r).tier.id for r in sources if inst.find(id=r)])

    if len(source_tiers) > 1:
        raise XamlParseException('POS Tag Tier references more than one tier...')

    source_tier = inst.find(id=source_tiers[0])
    segmented_src_tags = find_aligned_tier_tags(source_tier)

    if 'L' in segmented_src_tags:
        pid = gen_tier_id(inst, POS_TIER_ID, tier_type=POS_TIER_TYPE, alignment=LANG_WORD_ID)
    elif 'T' in segmented_src_tags:
        pid = gen_tier_id(inst, POS_TIER_ID, tier_type=POS_TIER_TYPE, alignment=TRANS_WORD_ID)
    elif 'G' in segmented_src_tags:
        pid = gen_tier_id(inst, POS_TIER_ID, tier_type=POS_TIER_TYPE, alignment=GLOSS_WORD_ID)

    pt = RGTokenTier(id=pid, igt=inst, alignment=source_tier.id, type=POS_TIER_TYPE)

    tagparts = pos_tier.findall('.//{*}TagPart')

    for tagpart in tagparts:
        src = seen_id_mapping.get(xaml_ref(tagpart.attrib['Source']))
        txt = tagpart.attrib['Text']

        pos_t = RGToken(id=pt.askItemId(), alignment=src, text=txt, tier=pos_tier)
        pt.add(pos_t)


    inst.add(pt)



#===============================================================================
# Alignment tools
#===============================================================================

def get_refs(e, seen_id_mapping):
    return [seen_id_mapping.get(xaml_ref(r)) for r in e.xpath(".//*[local-name()='Reference']/text()")]

def get_alignments(aln_tier, seen_id_mapping, reverse=True):
    pairs = []

    for aln_part in aln_tier.findall('.//{*}AlignPart'):

        src_id = seen_id_mapping.get(xaml_ref(aln_part.attrib['Source']))
        tgt_ids = get_refs(aln_part, seen_id_mapping)
        for tgt_id in tgt_ids:
            pairs.append((src_id, tgt_id))

    if reverse:
        return [(y, x) for x, y in pairs]
    else:
        return pairs


def find_aligned_tier_tags(t):
    if SEGMENTATION in t.attributes:
        attr = SEGMENTATION
    else:
        attr = CONTENT
    seg_tier = t.igt.find(id=t.attributes[attr])
    aligned_bits = uniqify([ids(i.attributes[attr])[0] for i in t])

    assert len(aligned_bits) == 1

    item = t.igt.find(id=aligned_bits[0])

    if CONTENT in item.attributes:
        item = t.igt.find(id=item.attributes[CONTENT])


    return item.attributes['tag'].split('+')


def align(aln_tier, inst, seen_id_mapping):
    # Figure out what the source alignment is:
    tgt_id = xaml_ref(aln_tier.attrib['AlignWith'])
    tgt_id = seen_id_mapping[tgt_id]

    tgt_tier = inst.find(id=tgt_id)
    segmented_tgt_tags = find_aligned_tier_tags(tgt_tier)

    # Find all the references contained by tokens inside here....
    refs = aln_tier.xpath(".//*[local-name()='AlignPart']/@Source")

    # Rewrite the reference...
    refs = [seen_id_mapping.get(xaml_ref(r)) for r in refs]

    # Now find the tier
    refs = uniqify([inst.find(id=r).tier.id for r in refs if inst.find(id=r)])

    if len(refs) > 1:
        raise XamlParseException('Alignment tier aligns with multiple other tiers.')

    src_tier = inst.find(id=refs[0])
    segmented_src_tags = find_aligned_tier_tags(src_tier)




    # If we are aligning gloss words and translation words, we need to make a bilingual alignment tier.
    # otherwise, we should just place the alignment attribute on the words.
    bilingual = False
    reverse = False

    if 'G' in segmented_src_tags and 'T' in segmented_tgt_tags:
        bilingual = True
        reverse = True
    elif 'T' in segmented_src_tags and 'G' in segmented_tgt_tags:
        bilingual = True
    elif 'G' in segmented_src_tags and 'L' in segmented_tgt_tags:
        pass
    elif 'L' in segmented_src_tags and 'G' in segmented_tgt_tags:
        reverse = True

    else:
        #print(src_tier.id)
        XAML_LOG.warning("Unknown alignment type: %s - %s" % (src_tier.type, tgt_tier.type))
        #raise XamlParseException("Unknown alignment type: %s - %s" % (src_tier.type, tgt_tier.type))

    aln_pairs = get_alignments(aln_tier, seen_id_mapping, reverse)

    #===========================================================================
    # If reversed, swap things around...
    #===========================================================================
    if reverse:
        temp_tier = src_tier
        src_tier = tgt_tier
        tgt_tier = temp_tier

    #===========================================================================
    # Do the bilingual alignment.
    #===========================================================================

    if bilingual:
        at = RGBilingualAlignmentTier(id=gen_tier_id(inst, L_T_ALN_ID, tier_type=ALN_TIER_TYPE),
                                      source=src_tier.id,
                                      target=tgt_tier.id)
        for src, tgt in aln_pairs:
            at.add_pair(src, tgt)

        inst.add(at)

    # Otherwise, we want to just add the alignment attribute to a words tier.
    else:

        src_tier.alignment = tgt_tier.id

        for src, tgt in aln_pairs:

            src_w = src_tier.find(id=src)
            if src_w:
                src_w.alignment = tgt
            else:
                XAML_LOG.warn('Src token %s not found.' % src)



# -------------------

def xaml_id(e):
    return 'xaml'+e.attrib['Name'].replace('_','')

xaml_ref_re = re.compile('_([\S]+?)}?$')
def xaml_ref(s):
    return 'xaml'+re.search(xaml_ref_re, s).group(1)


def load(xaml_path) -> RGCorpus:
    """

    :rtype : RGCorpus
    """
    xc = RGCorpus()
    xaml = lxml.etree.parse(xaml_path)
    root = xaml.getroot()
    for i, igt in enumerate(root.findall('.//{*}Igt')):

        # Create the new IGT Instance...
        inst = RGIgt(id='i{}'.format(i + 1))

        seen_id_mapping = {}

        # Create the raw tier...
        tt = RGTier(id=RAW_ID, type=ODIN_TYPE, attributes={STATE_ATTRIBUTE: RAW_STATE}, igt=inst)

        # Next, let's gather the text tiers that are not the full raw text tier.
        lines = igt.xpath(".//*[local-name()='TextTier' and not(contains(@TierType,'odin-txt'))]")
        for textitem in lines:

            # Occasionally some broken lines have no text.
            if 'Text' in textitem.attrib:
                tags = re.search('([^\-]+)\-?', textitem.attrib['TierType']).group(1)

                # Enter this id in the seen_id_mapping and give it a better one.
                item_id = tt.askItemId()
                seen_id_mapping[xaml_id(textitem)] = item_id

                item = RGItem(id=item_id, attributes={'tag': tags})
                item.text = textitem.attrib['Text']
                tt.add(item)

        # Add the text tier to the instance.
        inst.append(tt)

        # =======================================================================
        # Segmentation Tiers. ---
        #=======================================================================
        # Now, we start on the segmentation tiers.
        segtiers = igt.findall('.//{*}SegTier')
        for segtier in segtiers:

            # First, we need to figure out what previous
            # tier this one is segmenting.
            sources = uniqify(segtier.xpath('.//@SourceTier'))

            if len(sources) > 1:
                raise XamlParseException('Multiple sources for segmentation line.')

            # Otherwise, find that tier.

            ref_id = seen_id_mapping.get(xaml_ref(sources[0]))
            segmented_raw_item = inst.find(id=ref_id)

            # Now, decide what type of tier we are creating based on the tag of the referenced tier.
            tags = segmented_raw_item.attributes['tag']

            tier_ref = segmented_raw_item.tier.id
            item_ref = segmented_raw_item.id

            word_type = None

            # Set up the attributes by which this tier will
            # refer to the others.
            if 'L' in tags.split('+'):
                seg_attr = SEGMENTATION
                seg_type = LANG_WORD_TYPE
                seg_id = LANG_WORD_ID

                pt = RGPhraseTier(id=gen_tier_id(inst, LANG_PHRASE_ID, LANG_PHRASE_TYPE), type=LANG_PHRASE_TYPE,
                                  content=segmented_raw_item.tier.id)
                pt.add(RGPhrase(id=pt.askItemId(), content=segmented_raw_item.id))
                inst.append(pt)

                tier_ref = pt.id
                item_ref = pt[0].id


            elif 'G' in tags.split('+'):
                seg_attr = CONTENT
                seg_type = GLOSS_WORD_TYPE
                seg_id = GLOSS_WORD_ID

                word_type = 'gloss'

            elif 'T' in tags.split('+'):
                seg_attr = SEGMENTATION
                seg_type = TRANS_WORD_TYPE
                seg_id = TRANS_WORD_ID

                pt = RGPhraseTier(id=gen_tier_id(inst, TRANS_PHRASE_ID, TRANS_PHRASE_TYPE), type=TRANS_PHRASE_TYPE,
                                  content=segmented_raw_item.tier.id)
                pt.add(RGPhrase(id=pt.askItemId(), content=segmented_raw_item.id))
                inst.append(pt)

                tier_ref = pt.id
                item_ref = pt[0].id

            else:
                raise XamlParseException('Unknown tag type in segmentation tier.')





            # Create the new words tier.
            wt_id = gen_tier_id(inst, seg_id, seg_type)
            seen_id_mapping[xaml_id(segtier)] = wt_id

            wt = RGWordTier(id=wt_id, type=seg_type, igt=inst, attributes={seg_attr: tier_ref})

            if word_type == 'gloss':
                add_word_level_info(wt, INTENT_GLOSS_WORD)

            # Now, add the segmentation parts.
            for segpart in segtier.findall('.//{*}SegPart'):
                ref_expr = '%s[%s:%s]' % (item_ref, segpart.attrib['FromChar'], segpart.attrib['ToChar'])

                # Get the item ID and cache it...
                w_id = wt.askItemId()
                seen_id_mapping[xaml_id(segpart)] = w_id

                w = RGWord(id=w_id,
                           attributes={seg_attr: ref_expr})

                wt.add(w)

            inst.append(wt)


        #=======================================================================
        # Alignment Tiers
        #=======================================================================
        aln_tiers = igt.findall('.//{*}AlignmentTier')

        for aln_tier in aln_tiers:
            align(aln_tier, inst, seen_id_mapping)


        #=======================================================================
        # Finally, for POS tiers.
        #=======================================================================
        pos_tiers = igt.findall('.//{*}PosTagTier')

        for pos_tier in pos_tiers:
            try:
                pos(pos_tier, inst, seen_id_mapping)
            except XigtError as xe:
                XAML_LOG.error(xe)

        #inst.sort()
        xc.append(inst)

    return xc

def get_pos_word(tier, i):
    gp = tier[i]
    if ALIGNMENT in gp.attributes:
        gw = tier.igt.find(id=gp.attributes[ALIGNMENT])
        if gw:
            return gw.value()
        else:
            return None

def process_pos_tags(corp, path):
    """
    Take the newly created corpus and extract the part-of-speech tags from the gloss
    in order to train a classifier.

    :param corp:
    :param path:
    """
    f = open(path, 'w', encoding='utf-8')

    for inst in corp:
        gloss_pos = inst.find(id='gw-pos')
        gloss_tier = inst.find(id='')
        if gloss_pos:


            for i, gp in enumerate(gloss_pos):
                tag = gp.value()
                word = get_pos_word(gloss_pos, i)
                if word:

                    prev_gram = None if i == 0 else get_pos_word(gloss_pos, i-1)
                    next_gram = None if i >= len(gloss_pos)-1 else get_pos_word(gloss_pos, i+1)


                    write_gram(GoldTagPOSToken(word, goldlabel=tag), output=f, type='classifier',
                               next_gram=next_gram, prev_gram=prev_gram)
    f.close()




if __name__ == '__main__':

    tagger = StanfordPOSTagger(tagger_model)
    m = MalletMaxent(classifier)

    lang_docs = []

    # -- 1) Set the output directory for the xigt stuff.
    dir = '/Users/rgeorgi/Documents/code/treebanks/annotated_xigt/'

    for path in glob.glob('/Users/rgeorgi/Documents/code/treebanks/xigt_odin/annotated/*-filtered.xml'):

        lang = os.path.basename(path)[0:3]

        xc = load(path)

        # -- 2) Dump out the XIGT docs.
        # xigtxml.dump(open(os.path.join(dir,'{}.xml'.format(lang)), 'w', encoding='utf-8'), xc)

        # -- 3) Write out the features for each language
        process_pos_tags(xc, os.path.join(dir,'{}-feats.txt'.format(lang)))

        lang_docs.append((xc, lang))


    # Now that we have them all written out, let's go back
    # over and create the classifiers.



    all_feats = os.path.join(dir, 'all.txt')
    try:
        os.unlink(all_feats)
    except Exception: pass

    all_model_path = os.path.join(dir, 'all_feats.classifier')

    os.system("""find {0} -iname "*feats.txt" -exec cat {{}} >> {1} \;  """.format(dir, all_feats))
    all_model = train_txt(all_feats, all_model_path)

    poseval_f = open(os.path.join(dir, 'pos_results.txt'), 'w', encoding='utf-8')

    # Set up the tagger
    st = StanfordPOSTagger(tagger_model)

    for (xc, lang) in lang_docs:
        assert isinstance(xc, RGCorpus)

        gold_sents = []
        ablation_sents = []
        full_sents = []

        missing_lang_file = os.path.join(dir, 'no{}.txt'.format(lang))
        os.unlink(missing_lang_file)
        os.system("""find {1} -iname "*feats.txt" -not -iname "*{0}*" -exec cat {{}} >> {2} \;  """.format(lang, dir, missing_lang_file))

        # -- 4) Finally, train a classifier on all the data that isn't for this language, then
        #       test it out on this language.

        noclass_model_path = os.path.join(dir, 'no{}.classifier'.format(lang))
        noclass_feat_path  = os.path.join(dir, 'no{}.txt'.format(lang))

        # Obtain the classifier trained from all but this language.
        c = train_txt(noclass_feat_path, noclass_model_path)


        # Now, use this to classify the gloss for this language and compare.
        for inst in xc:
            assert isinstance(inst, RGIgt) # Just some type hinting...

            old_inst = inst.copy()

            # a) Projection
            proj_inst = inst.copy()
            strip_pos(proj_inst)

            # b) Ablation
            not_this_lang = inst.copy()
            strip_pos(not_this_lang)

            # c) All languages
            all_langs = inst.copy()
            strip_pos(all_langs)
            # Since we're not specifying where we're pulling the annotation, strip it...


            # If we can't get the sequence from the gold,
            # no point in trying to get it ourselves.

            try:
                lang_seq = old_inst.get_lang_sequence()
            except ProjectionException as pe:
                XAML_LOG.warn(pe)
                continue

            # Try projection
            inst.tag_trans_pos(st)



            # now, let's try to get it with this classifier.
            not_this_lang.classify_gloss_pos(c)
            all_langs.classify_gloss_pos(all_model)

            assert inst is not old_inst

            try:
                not_this_lang.project_gloss_to_lang()
                all_langs.project_gloss_to_lang()
            except GlossLangAlignException as glae:
                XAML_LOG.warn(glae)
                continue


            not_this_lang_seq = not_this_lang.get_lang_sequence()
            all_lang_seq = all_langs.get_lang_sequence()


            gold_sents.append(lang_seq)
            ablation_sents.append(not_this_lang_seq)
            full_sents.append(all_lang_seq)




        # Finally, evaluate the POS tags

        #print([[l.label for l in class_sent] for class_sent in class_sents])
        #sys.exit()


        poseval_f.write("For language {}:\n".format(lang))
        poseval(ablation_sents, gold_sents, csv=True, out_f=poseval_f, matrix=False, details=True)
        poseval(full_sents, gold_sents, csv=True, out_f=poseval_f, matrix=False, details=True)

        continue



        new_xc = xc.copy()
        new_xc.giza_align_t_g()


        new_xc.giza_align_l_t()

        gold_ac = AlignedCorpus()

        heur_ac = AlignedCorpus()
        giza_ac = AlignedCorpus()

        # Set up the POS evaluation corpora...
        gold_pos_sents = []

        b1_sents = []
        s1a_sents = []
        s1c_sents = []
        s2a_sents = []
        s2c_sents = []
        s3_sents = []

        for old_inst, new_inst in zip(xc, new_xc):
            # Strip any enrichment (pos tags, bilingual alignment)
            # from the instance we are going to try the tools on.

            old_inst.sort()
            rgp(old_inst)
            #print(old_inst.get_trans_gloss_alignment())
            #sys.exit()

            # TODO: This assertion error is sloppy, find another way.
            try:
                ba = old_inst.get_trans_gloss_alignment()
            except ProjectionTransGlossException:
                continue
            if ba:
                new_inst.heur_align()

                heur_sent = AlignedSent(new_inst.trans.tokens(), new_inst.gloss.tokens(), new_inst.get_trans_gloss_alignment(INTENT_ALN_HEUR))
                giza_sent = AlignedSent(new_inst.trans.tokens(), new_inst.gloss.tokens(), new_inst.get_trans_gloss_alignment(INTENT_ALN_GIZA))
                gold_sent = AlignedSent(new_inst.trans.tokens(), new_inst.gloss.tokens(), old_inst.get_trans_gloss_alignment())

                heur_ac.append(heur_sent)
                giza_ac.append(giza_sent)
                gold_ac.append(gold_sent)

                # Now, let's try the POS tagging for each one of the different configurations...
                # B1 = Giza, treating l/g as bitext, assuming "NOUN"
                # S1a = Heuristic Alignment, assuming "NOUN"
                # S1c = Heuristic Alignment, Classifying
                #
                # S2a = Giza alignment, assuming "NOUN"
                # S2c = Giza alignment, Classifying
                #
                # S3 = classifying
                #

                #===============================================================
                # S1a
                #===============================================================
                new_inst.tag_trans_pos(tagger)
                new_inst.project_trans_to_gloss(tag_method = INTENT_POS_TAGGER)

                new_inst.project_trans_to_gloss(tag_method = INTENT_POS_TAGGER)

                #new_inst.project_gloss_to_lang(created_by = 'intent-s1a', pos_creator='intent-heuristic', unk_handling='noun')
                #new_inst.project_gloss_to_lang(created_by = 'intent-s1c', pos_creator='intent-heuristic', unk_handling='classify', classifier=classifier, posdict=posdict)

                #new_inst.project_gloss_to_lang(created_by = 'intent-s2a', pos_creator='intent-giza', unk_handling='noun')
                #new_inst.project_gloss_to_lang(created_by = 'intent-s2c', pos_creator='intent-giza', unk_handling='classify', classifier=classifier, posdict=posdict)

                #new_inst.project_trans_to_lang(created_by = 'intent-b1', pos_creator='intent-tagger', aln_creator='intent-giza')

                new_inst.classify_gloss_pos(m, tag_method='intent-classify')
                new_inst.project_gloss_to_lang(tag_method='intent-classify')


                try:
                    gold_sent = old_inst.get_lang_sequence()
                except ProjectionException:
                    # TODO: More useful error report here...
                    sys.stderr.write("Skipping instance...\n")
                    continue

                gold_pos_sents.append(gold_sent)

                b1_sents.append(new_inst.get_lang_sequence('intent-b1'))

                #s1a_sents.append(new_inst.get_lang_sequence('intent-s1a'))
                #s1c_sents.append(new_inst.get_lang_sequence('intent-s1c'))

                #s2a_sents.append(new_inst.get_lang_sequence('intent-s2a'))
                #s2c_sents.append(new_inst.get_lang_sequence('intent-s2c'))

                #s3_sents.append(new_inst.get_lang_sequence('intent-s3'))






        giza_ae = AlignEval(giza_ac, gold_ac)
        heur_ae = AlignEval(heur_ac, gold_ac)

        print(lang)
        print(heur_ae.all())
        print(giza_ae.all())

        #b1_acc = poseval(b1_sents, gold_pos_sents, out_f=open(os.devnull, 'w'))
        #s1a_acc = poseval(s1a_sents, gold_pos_sents, out_f=open(os.devnull, 'w'))
        #s1c_acc = poseval(s1c_sents, gold_pos_sents, out_f=open(os.devnull, 'w'))
        #s2a_acc = poseval(s2a_sents, gold_pos_sents, out_f=open(os.devnull, 'w'))
        #s2c_acc = poseval(s2c_sents, gold_pos_sents, out_f=open(os.devnull, 'w'))
        #s3_acc = poseval(s3_sents, gold_pos_sents, out_f=open(os.devnull, 'w'))


        #accs = [b1_acc, s1a_acc, s1c_acc, s2a_acc, s2c_acc, s3_acc]
        #accs = [i.overall_breakdown() for i in accs]

        #print(''.join(accs))



