'''
Created on Oct 22, 2013

@author: rgeorgi
'''
# import pygame
# import time
# 
import subprocess
import sys
import logging
from threading import Thread
from queue import Empty, Queue
def notify():
	pass
# 	pygame.mixer.init()
# # 	pygame.mixer.music.load("/Users/rgeorgi/Music/BuhBuhBuhBam.aif")
# 	pygame.mixer.music.load("/Users/rgeorgi/Music/maow2.aif")
# 	pygame.mixer.music.play()
# 	time.sleep(2)
# 	pygame.mixer.quit()


def enqueue_output(out, queue):
	for line in iter(out.readline, b''):
		queue.put(line)
	out.close()


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