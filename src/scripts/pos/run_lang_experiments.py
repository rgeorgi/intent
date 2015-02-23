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
from multiprocessing.pool import Pool
import copy
import sqlite3
from multiprocessing.synchronize import Lock


class TestFile(object):
	'''
	Simple class to hold the different types of files.
	'''
	def __init__(self, path, ftype, name):
		self.path = path
		self.type = ftype
		self.name = name
		if ftype not in ['giza','standard']:
			raise Exception('This type is not recognized.')

def run_tagger(name, train_path, rawfile, pc, delete_path = False):
	# Create a new temporary file to store the model. We won't 
	# need to keep it.
	
	mod_temp = NamedTemporaryFile('r', delete=False)
	tag_temp = NamedTemporaryFile('r', delete=False)
		
	# Now, train and test.
	print('Training "%s"' % os.path.basename(train_path))
	stanford_tagger.train(train_path, mod_temp.name, out_f=open(os.devnull, 'w'))
	print('Testing "%s"' % os.path.basename(train_path))
	stanford_tagger.test(rawfile, mod_temp.name, tag_temp.name, log_f=open(os.devnull, 'w'))
	
	# Finally, evaluate.
	eval_corpus = POSCorpus.read_slashtags(tag_temp.name)
	
	# Get the accuracy.
	acc = pos_eval.poseval(eval_corpus, pc, out_f=open(os.devnull, 'w'))
	
	train_c = POSCorpus.read_slashtags(train_path)
	
	# Delete the training file if we are told to.
	if delete_path:
		os.remove(train_path)
		
	return name, acc, sum([len(i) for i in train_c]), train_path
	
class ResultsFile(object):
	def __init__(self, path = None):
		if path:
			self.db = sqlite3.connect(path)
		else:
			self.db = sqlite3.connect(':memory:')
		
		# Set up the cursor...
		self.c = self.db.cursor()

		# Create the table
		self._create()
			
		self._dict = defaultdict(dict)
		
	def _create(self):
		self.execute('CREATE TABLE IF NOT EXISTS results (name text, length int, acc real, filename text)')
		self.db.commit()
		
	def execute(self, cmd):
		self.c.execute(cmd)
		return self.c.fetchall()
		
	def seen_file(self, filename):
		rows = self.execute("SELECT * FROM results WHERE filename = '%s'" % os.path.basename(filename))
		if rows:
			return True
		else:
			return False
		
	def seen_name(self, name):
		rows = self.execute("SELECT * FROM results WHERE name = '%s'" % name)
		if rows:
			return True
		else:
			return False
		
	def add(self, name, acc, length, filename):
		self.execute("INSERT INTO results VALUES ('%s', %s, %s, '%s');" % (name, length, acc, os.path.basename(filename)))
		self.db.commit()
		
	def lastlen(self, name):
		'''
		Return the largest previous length of a run for the test of this name.
		:param name:
		'''
		results = self.execute("SELECT DISTINCT length FROM results WHERE name = '%s' ORDER BY length DESC" % name)
		if results:
			return results[0][0]
		else:
			return 0
		
		
	def keys(self):
		return [i[0] for i in self.execute("SELECT DISTINCT name FROM results")]
		
	def write(self, fh):

		
		
		fh = open(fh, 'w')
		for key in sorted(self.keys()):
			fh.write('-'*40+'\n')
			fh.write('%s\n' % key)
			
			rows = sorted(self.execute("SELECT DISTINCT length, acc FROM results WHERE name = '%s'" % key))

			for row in rows:
				fh.write('%s,%.2f\n' % row)
		fh.close()
				

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
	print("Creating temporary directory %s" % tempdir)
	
	

	# Place to store the results
	results = os.path.join(outdir, 'results.db')
	results_txt = os.path.join(outdir, 'results.txt')
	
	r = ResultsFile(results)
	l = Lock()
	
	# Callback
	def callback(result):
		l.acquire()
		r = ResultsFile(results)
		r.add(*result)		
		r.write(results_txt)
		r.db.commit()
		l.release()
	
	# Multithreaded pool...
	p = Pool(8)
	
	# Now, let's go through each file in the list and train and test.
	for tf in filelist:
		
		train_path = tf.path
		train_type = tf.type
		train_name = tf.name
		
		# The giza files are already split, but for the standard
		# files, let's vary the size of the corpus.
		if train_type == 'standard':
			full_c = POSCorpus.read_slashtags(train_path)

			# Only run the experiment if we don't have results in the database.
			if not r.seen_name(train_name):
						
				for i in range(50, len(full_c), 25):
					small_c = full_c[0:i]
					small_path = NamedTemporaryFile('r', delete=False)
					POSCorpus(small_c).write(small_path.name, 'slashtags', outdir='')
					
					args = [os.path.basename(train_path), small_path.name, rawfile.name, pc, True]
					
	
					p.apply_async(run_tagger, args=args, callback=callback)
				
		
		else:
			# Again, only run if we haven't done the results.
			if not r.seen_file(train_path):
				args = [train_name, train_path, rawfile.name, pc, False]
				p.apply_async(run_tagger, args, callback=callback)


	# Wait for the pool to finish.
	p.close()
	p.join()

	

	print('Removing "%s" ' % tempdir)
	shutil.rmtree(tempdir)


