import ConfigParser
from optparse import OptionParser

class Flagfile():
	""" Handy way to define flags in flagfile.
	Provide int range check
	"""
	def __init__(self, flagfile = 'flagfile.cfg'):
		self.__flagfile = flagfile
		self.__int_flags = []
		self.__string_flags = []
		self.__str = ''
	def AddInt(self, name, min_v = 0, max_v = 65535,
			section='Crawling'):
		self.__int_flags.append((name, min_v, max_v, section))
	def AddString(self, name, section='Crawling'):
		self.__string_flags.append((name, section))
	def Parse(self):
		config = ConfigParser.ConfigParser()
		config.read(self.__flagfile)
		parser = OptionParser()
		# int flags
		for flag in self.__int_flags:
			assert len(flag) == 4
			name = flag[0]
			min_v = flag[1]
			max_v = flag[2]
			section = flag[3]
			parser.add_option("--%s"%name,
					"--%s"%name,
					type = int,
					dest = name,
					help = "The number of %s, value range %d - %d"%(
						name, min_v, max_v),
					default = config.get(section, name))
		# string flags
		for flag in self.__string_flags:
			assert len(flag) == 2
			name = flag[0]
			section = flag[1]
			parser.add_option("--%s"%name,
					"--%s"%name,
					dest = name,
					help = name,
					default = config.get(section, name)[1:-1])
		# Now parse
		options, args = parser.parse_args()
		# Now check int flag range
		self.__str = ''
		for flag in self.__int_flags:
			assert len(flag) == 4
			name = flag[0]
			min_v = flag[1]
			max_v = flag[2]
			v = getattr(options, name)
			assert v >= min_v, '%d must not be smaller than %d'%(v, min_v)
			assert v <= max_v, '%d must not be larger than %d'%(v, max_v)
			self.__str += '-%s-%d'%(name, v)
		for flag in self.__string_flags:
			assert len(flag) == 2
			name = flag[0]
			v = getattr(options, name)
			self.__str += '-%s-%s'%(name, v)

		return options
	def ToString(self):
		return self.__str

def FlagvalueFromString(s):
	""" Note that, only name=value are copied, min, max, section are not contained.
	"""
	d = {}
	n = ''
	count = 1
	for v in s.split('-'):
		if len(v) == 0:
			continue
		if count % 2 == 1:
			n = v
		else:
			d[n] = v
		count += 1
	return d

if __name__ == '__main__':
	ff = Flagfile('test/flagfile.cfg')
	ff.AddInt('max_shards')
	ff.AddString('ua_content')
	options = ff.Parse()
	print options.max_shards
	s = ff.ToString()
	print s

	print FlagvalueFromString(s)


