'''
Created on Feb 14, 2014

@author: rgeorgi
'''

import os, sys, re, argparse
from utils import ConfigFile
import glob
from alignment.Alignment import AlignedCorpus, combine_corpora, AlignedSent
from eval.AlignEval import AlignEval
from utils.setup_env import c
from utils.fileutils import swapext, matching_files, remove_safe
from utils.systematizing import piperunner
from tempfile import mkdtemp
import shutil
from collections import defaultdict
import time

class GizaAlignmentException(Exception):
	pass

class CooccurrenceFile(defaultdict):
	def __init__(self):
		defaultdict.__init__(self, set)
		
	def dump(self, path = None):
		
		if not path:
			f = sys.stdout
		else:
			f = open(path, 'w', encoding='utf-8')
			
		for key in sorted(self.keys()):
			for entry in sorted(self[key]):
				f.write('%d %d\n' % (key, entry))
		
		f.flush()
		
class A3files(object):
	def __init__(self, prefix):
		self.files = glob.glob(prefix+'.A3.final.part*')
		self.prefix = prefix
		
	def merge(self, merged_path):
		
		sentdict = {}
		
		for filename in self.files:
			f = open(filename, 'r', encoding='utf-8')
			lines = f.readlines()
			f.close()
			
			while lines:			
				line1 = lines.pop(0)
				line2 = lines.pop(0)
				line3 = lines.pop(0)
				
				num = int(re.search('pair \(([0-9]+)\)', line1).group(1))
				sentdict[num] = (line1,line2,line3)
				
		# Create and write out the merged file
		merged_f = open(merged_path, 'w', encoding='utf-8')
		for key in sorted(sentdict.keys()):
			for line in sentdict[key]:
				merged_f.write(line)
				
		merged_f.close()
			
			
				

