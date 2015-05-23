from intent.utils.dicts import CountDict, TwoLevelCountDict

__author__ = 'rgeorgi'

path = '/Users/rgeorgi/Documents/code/dissertation/definitions.txt'

f = open(path, 'r', encoding='utf-8')

d = TwoLevelCountDict()

for line in f:
    lang_w, gloss_w, orig_tag, new_tag = line.split()

    d.add(new_tag, gloss_w)

top_prt = d.top_n('PRT', n=100, min_num=2)
print(top_prt)
for prt, n in top_prt:
    print(prt, n)