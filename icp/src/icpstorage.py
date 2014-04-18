class ICPStorage():
	def __init__(self, directory, num, pindex):
		""" pindex stand for province index
		"""
		self.__directory = directory
		self.__num = num
		self.__pindex = pindex
	def HasData(self, search_all_index = False):
		""" Assumption, ICP are unique among all province. If one province have data, no need to search in another province.
		"""
		if not search_all_index:
			return ExistsFile(self.__datafilename(self.__pindex))
		for pindex in range(0, len(GV.provinces)):
			if ExistsFile(self.__datafilename(pindex)):
				return True
		return False
	def StoreData(self, data):
		outfile = DoOpenFile(self.__datafilename(self.__pindex))
		outfile.write(data)
		outfile.close()
	def HasError(self):
		return GV.err_store.Has(self.__errkey())
	def StoreError(self, data):
		GV.err_store.Set(self.__errkey(), data)
	def StoreBusy(self, data):
		GV.err_store.Set(self.__busykey(), data)
	def __errkey(self):
		return [self.__num, self.__key]
	def __busykey(self):
		return [self.__num, self.__key, 'busy']
	def __datafilename(self, pindex):
		return self.__suffixfilename(pindex, 'data')
	def __suffixfilename(self, pindex, suffix):
		return os.path.join(self.__directory, '%d'%pindex, '%d.%s'%(self.__num, suffix))

if __name__ == '__main__':
	RUN_TEST = False
	if RUN_TEST:
		unittest.main()
	else:
		main()
