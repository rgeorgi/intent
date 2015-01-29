'''
Created on Jan 27, 2015

@author: rgeorgi
'''

from unittest import TestCase

#===============================================================================
# ArgPasser
#===============================================================================

class ArgPassingException(Exception):
	pass

class ArgPasser(dict):
	'''
	Argpasser is just a drop-in replacement for a \*\*kwarg dict,
	but allows for things that evaluate to false in the dict
	to be returned without being replaced by the default.
	'''
	
	def __init__(self, d):
		super().__init__(d)		
	
	def get(self, k, default=None, t=None):
		'''
		Using the key *k*, attempt to retrieve the value from the
		dictionary. A default replacement is available, and a "type"
		argument which can be applied to verify the argument is of the
		right type.
		
		**k**       -- the key
		
		**default** -- what to return if *k* was not found in the dict
		
		**t**       -- the type function to apply to the retrieved argument.   
		'''

		# Only replace with default if the key is actually
		# not in the mapping, not just evaluates to nothing.
		if k in self:
			val = self[k]
		else:
			val = default 
			
			
		
		# Parse val as the given type
		if t:
			try:
				val = t(val)
			except Exception as e:
				raise ArgPassingException(e)
			
		return val
			

#===============================================================================
#  TEST CASES
#===============================================================================
			
class ArgPasserTests(TestCase):
	
	def setUp(self):
		self.ap = ArgPasser({'a':1,
			 'b':'True',
			 'c':'2',
			 'd':0})
	
	def testBool(self):

		ap = self.ap
		self.assertIsNot(ap.get('b'), True)
		self.assertIs(ap.get('b', t=bool), True)
		self.assertTrue(ap.get('a'))
		self.assertFalse(ap.get('d', t=bool))
		
	def testInt(self):
		ap = self.ap
		self.assertEqual(ap.get('a'), 1)
		self.assertIsNot(ap.get('c'), 2)
		self.assertIs(ap.get('c', t=int), 2)