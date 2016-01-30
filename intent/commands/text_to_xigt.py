from intent.igt.parsing import raw_txt_to_xc

__author__ = 'rgeorgi'

def text_to_xigtxml(infile):
    f = infile.read()
    xc = raw_txt_to_xc(f)
    return xc