from intent.igt.rgxigt import RGCorpus

__author__ = 'rgeorgi'

def text_to_xigtxml(infile):
    f = infile.read()
    xc = RGCorpus.from_raw_txt(f)
    return xc