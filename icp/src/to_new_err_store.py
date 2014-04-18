import os
from os import listdir
from os.path import isfile, isdir, join, basename
from asflagfile import FlagvalueFromString
from asbase import ParseLogfileTimeAndName, ParseLogentryTime
from asstorage import KeyValueFileStorage

mypath = 'sample-output'
err_store = KeyValueFileStorage('sample-output/visited', 1000, 60, True)

def ProcessErrorFile(filename):
	pindex = int(filename.split('/')[1])
	basename = filename.split('/')[2].split('.')[0]
	num = int(basename)
	err_store.Set('%d:%d'%(num, pindex), '')
	os.remove(filename)

total_files = 0
total_errs = 0

subdirs = [join(mypath, f) for f in listdir(mypath) if isdir(join(mypath, f))]
for subdir in subdirs:
	allfiles = [ join(subdir, f) for f in listdir(subdir) if isfile(join(subdir, f)) ]
	for f in allfiles:
		total_files += 1
		if f[-5:] == 'error':
			ProcessErrorFile(f)
			total_errs += 1

# now make sure they are same
count = err_store.length()
print count, total_errs
