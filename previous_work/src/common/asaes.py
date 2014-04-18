from asthirdparty import AES
import unittest

class AsAESError(Exception):
	def __init__(self, err):
		self.err = err
	def __str__(self):
		return self.err

class AsAES():
	""" padding support by native.
	"""
	def __init__(self, passwd):
		self.__aes = AES.new(AsAES.padding(passwd, 32), AES.MODE_ECB)

	def encrypt(self, msg):
		return self.__aes.encrypt(AsAES.padding(msg, 16))

	def decrypt(self, msg):
		""" Return INVALID if can not decrypt
		"""
		msg_with_padding = self.__aes.decrypt(msg)
		try:
			return AsAES.unpadding(msg_with_padding)
		except AsAESError as e:
			print 'error:%s for "%s"\n'%(e, msg)
			return 'INVALID'

	@staticmethod
	def padding(message, length):
		output = message + '1'
		paddings = []
		num_of_padding = (length - len(output)%length)%length
		for i in range(num_of_padding):
			paddings.append('0')
		return '%s%s'%(output, ''.join(paddings))
	@staticmethod
	def unpadding(message):
		pos = message.rfind('1')
		if pos == -1:
			raise AsAESError('no \\n found')
		padding = message[pos + 1:]
		for i in range(len(padding)):
			if padding[i] != '0':
				raise AsAESError('filling %s error'%padding)
		return message[:pos]

class CheckAES(unittest.TestCase):
	def testAsAES(self):
		aes = AsAES('rootpass')
		aes2 = AsAES('rootpass2')
		for i in range(1, 18):
			text = CheckAES.getText(i)
			ciphered = aes.encrypt(text)
		 	self.assertEqual(text, aes.decrypt(ciphered))
			self.assertNotEqual(text, aes2.decrypt(ciphered))
	def testPadding(self):
		for length in range(2, 34):
			msg = AsAES.padding('abcde', length)
			self.assertEqual(0, len(msg)%length)
			self.assertEqual('abcde', AsAES.unpadding(msg))

	@staticmethod
	def getText(length):
		text = []
		for i in range(length):
			text.append(str(i%9))
		return ''.join(text)


if __name__ == '__main__':
	unittest.main()

