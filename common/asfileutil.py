import os

def ExistsFile(filename):
	try:
		f = open(filename, 'r')
		f.close()
		return True
	except IOError:
		return False

def CreateDirIfNotExists(filename):
	name = os.path.dirname(filename)
	if not os.path.exists(name):
		os.makedirs(name)

def DoOpenFile(filename):
	if os.path.basename(filename) != filename:
		CreateDirIfNotExists(filename)
	return open(filename, 'w')
