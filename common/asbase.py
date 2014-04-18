import signal
from datetime import datetime
import os
import threading
from asfileutil import DoOpenFile

def asoutput(s):
	if isinstance(s, unicode):
		return s.encode('utf-8')
	else:
		return s

LOGTIME_FORMAT_PAT = '%Y%m%d-%H%M%S-%f'

def Logtime2String(t):
	return t.strftime(LOGTIME_FORMAT_PAT)
def String2Logtime(s):
	return datetime.strptime(s, LOGTIME_FORMAT_PAT)

def ParseLogfileTimeAndName(filename):
	bname = os.path.basename(filename)
	entries = bname.split('.')
	if len(entries) < 3 or entries[-1] != 'log':
		return None, None
	t = String2Logtime(entries[0])
	return t, '.'.join(entries[1: -1])
def ParseLogentryTime(entry):
	return String2Logtime(entry.split()[0])

class Logger():
	def __init__(self, filename, dirname = ''):
		basename = '%s.%s.log'%(Logtime2String(datetime.now()), filename)
		if dirname != '':
			self.__filename = os.path.join(dirname, basename)
		else:
			self.__filename = basename
		self.__logfile = DoOpenFile(self.__filename)
		self.__loglock = threading.RLock()
	def __del__(self):
		self.__logfile.close()

	def logfilename(self):
		return self.__filename

	def Log(self, log, thread_name = ''):
		self.__loglock.acquire()
		self.__logfile.write('%s %s %s\n'%(
			Logtime2String(datetime.now()), thread_name, log))
		self.__loglock.release()

def LibOnCtrlC(signal, frame):
	print 'quit on Ctrl+C'
def WaitForCtrlC(func = LibOnCtrlC):
	signal.signal(signal.SIGINT, func)
	signal.pause()

def Main():
	logger = Logger('filename')
	filename = logger.logfilename()
	print ParseLogfileTimeAndName(filename)

	logger.Log('any log')
	logger.Log('another log')
	del logger

	for l in open(filename):
		print ParseLogentryTime(l)

if __name__ == '__main__':
	Main()