def create_files(inpath, outdir, goldpath, make_files = True, **kwargs):
	
	classifier = MalletMaxent(c['classifier_model'])

	# Load the corpus...	
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
		files_to_test.append(TestFile(outfile, 'standard', name))
		length = 0 if not os.path.exists(inpath) else lc(inpath)
		
		# Only overwrite if force tag is present
		if make_files and (not os.path.exists(outfile) or kwargs.get('force')):
			pt.produce_tagger(inpath, writefile(outfile), method, xc = copy.deepcopy(xc), **kwargs)
			
	#===========================================================================
	# Giza files
	#===========================================================================
	
	def produce_giza_taggers(name, method, skip=False, resume=True):
		giza_dir = os.path.join(outdir, name)
		os.makedirs(giza_dir, exist_ok = True)
		
		prev_corp_length = None
		cur_corp_length = None
		
		for i in range(50, len(xc)+1, 50):
			
			# Create the filename to be created....
			filename = os.path.join(giza_dir, '%s.txt' % i)
			files_to_test.append(TestFile(filename, 'giza', name))
			
					
			# Just continue on if we're not making files.
			if (not make_files):
				continue
			
			# If the filename already exists and is non-empty, and we're not forcing, use that.
			if os.path.exists(filename) and lc(filename) > 0 and not kwargs.get('force'):
				prev_corp_length = cur_corp_length
				cur_corp_length = lc(filename)

			
			else:
				prev_corp_length = cur_corp_length
				cur_corp_length = pt.produce_tagger(inpath, writefile(os.path.join(giza_dir, '%s.txt' % i)), method, xc = copy.deepcopy(xc), skip=skip, limit=i, resume=resume)
			
			
			# If we haven't increased the size of the output corpus in the last two efforts, abort.
			if (prev_corp_length is not None) and (cur_corp_length is not None) and (cur_corp_length >= prev_corp_length):
				break 
	
	
	# 1) Non-Giza Files -----------------------------------------------------------
	# First, we will create all the files for the non-giza methods.
	if True:
		prod('classification.txt', pt.classification, classifier=classifier)
		prod('proj-keep.txt', pt.heur_proj, skip=False)
		prod('proj-keep-nouns.txt', pt.heur_proj, skip=False, unk_nouns=True)
		prod('proj-skip.txt', pt.heur_proj, skip=True)
	
	# 2) Giza Files ---------------------------------------------------------------
	# Next, let's create directories for the giza instances, since we will have to vary the amount of training instances for each.
	
	if True:
		produce_giza_taggers('proj-keep-giza-resume', pt.giza_proj, skip=False)
		produce_giza_taggers('proj-skip-giza-resume', pt.giza_proj, skip=True)
		
		# The case where the 
		produce_giza_taggers('proj-keep-giza', pt.giza_proj, skip=False, resume=False)
		produce_giza_taggers('proj-skip-giza', pt.giza_proj, skip=True, resume=False)
		
		produce_giza_taggers('direct-keep-giza', pt.giza_direct, skip=False)
		produce_giza_taggers('direct-skip-giza', pt.giza_direct, skip=True)
		

	
	return files_to_test
		
	

if __name__ == '__main__':
	p = ArgumentParser()
	p.add_argument('-i', '--input', required=True, type=existsfile)
	p.add_argument('-d', '--directory', required=True, type=writedir)
	p.add_argument('-g', '--gold', required=True, type=existsfile)
	p.add_argument('-p', '--produce', default=True, help='Whether to produce files or just evaluate.')
	
	args = p.parse_args()
	
	filelist = create_files(args.input, args.directory, args.gold, args.produce)
	train_and_test(filelist, args.gold, args.directory)