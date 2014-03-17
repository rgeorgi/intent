'''
Created on Feb 14, 2014

@author: rgeorgi
'''

import os, sys, re, argparse
from utils import ConfigFile
import glob
from alignment.Alignment import AlignedCorpus
from eval.align_eval import AlignEval

def junk_helper(ls, dir, s):
	return ls.extend(glob.glob(dir + s))


def remove_junk(prefix):
	jl = []	
	junk_helper(jl, prefix, '*d3*')
	junk_helper(jl, prefix, '*d4*')
	junk_helper(jl, prefix, '*perp')
	junk_helper(jl, prefix, '*vcb')
	junk_helper(jl, prefix, '*cooc')
	junk_helper(jl, prefix, '*t3*')
	junk_helper(jl, prefix, '*p0_3*l')
	junk_helper(jl, prefix, '*gizacfg')
	junk_helper(jl, prefix, '*Decoder.config')
	junk_helper(jl, prefix, '*snt')
	junk_helper(jl, prefix, '*aa3.final')
	junk_helper(jl, prefix, '*n3.final')
	
	
	for ji in jl:
		os.remove(ji)
	
						

def run_giza(e_file, f_file, giza_bin, out_prefix, aln_path):
	
	#------------------------------------------------------------------------------ 
	# Start with plain2snt
	plain2snt = os.path.join(giza_bin, 'plain2snt.out')
	os.system(plain2snt + ' ' + e_file + ' ' + f_file)
	
	
	#===========================================================================
	# Define all the files 
	#===========================================================================
	
	e_base = os.path.splitext(os.path.basename(e_file))[0]
	f_base = os.path.splitext(os.path.basename(f_file))[0]
	
	dir = os.path.dirname(e_file)
	
	e_vcb = os.path.join(dir, e_base+'.vcb')
	f_vcb = os.path.join(dir, f_base+'.vcb')
	
	corp = os.path.join(dir, e_base+'_'+f_base+'.snt')
	
	cooc = os.path.join(dir, e_base+'_'+f_base+'.cooc')
	
	#------------------------------------------------------------------------------ 
	
	
	e_cats = os.path.join(dir, e_base+'.cats')
	f_cats = os.path.join(dir, f_base+'.cats')
	
	# Now, let's get the other files.
# 	mkcls = os.path.join(giza_bin, 'mkcls')
# 	cmd_e = mkcls + ' -c12 -n1 -p%s -V%s' % (e_file, e_cats)
# 	cmd_f = mkcls + ' -c12 -n1 -p%s -V%s' % (f_file, f_cats)
# 
# 	os.system(cmd_e)
# 	os.system(cmd_f)
	
	# Now make the coocurrence file
	snt2cooc = os.path.join(giza_bin, 'snt2cooc.out')
	cmd = snt2cooc + ' ' + e_vcb + ' ' + f_vcb + ' ' + corp + ' > ' + cooc
	sys.stderr.write(cmd+'\n')
	os.system(cmd)
	
	# Now run giza
	giza = os.path.join(giza_bin, 'GIZA++')
	cmd = giza + ' -o %s -S %s -T %s -C %s -CoocurrenceFile %s' % (out_prefix, e_vcb, f_vcb, corp, cooc)
	sys.stderr.write(cmd+'\n')
	os.system(cmd)
	
	remove_junk(c['outdir'])
	
	gold_ac = AlignedCorpus()
	gold_ac.read(e_file, f_file, aln_path)
	
	giza_ac = AlignedCorpus()
	giza_ac.read_giza(e_file, f_file, out_prefix+'.A3.final')
	
	ger = AlignEval(giza_ac, gold_ac, debug=False)
	print(ger.all())
	
	
	

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('c', metavar='CONFIG')
	
	args = p.parse_args()
	
	c = ConfigFile.ConfigFile(args.c)
	
	run_giza(c['e_file'], c['f_file'], c['giza_bin'], c['outprefix'], c['aln_file'])
	