class GizaFiles(object):
	'''
	Giza produces so many files, it's easy just to initialize an object to represent
	all the files that will be produced, based on the input F, E text files, and the prefix
	provided for output.
	'''
	
	def __init__(self, prefix, e, f):
		self.e = e
		self.f = f
		self.prefix = prefix

	@property
	def cfg(self):
		return self.prefix+'.gizacfg'
	
	@property
	def e_vcb(self):
		return swapext(self.e, '.vcb')
	
	@property
	def f_vcb(self):
		return swapext(self.f, '.vcb')
	
	@property
	def ef(self):
		return os.path.splitext(self.e)[0]+'_'+os.path.basename(os.path.splitext(self.f)[0])
	
	@property
	def fe(self):
		return os.path.splitext(self.f)[0]+'_'+os.path.basename(os.path.splitext(self.e)[0])
	
	@property
	def ef_snt(self):
		return self.ef+'.snt'
	
	@property
	def fe_snt(self):
		return self.fe+'.snt'
			
	@property
	def ef_cooc(self):
		return self.ef+'.cooc'
	
	@property
	def fe_cooc(self):
		return self.fe+'.cooc'
	
	@property
	def a3(self):
		return glob.glob(self.prefix+'.A3.final.part*')
	
	@property
	def a3merged(self):
		return self.prefix+'.A3.final.merged'
	
	@property
	def t(self):
		return self.prefix+'.t3.final'
	
	@property
	def a(self):
		return self.prefix+'.a3.final'
	
	@property
	def n(self):
		return self.prefix+'.n3.final'
	
	@property
	def d3(self):
		return self.prefix+'.d3.final'
	
	@property
	def d4(self):
		return self.prefix+'.d4.final'
	
	@property
	def perp(self):
		return self.prefix+'.perp'
	
	@property
	def p0(self):
		return self.prefix+'.p0_3.final'
	
	@property
	def decoder(self):
		return self.prefix+'.Decoder.config'
	
	def _clean(self, ls):
		for f in ls:
			try:
				os.remove(f)
			except:
				pass
	
	def merge_a3(self):
		a3 = A3files(self.prefix)
		a3.merge(self.a3merged)
		
	def clean(self):
		
		self.merge_a3()
		
		filelist = [self.ef_cooc, self.fe_cooc,
					self.t, self.d3, self.d4, self.n, self.a,
					self.e_vcb, self.f_vcb,
					self.ef_snt, self.fe_snt,
					self.cfg, self.perp, self.p0, self.decoder]
		
		
		filelist.extend(self.a3)
		filelist.extend(glob.glob(self.prefix+'.trn*'))
		filelist.extend(glob.glob(self.prefix+'.tst*'))
		
				
		self._clean(filelist)
		

		
		#sys.exit()
		
		
	
	def txt_to_snt(self, ev = None, fv = None):
		'''
		This function will generate .snt files in the appropriate place based
		on the vocabularies and text files provided.
		'''
		
		# --- 1) If we are provided with Vocab objects,
		#        use those. Otherwise, attempt to load the files.
		#        finally, attempt to create new ones.
		if not ev:
			if os.path.exists(self.e_vcb):
				ev = Vocab.load(self.e_vcb)
			else:
				ev = Vocab()
			
			
		if not fv:
			if os.path.exists(self.f_vcb):
				fv = Vocab.load(self.f_vcb)
			else:
				fv = Vocab()
		
		# --- 2) Load the text files.
		ef = open(self.e, encoding='utf-8')
		ff = open(self.f, encoding='utf-8')
		
		ef_lines = ef.readlines()
		ff_lines = ff.readlines()
		
		# --- 3) Verify the files are the same length
		if len(ef_lines) != len(ff_lines):
			raise GizaAlignmentException('Files are of unequal length. %d vs. %d' % (len(ef_lines), len(ff_lines)))
		
		# --- 4) Attempt to open up the snt file locations for writing...
		ef_file = open(self.ef_snt, 'w', encoding='utf-8')
		fe_file = open(self.fe_snt, 'w', encoding='utf-8')
		
		# --- 5) While we are at it, let's make the cooc files.
		ef_cooc = CooccurrenceFile()
		fe_cooc = CooccurrenceFile()
		
		# --- 4) Otherwise, proceed converting text files with the vocab...
		for e_line, f_line in zip(ef_lines, ff_lines):
			
			# Skip if one of the lines is empty...
			if (not e_line.strip()) or (not f_line.strip()):
				continue
			
			e_snt_ids = ev.string_to_ids(e_line, add=True)
			f_snt_ids = fv.string_to_ids(f_line, add=True)
			
			e_snt = ev.string_to_snt(e_line)
			f_snt = fv.string_to_snt(f_line)
				
			# The cooc file contains every id
			# for '0', and then, for every e_id, 
			# the f_ids that it is seen co-ocurring with.
			# 
			# So, let's build that database.
			for e_id in e_snt_ids:
				fe_cooc[0].add(e_id)

				for f_id in f_snt_ids:
					ef_cooc[e_id].add(f_id)
				
			
			for f_id in f_snt_ids:
				ef_cooc[0].add(f_id)
				
				for e_id in e_snt_ids:
					fe_cooc[f_id].add(e_id)
							
							
			# Write the special "1" token to each file
			ef_file.write('1\n')
			ef_file.write('%s\n%s\n' % (e_snt, f_snt))			
			
			fe_file.write('1\n')
			fe_file.write('%s\n%s\n' % (f_snt, e_snt))
			
			ef_file.flush(), fe_file.flush()
			
		# --- 5) Dump our (posisbly) updated vocab files
		ev.dump(self.e_vcb)
		fv.dump(self.f_vcb)
		
		# --- 6) Also dump our coocurrence files...
		ef_cooc.dump(self.ef_cooc)
		fe_cooc.dump(self.fe_cooc)
			
			
			
			
	
	# Read the aligned file here...
	def aligned_sents(self):
		a_f = open(self.a3merged, 'r', encoding='utf-8')
		lines = a_f.readlines()
		a_f.close()
		
		a_sents = []
		
		while lines:
			top = lines.pop(0)
			tgt = lines.pop(0)
			aln = lines.pop(0)
			
			idx = int(re.search('\(([0-9]+)\)', top).group(1))
			
			a_sents.append(AlignedSent.from_giza_lines(tgt, aln))
			

		return a_sents
				

