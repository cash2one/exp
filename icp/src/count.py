from os import listdir
from os.path import isfile, isdir, join, basename
from asflagfile import FlagvalueFromString
from asbase import ParseLogfileTimeAndName, ParseLogentryTime
from asstorage import KeyValueFileStorage
from ascolorstring import OKString

def IterateAllDatafiles(Process, mypath = 'sample-output'):
	subdirs = [join(mypath, f) for f in listdir(mypath) if isdir(join(mypath, f))]
	for subdir in subdirs:
		allfiles = [ join(subdir, f) for f in listdir(subdir) if isfile(join(subdir, f)) ]
		for f in allfiles:
			if f[-4:] == 'data':
				Process(f)
	
class DataDistributionCollector():
	"""Collect distribution data from log file
	"""
	def __init__(self, mypath = 'sample-output'):
		self.mypath = mypath
	def run(self):
		self.provinces = []
		for l in open('province-list-full.txt'):
			self.provinces.append(l.strip())

		self.pindex_count = {} # pindex => count
		self.pindex_min_max = {} # pindex => [min, max]
		# min max
		IterateAllDatafiles(self.__ProcessDataFile)
		# overall min max
		self.global_min = 99999999
		self.global_max = 0
		for k, v in self.pindex_min_max.iteritems():
			self.global_min = min(self.global_min, v[0])
			self.global_max = max(self.global_max, v[1])


		self.total_pages_with_icp = 0
		for k, v in self.pindex_count.iteritems():
			self.total_pages_with_icp += v
		# percentage per province
		self.percentage = {}
		if self.total_pages_with_icp > 0:
			for k, v in self.pindex_count.iteritems():
				self.percentage[k] = float(v) * 100 / self.total_pages_with_icp
	def __ProcessDataFile(self, filename):
		pindex = int(filename.split('/')[1])
		pos = basename(filename).find('.')
		num = int(basename(filename)[:pos])
		# update count
		if not pindex in self.pindex_count:
			self.pindex_count[pindex] = 0
		self.pindex_count[pindex] += 1
		# update max min
		if not pindex in self.pindex_min_max:
			self.pindex_min_max[pindex] = [99999999, 0]
		self.pindex_min_max[pindex][0] = min(num, self.pindex_min_max[pindex][0])
		self.pindex_min_max[pindex][1] = max(num, self.pindex_min_max[pindex][1])
	
class ThroughputCollector():
	"""Collect throughput data from log file
	"""
	def __init__(self, mypath = 'sample-output'):
		self.mypath = mypath
		pass
	def run(self):
		entry = self.GetLogfilenameAndTime()
		self.logfilename = entry[0]
		self.starttime = entry[1]
		self.finishtime = self.GetFinishTime(self.logfilename)
		eclipsed = self.finishtime - self.starttime
		# time in seconds
		self.eclipsed = eclipsed.total_seconds()

		(error_count, busy_count) = self.TotalErrorBusyCount()
		self.total_error_pages = error_count
		self.total_busy_pages = busy_count
		self.GetTotalDataPages()
		self.total_crawled_pages = self.total_error_pages + self.total_data_pages

		self.qps = self.total_crawled_pages / self.eclipsed
		# K pages/day
		self.throughput = self.qps * 3.6 * 24

	def GetLogfilenameAndTime(self):
		alllogs = [f for f in listdir(self.mypath) if isfile(join(self.mypath, f))]
		max_time = None
		max_name = ''
		for logfile in alllogs:
			logtime, name = ParseLogfileTimeAndName(logfile)
			if name is None:
				continue
			if max_time is None or max_time < logtime:
				max_time = logtime
				max_name = logfile
		return (max_name, max_time)
	def TotalErrorBusyCount(self):
		err_store = KeyValueFileStorage('sample-output/visited', 1000, 60)
		busy_count = 0
		error_count = 0
		for k in err_store.iterkeys():
			if k.split(':')[-1] == 'busy':
				busy_count += 1
			else:
				error_count += 1
		return (error_count, busy_count)
	def GetTotalDataPages(self):
		self.total_data_pages = 0
		IterateAllDatafiles(self.__ProcessDataFile)
	def GetFinishTime(self, logfilename):
		previous = None
		max_entry = None
		for l in open(join(self.mypath, logfilename)):
			previous = max_entry
			max_entry = l
		try:
			return ParseLogentryTime(max_entry)
		except ValueError:
			# Still writing logs, use previous one
			return ParseLogentryTime(previous)
	def __ProcessDataFile(self, filename):
		self.total_data_pages += 1

dbc = DataDistributionCollector()
dbc.run()
tc = ThroughputCollector()
tc.run()

print OKString('\nANALYZE OUTPUT')
print tc.logfilename

print OKString('\nProvince distribution:')
for k, v in dbc.pindex_count.iteritems():
	print dbc.provinces[k], '%.0f%%'%(dbc.percentage[k]), v

print OKString('\nPossible number ranges:')
for k, v in dbc.pindex_min_max.iteritems():
	print dbc.provinces[k], v
print [dbc.global_min, dbc.global_max]

print OKString('\nTHROUGHPUT:')
print 'Crawled %d files in %.2f seconds'%(tc.total_crawled_pages, tc.eclipsed)
print 'found %d icp page, %d empty pages, %d connection reset'%(
		tc.total_data_pages, tc.total_error_pages, tc.total_busy_pages)
#TODO. This is a overcount, because total_error_pages are sahred betwen every runs, but the time are for this run.
# Should read data count, busy count, error count from log file instad of storage.
# Let crawler to keep this in memory, and flush when quit.
print 'qps = %.2f\nthroughput = %.2f K/day'%(tc.qps, tc.throughput)
