'''
Created on Oct 22, 2013

@author: rgeorgi
'''
import pygame
import time

def notify():
	pygame.mixer.init()
	pygame.mixer.music.load("/Users/rgeorgi/Music/BuhBuhBuhBam.aif")
	pygame.mixer.music.play()
	time.sleep(2)
	pygame.mixer.quit()