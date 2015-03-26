'''
Created on Oct 22, 2013

@author: rgeorgi
'''
# import pygame
import time
# 
import subprocess
import sys
import logging
from threading import Thread
from queue import Empty, Queue
from _testcapi import the_number_three
from unittest.case import TestCase


def enqueue_output(out, queue):
	for line in iter(out.readline, b''):
		queue.put(line)
	out.close()
	
def thread_handler(out, func):
	for line in iter(out.readline, b''):
		func(line.decode('utf-8').strip())
	
def handle_stderr(p, queue, func):
	while p.poll() == None:
		try:			
			data = queue.get_nowait()
		except Empty:
			pass
		else:
			func(data.decode('utf-8'))
	
class ProcessCommunicator(object):
	'''
	This is a class to make communicating between a commandline program easier.
	It will make available stdin and stdout pipes, while allowing for the stderr
	to be handled by a custom handler.
	'''
	
	def __init__(self, cmd, stdout_func = None, stderr_func=None):
		'''
		Execute a command, ``cmd`` and save the stdin/stdout for communication,
		but allow the stderr to be read in a non-blocking manner and printed using
		stderr_func.
		
		:param cmd: Command to be run
		:type cmd: str
		:param stderr_func: Function to handle the stderr strings.
		:type stderr_func: func
		'''
		
		# 1) Initialize the subprocess ---------------------------------------------
		self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1)
		
		if stderr_func:
			stderr_t = Thread(target=thread_handler, args=(self.p.stderr, stderr_func))
			stderr_t.daemon = True
			stderr_t.start()
			
		if stdout_func:
			stdout_t = Thread(target=thread_handler, args=(self.p.stdout, stdout_func))
			stdout_t.daemon = True
			stdout_t.start()
			
		
	def wait(self):
		return self.p.wait()
		
	def poll(self):
		return self.p.poll()
	
	@property
	def stdout(self):
		return self.p.stdout
	
	@property
	def stderr(self):
		return self.p.stderr
	
	@property
	def stdin(self):
		return self.p.stdin
	

def piperunner(cmd, log_name = None):
	'''
	Fancy way to call a blocking subprocess and log its activity, while 
	
	
	:param cmd:
	:type cmd:
	:param log_name:
	:type log_name:
	'''
	

	if not log_name:
		out_func = sys.stdout.write
	else:
		logger = logging.getLogger(log_name)
		out_func = logger.info

	out_func('-'*35+' COMMAND: ' + '-'*35+'\n')
	out_func(cmd+'\n'+'-'*80+'\n')
	
	p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1)
	q = Queue()
	t = Thread(target=enqueue_output, args=(p.stdout, q))
	t.daemon = True
	t.start()
	
	while p.poll() == None:
		try:
			data = q.get_nowait()
		except Empty:
			pass
		else:
			out_func(data.decode('utf-8'))
		
		
	return p.returncode

#===============================================================================
# Testcases
#===============================================================================

class ProcessCommunicatorTest(TestCase):
	
	def error_test(self):
		self.pc = ProcessCommunicator('echo asdf ', stdout_func = print)
		print(self.pc.wait())