class VocabWord(object):
	def __init__(self, word, id):
		self.id = id
		self.content = word
		
	def __hash__(self):
		return hash(self.content)
	
	def __eq__(self, o):
		return str(self) == str(o)
	
	def __str__(self):
		return self.content
	
	def __repr__(self):
		return '%s[%s]' % (self.content, self.id)
				
class VocabNotFoundException(Exception):
	pass
				
class Vocab(object):
	'''
	Internal representation for a .vcb file, so that they can be quickly rewritten.
	
	Note that "1" is the symbol reserved for end-of-sentence, so the indices should start with "2"
	'''
	
	def __init__(self):
		self._counts = {}
		self._words = {}
		self._i = 1
				
	def __len__(self):
		return self._i
	
	def add(self, word, count=1):
		'''
		Add a word to the vocab and assign it a new id.
		'''
		if word in self._counts:			
			self._counts[word] += count
			return self._words[word].id
		else:
			self._i += 1
			vw = VocabWord(word, self._i)
			self._counts[vw] = count
			self._words[vw] = vw
			return self._i

	def add_from_txt(self, path):
		f = open(path, 'r', encoding='utf-8')
		lines = f.readlines()
		f.close()
		for line in lines:
			for word in line.split():
				self.add(word)
		
	def get_id(self, w, add=False):
		'''
		Get the ID for a word. If "add" is False, raise an exception if the word
		is not found in the vocab. Otherwise, add it and return the new ID.
		'''
		if self._words.get(w):
			if add:
				return self.add(w)
			else:
				return self._words.get(w).id
		elif not add:
			raise VocabNotFoundException
		else:
			return self.add(w)
		
	def string_to_ids(self, string, add=False):
		'''
		Given a string, convert it to the ids representation expected by GIZA, using the words
		in this vocab. If an unknown word is discovered, raise an Exception.
		'''
		
		words = string.split()
		
		ids = [self.get_id(w, add) for w in words]
		return ids
		
	def string_to_snt(self, string, add=False):
		'''
		Do what string_to_ids does, but return a string.
		'''
		return ' '.join([str(i) for i in self.string_to_ids(string, add)])
	

		
		
	@classmethod
	def load(cls, path):
		'''
		Create a vocab object from a path.
		'''
		v = cls()
		f = open(path, 'r', encoding='utf-8')
		lines = f.readlines()
		f.close()
		
		# Each line looks like this:
		#
		# ID  WORD COUNT
		# 163 top 650
				
		for line in lines:
			id, word, count =  line.split()
			v.add(word, int(count))
		
		return v
		
	
	def items(self):
		return sorted(self._counts.items(), key=lambda i: i[0].id)
			
	def dump(self, path=None):
		if not path:
			fh = sys.stdout
		else:
			fh = open(path, 'w', encoding='utf-8')
			
		for vw, count in self.items():
			fh.write('%s %s %s\n' % (vw.id, vw.content, count))
		fh.flush()
		

