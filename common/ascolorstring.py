class bcolors:
	HEADER = '\033[95m'
	OK_NBLUE = '\033[94m'
	OK_GREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	END = '\033[0m'

	def disable(self):
		self.HEADER = ''
		self.OK_BLUE = ''
		self.OK_GREEN = ''
		self.WARNING = ''
		self.FAIL = ''
		self.END = ''

def OKString(s):
	return '%s%s%s'%(bcolors.OK_GREEN, s, bcolors.END)
