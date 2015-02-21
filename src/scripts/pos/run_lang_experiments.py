'''
Created on Feb 21, 2015

@author: rgeorgi

Script to generate all the parse documents for a given language. 
'''
from argparse import ArgumentParser
from utils.argutils import existsfile, writedir, writefile
from utils.setup_env import c
from interfaces.mallet_maxent import MalletMaxent
import scripts.igt.produce_tagger as pt
import os
from igt.rgxigt import RGCorpus
from interfaces import stanford_tagger
from tempfile import NamedTemporaryFile, mkdtemp
from corpora.POSCorpus import POSCorpus
from eval import pos_eval
from utils.fileutils import lc
import shutil
import sys
from collections import defaultdict


class TestFile(object):
	'''
	Simple class to hold the different types of files.
	'''
	def __init__(self, path, ftype):
		self.path = path
		self.type = ftype
		if ftype not in ['giza','standard']:
			raise Exception('This type is not recognized.')

def run_tagger(name, train_path, logfile, rawfile, pc):
	# Create a new temporary file to store the model. We won't 
	# need to keep it.
	
	mod_temp = NamedTemporaryFile('r', delete=False)
	tag_temp = NamedTemporaryFile('r', delete=False)
		
	# Now, train and test.
	print('Training "%s"' % os.path.basename(train_path))
	stanford_tagger.train(train_path, mod_temp.name, out_f=logfile)
	print('Testing "%s"' % os.path.basename(train_path))
	stanford_tagger.test(rawfile.name, mod_temp.name, tag_temp.name, log_f=logfile)
	
	# Finally, evaluate.
	eval_corpus = POSCorpus.read_slashtags(tag_temp.name)
	
	# Get the accuracy.
	acc = pos_eval.poseval(eval_corpus, pc, out_f=logfile)
	train_l = lc(train_path)
	return name, acc, train_l
	

def train_and_test(filelist, goldpath, outdir):
	'''
	Function 
	
	:param filelist: List of slashtags files to train with
	:param goldpath: Gold file to evaluate against
	:type goldpath: filepath
	'''
	
	# Read in the slashtags file and produce a raw file for the tagger.
	rawfile = NamedTemporaryFile('w', encoding='utf-8', delete=False)
	pc = POSCorpus.read_slashtags(goldpath)
	rawfile.write(pc.raw())
	rawfile.close()
	
	logfile = open(os.path.join(outdir, 'taglog.txt'), 'w', encoding='utf-8')

	
	tempdir = mkdtemp()
	
	model = os.path.join(tempdir, 'model')
	tagged = os.path.join(tempdir, 'tagged')
	
	# Place to store the results
	results = defaultdict(dict)
	
	# Callback
	def callback(result):
		name, acc, length = result
		results[name][length] = acc
	
	# Now, let's go through each file in the list and train and test.
	for tf in filelist:
		
		train_path = tf.path
		train_type = tf.type
		
		# The giza files are already split, but for the standard
		# files, let's vary the size of the corpus.
		if train_type == 'standard':
			full_c = POSCorpus.read_slashtags(train_path)
			
			for i in range(50, len(full_c), 50):
				small_c = full_c[0:i]
				small_path = NamedTemporaryFile('r', delete=True)
				POSCorpus(small_c).write(small_path.name, 'slashtags', outdir='')
				
				result = run_tagger(os.path.basename(train_path), small_path.name, logfile, rawfile, pc)
				small_path.close()
				callback(result)
				print(results)
				
		else:
			result = run_tagger(os.path.basename(train_path), train_path, logfile, rawfile, pc)
			callback(result)
			
		print(results)

	print('Removing "%s" ' % tempdir)
	shutil.rmtree(tempdir)


def create_files(inpath, outdir, goldpath, make_files = True, **kwargs):
	
	classifier = MalletMaxent(c['classifier_model'])

	# Load the corpus...	
	xc = RGCorpus()
	if make_files:
		print('loading XIGT corpus...', end=' ')
		xc = RGCorpus.load(inpath)
		print('loaded')
	
	# Gather the files that we will be training and testing
	# a tagger on.
	files_to_test = []

	
	#===========================================================================
	# Non-giza files
	#===========================================================================
	
	def prod(name, method, **kwargs):
		'''
		Convenience method to generate standard files.
		'''
		
		outfile = os.path.join(outdir, name)
		files_to_test.append(TestFile(outfile, 'standard'))
		length = 0 if not os.path.exists(inpath) else lc(inpath)
		
		# Only overwrite if force tag is present
		if make_files and length < len(xc) and (not os.path.exists(outfile) or kwargs.get('force')):
			pt.produce_tagger(inpath, writefile(outfile), method, xc = xc.copy(), **kwargs)
			
	#===========================================================================
	# Giza files
	#===========================================================================
	def produce_giza_taggers(name, method, skip=False):
		giza_dir = os.path.join(outdir, name)
		os.makedirs(giza_dir, exist_ok = True)
		
		for i in range(50, len(xc)+1, 100):
			# check if this iteration has already been written:
			filename = os.path.join(giza_dir, '%s.txt' % i)
			files_to_test.append(TestFile(filename, 'giza'))
			
			length = 0 if not os.path.exists(filename) else lc(filename)
			
			
			# And skip it if it has, and we're not forcing overwrites.
			if (not make_files) or (os.path.exists(filename) and not kwargs.get('force')) or length + i > len(xc):
				continue
			
			# Deep copy the subset of igts... this will save on performance by a lot.
			#small_xc = RGCorpus(igts=(xc.igts[:i]))
			
			sk = pt.produce_tagger(inpath, writefile(os.path.join(giza_dir, '%s.txt' % i)), pt.giza_proj, xc = xc.copy(), skip=skip, limit=i)
			
			# Between how many we want and how many were skipped, if
			# it reaches the size of the corpus, just stop now, otherwise
			# we will just keep skipping more.
			#if length + i > len(xc):
			#	break
	
	
	# 1) Non-Giza Files -----------------------------------------------------------
	# First, we will create all the files for the non-giza methods.
	if True:
		prod('classification.txt', pt.classification, classifier=classifier)
		prod('proj-keep.txt', pt.heur_proj)
		prod('proj-skip.txt', pt.heur_proj)
	
	# 2) Giza Files ---------------------------------------------------------------
	# Next, let's create directories for the giza instances, since we will have to vary the amount of training instances for each.
	
	if True:
		produce_giza_taggers('proj-keep-giza', pt.giza_proj, skip=False)
		produce_giza_taggers('proj-skip-giza', pt.giza_proj, skip=True)
		produce_giza_taggers('direct-keep-giza', pt.giza_direct, skip=False)
		produce_giza_taggers('direct-skip-giza', pt.giza_direct, skip=True)
		

	
	return files_to_test
		
	

if __name__ == '__main__':
	p = ArgumentParser()
	p.add_argument('-i', '--input', required=True, type=existsfile)
	p.add_argument('-d', '--directory', required=True, type=writedir)
	p.add_argument('-g', '--gold', required=True, type=existsfile)
	p.add_argument('-p', '--produce', default=False, help='Whether to produce files or just evaluate.')
	
	args = p.parse_args()
	
	filelist = create_files(args.input, args.directory, args.gold, args.produce)
	train_and_test(filelist, args.gold, args.directory)