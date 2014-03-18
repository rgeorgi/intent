'''
Created on Feb 14, 2014

@author: rgeorgi
'''

import os, sys, re, argparse
from utils import ConfigFile
import glob
from alignment.Alignment import AlignedCorpus, combine_corpora
from eval.AlignEval import AlignEval

def junk_helper(ls, dir, s):
	return ls.extend(glob.glob(dir + s))


def remove_junk(prefix):
	jl = []	
	junk_helper(jl, prefix, '*d3*')
	junk_helper(jl, prefix, '*D_4*')
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
	os.system(plain2snt + ' ' + f_file + ' ' + e_file)
	
	
	#===========================================================================
	# Define all the files 
	#===========================================================================
	
	e_base = os.path.splitext(os.path.basename(e_file))[0]
	f_base = os.path.splitext(os.path.basename(f_file))[0]
	
	dir = os.path.dirname(e_file)
	
	e_vcb = os.path.join(dir, e_base+'.vcb')
	f_vcb = os.path.join(dir, f_base+'.vcb')
	
	g_t_corp = os.path.join(dir, e_base+'_'+f_base+'.snt')
	t_g_corp = os.path.join(dir, f_base+'_'+e_base+'.snt')
	
	g_t_cooc = os.path.join(dir, e_base+'_'+f_base+'.cooc')
	t_g_cooc = os.path.join(dir, f_base+'_'+e_base+'.cooc')
	
	g_t_prefix = out_prefix+'_g_t'
	t_g_prefix = out_prefix+'_t_g'
	
	#------------------------------------------------------------------------------ 
	
	run = False
	
# 	e_cats = os.path.join(dir, e_base+'.cats')
# 	f_cats = os.path.join(dir, f_base+'.cats')
	
	# Now, let's get the other files.
# 	mkcls = os.path.join(giza_bin, 'mkcls')
# 	cmd_e = mkcls + ' -c12 -n1 -p%s -V%s' % (e_file, e_cats)
# 	cmd_f = mkcls + ' -c12 -n1 -p%s -V%s' % (f_file, f_cats)
# 
# 	os.system(cmd_e)
# 	os.system(cmd_f)
	
	if run:
	
		# Now make the coocurrence file
		snt2cooc = os.path.join(giza_bin, 'snt2cooc.out')
		cmd = snt2cooc + ' ' + e_vcb + ' ' + f_vcb + ' ' + g_t_corp + ' > ' + g_t_cooc
		sys.stderr.write(cmd+'\n')
		os.system(cmd)
		
		cmd = snt2cooc + ' ' + f_vcb + ' ' + e_vcb + ' ' + t_g_corp + ' > ' + t_g_cooc
		sys.stderr.write(cmd+'\n')
		os.system(cmd)
		
		# Now run giza	
		giza = os.path.join(giza_bin, 'GIZA++')
		cmd = giza + ' -o %s -S %s -T %s -C %s -CoocurrenceFile %s' % (g_t_prefix, e_vcb, f_vcb, g_t_corp, g_t_cooc)
		sys.stderr.write(cmd+'\n')
		os.system(cmd)
		
		# Run in opposite direction
		cmd = giza + ' -o %s -S %s -T %s -C %s -CoocurrenceFile %s' % (t_g_prefix, f_vcb, e_vcb, t_g_corp, t_g_cooc)
		sys.stderr.write(cmd+'\n')
		os.system(cmd)
	
	remove_junk(c['outdir'])
	
	gold_ac = AlignedCorpus()
	gold_ac.read(e_file, f_file, aln_path)
	
	g_t_giza_ac = AlignedCorpus()
	g_t_giza_ac.read_giza(e_file, f_file, g_t_prefix+'.A3.final')
	
	t_g_giza_ac = AlignedCorpus()
	t_g_giza_ac.read_giza(f_file, e_file, t_g_prefix+'.A3.final')
	
	intersected = combine_corpora(g_t_giza_ac, t_g_giza_ac, method='intersect')
	union = combine_corpora(g_t_giza_ac, t_g_giza_ac, method='union')
	refined = combine_corpora(g_t_giza_ac, t_g_giza_ac, method='refined')
	
	g_t_ae = AlignEval(g_t_giza_ac, gold_ac, debug=False)
	t_g_ae = AlignEval(t_g_giza_ac, gold_ac, debug=False, reverse=True)
	i_ae = AlignEval(intersected, gold_ac, debug=False)
	union_ae = AlignEval(union, gold_ac, debug=False)
	refined_ae = AlignEval(refined, gold_ac, debug=False)
	
	print('System,AER,Precision,Recall,F-Measure,Matches,Gold,Test')
	print(r'Gloss $\rightarrow$ Trans,%s'%g_t_ae.all())
	print(r'Trans $\rightarrow$ Gloss,%s'%t_g_ae.all())
	print(r'Intersection,%s'%i_ae.all())
	print(r'Union,%s'%union_ae.all())
	print(r'Refined,%s'%refined_ae.all())
	
	
	

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('c', metavar='CONFIG')
	
	args = p.parse_args()
	
	c = ConfigFile.ConfigFile(args.c)
	
	run_giza(c['e_file'], c['f_file'], c['giza_bin'], c['outprefix'], c['aln_file'])
	