class GizaAligner(object):
	
	def __init__(self):
		pass

	
	def force_align(self, e_snts, f_snts):
		tempdir = mkdtemp()
		
		g_path = os.path.join(tempdir, 'g.txt')
		t_path = os.path.join(tempdir, 't.txt')
		
		g_f = open(g_path, 'w', encoding='utf-8')
		t_f = open(t_path, 'w', encoding='utf-8')
		
		for snt in e_snts:
			g_f.write(snt+'\n')
		for snt in f_snts:
			t_f.write(snt+'\n')
			
		g_f.close(), t_f.close()
		
		prefix = os.path.join(tempdir, 'temp')		
		
		aln = self.resume(prefix, g_path, t_path)
		shutil.rmtree(tempdir)
		return aln
		
		
		
		

	def resume(self, prefix, new_e, new_f):
		'''
		"Force" align a new set of data using the old
		model, per the instructions at:
		
		http://www.kyloo.net/software/doku.php/mgiza:forcealignment
		
		'''
		# First, initialize a new GizaFile container for
		# the files we are going to create
		new_gf = GizaFiles(prefix, new_e, new_f)
		
		# Now, we're going to extend the old vocabulary files
		# with the new text to align.
		old_ev = Vocab.load(self.tf.e_vcb)
		old_fv = Vocab.load(self.tf.f_vcb)
		
		old_ev.add_from_txt(new_gf.e)
		old_fv.add_from_txt(new_gf.f)
		
		# Now that we've extended the vocabs, let's dump the 
		# now-extended vocabs into the new filepaths.
		old_ev.dump(new_gf.e_vcb)
		old_fv.dump(new_gf.f_vcb)
		
		# Write out
		new_gf.txt_to_snt(ev = old_ev, fv = old_fv)
		#new_gf.txt_to_snt()
				

		exe = c['mgiza']
		
		args = [exe, #self.tf.cfg,
				'-restart', '2',
				'-o', new_gf.prefix,
				'-m2', '5',
				'-previoust', self.tf.t,
				'-previousa', self.tf.a,
				'-previousn', self.tf.n,
				'-previousd', self.tf.d3,
				'-c', new_gf.ef_snt,
				'-s', new_gf.e_vcb,
				'-t', new_gf.f_vcb,
				'-Coocurrencefile', new_gf.ef_cooc]
		
		cmd = ' '.join(args)
		#print(cmd)
		#sys.exit()
		
		#piperunner(cmd)
		os.system(cmd)
		
		new_gf.clean()
		
		return new_gf.aligned_sents()
		
		
	
	@classmethod
	def load(cls, prefix, e, f):
		ga = cls()
		ga.tf = GizaFiles(prefix, e, f)
		return ga
		
	
	def train(self, prefix, e, f):
		self.tf = GizaFiles(prefix, e, f)
		tf = self.tf
				
		#self.plain2snt(tf)
		#self.snt2cooc(tf)
		#sys.exit()

		self.tf.txt_to_snt(ev = Vocab(), fv = Vocab())
		#sys.exit()
		
		# Now, finally do the aligning...
		exe = c['mgiza']
				
		
		elts = [exe,
				'-o', tf.prefix,
				'-S', tf.e_vcb,
				'-T', tf.f_vcb,
				'-C', tf.ef_snt,
				'-CoocurrenceFile', tf.ef_cooc,
				'-hmmiterations', '5',
				'-model4iterations', '0']
		cmd = ' '.join(elts)
		os.system(cmd)
		
		# Finally, 
		
		
	def plain2snt(self, gf):
		exe = c['plain2snt']				
		os.system('%s "%s" "%s" -vcb1 "%s" -vcb2 "%s" -snt1 "%s" -snt2 "%s"' % (exe, gf.e, gf.f, gf.e_vcb, gf.f_vcb, gf.ef_snt, gf.fe_snt))
		
	def snt2cooc(self, gf):
		
		exe = c['snt2cooc']
		
		cmd1 = '%s "%s" "%s" "%s" "%s"' % (exe, gf.ef_cooc, gf.e_vcb, gf.f_vcb, gf.ef_snt)	
		cmd2 = '%s "%s" "%s" "%s" "%s"' % (exe, gf.fe_cooc, gf.f_vcb, gf.e_vcb, gf.fe_snt)	
		os.system(cmd1)
		os.system(cmd2)
			
	

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
	junk_helper(jl, prefix, '*a3.final*')
	junk_helper(jl, prefix, '*A3.final*')
	junk_helper(jl, prefix, '*n3.final')
	
	
	for ji in jl:		
		remove_safe(ji)
	
						

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
	