'''
Created on Oct 22, 2013

@author: rgeorgi
'''
import time
import pyaudio
import wave
import aifc

def notify():
	chunk = 1024
	f = aifc.open("/Users/rgeorgi/Music/maow2.aif", 'rb')
	p = pyaudio.PyAudio()
	stream = p.open(format = p.get_format_from_width(f.getsampwidth()),
								channels = f.getnchannels(),
								rate = f.getframerate(),
								output = True)
	
	data = f.readframes(chunk)
	while data != '':
		stream.write(data)
		data = f.readframes(chunk)
		
	stream.stop_stream()
	stream.close()
	
	p.terminate()
		