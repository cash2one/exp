""" For every third party package include and mock.
Only run unittest in TEST_MODE

Note. Make sure TEST_MODE is set to False in production.
Note. Usually, you should use a wrapper in common dir.
"""
import sys
import unittest

# Note. Please turn test mode to be False in production
# or there's serious secure problems.
TEST_MODE = False

if TEST_MODE:
	sys.stderr.write("""WARNING!!! You are using TEST_MODE!!!
Do not launch in production with TEST_MODE!!!\n\n""")

try:
	from Crypto.Cipher import AES
except ImportError:
	sys.stderr.write("""Failed to import Crypto, did you installed?\n""")
	if not TEST_MODE:
		sys.exit(1)
	else:
		class MockAESObj():
			def __init__(self, passwd, mode):
				if not TEST_MODE:
					sys.exit(1)
				self.passwd = passwd
				self.mode = mode
			def encrypt(self, msg):
				return '%s\n%s'%(msg, self.passwd)
			def decrypt(self, msg):
				pos = msg.rfind('\n')
				if msg[pos+1:] != self.passwd:
					return 'INVALID'
				return msg[:pos]

		class AES():
			MODE_ECB = 'ecb'
			@staticmethod
			def new(passwd, mode):
				return MockAESObj(passwd, mode)

class CheckAES(unittest.TestCase):
	def testAESEncrypt(self):
		aes = AES.new('rootpass', 'anymode')
		text = 'anything you want to encrypt'
		ciphered = aes.encrypt(text)
		self.assertEqual(text, aes.decrypt(ciphered))
		# now the INVALID passwd
		aes2 = AES.new('rootpass2', 'anymode')
		self.assertNotEqual(text, aes2.decrypt(ciphered))

if __name__ == '__main__':
	if TEST_MODE:
		print '\nSTART UNITTEST\n'
		unittest.main()
