'''
Created on Oct 22, 2013

@author: rgeorgi
'''

def process_tree(t, delimeter, maxlength = 0, sent_count = 0, tm = None):
	leaves = t.leaves()
	if maxlength and (len(leaves) > maxlength):
		return None
	else:
		sent_str = ''
		gold_str = ''
		remapped_str = ''
		
		for leaf in leaves:
			if not leaf.pos.strip():
				continue
			
			# Add the token to the sentences
			sent_str += '%s ' % leaf.label
			gold_str += '%s%s%s ' % (leaf.label, delimeter, leaf.pos)
			if tm:
				newtag = tm[leaf.pos]
				remapped_str += '%s%s%s ' % (leaf.label, delimeter, newtag)
			
		sent_count += 1
		return (sent_str.strip(), gold_str.strip(), remapped_str.strip())