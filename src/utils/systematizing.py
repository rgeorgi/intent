'''
Created on Oct 22, 2013

@author: rgeorgi
'''
# import pygame
# import time
# 
import subprocess
import sys
def notify():
	pass
# 	pygame.mixer.init()
# # 	pygame.mixer.music.load("/Users/rgeorgi/Music/BuhBuhBuhBam.aif")
# 	pygame.mixer.music.load("/Users/rgeorgi/Music/maow2.aif")
# 	pygame.mixer.music.play()
# 	time.sleep(2)
# 	pygame.mixer.quit()

def piperunner(cmd, out_f = sys.stdout):
	out_f.write('-'*35+' COMMAND: ' + '-'*35+'\n')
	out_f.write(cmd+'\n'+'-'*80+'\n')
	
	p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	
	while p.poll() == None:
		data = p.stdout.read(2)
		out_f.write(data.decode('utf-8'))
		
	return p.returncode