import psutil
import threading
import time
from psutil import NoSuchProcess

class Profiler:
	def __init__(self):
		self.__quit = False
		self.__process = {}
		self.__monitor_names = []
	
	def AddMonitor(self, name):
		self.__monitor_names.append(name)

	def Start(self):
		if self.__quit:
			self.__DumpData()
			return
		threading.Timer(0.1, self.Start).start()
	
		for pid in psutil.get_pid_list():
			p = None
			try:
				p = psutil.Process(pid)
			except NoSuchProcess:
				continue
			cpu = p.get_cpu_times()
			user_cpu = cpu[0]
			system_cpu = cpu[1]
			name = p.name
	
			if pid not in self.__process:
				print 'found new process %s (%d)'%(name, pid)
				self.__process[pid] = (name, 0.0, 0.0)
			if not self.__WorthMonitor(name):
				continue
			process = self.__process[pid]
			assert process[0] == name
			assert process[1] <= user_cpu
			assert process[2] <= system_cpu
			self.__process[pid] = (name, user_cpu, system_cpu)

	def Quit(self):
		self.__quit = True

	def __WorthMonitor(self, name):
		for n in self.__monitor_names:
			if n.find(name) >= 0:
				return True
		return False

	def __DumpData(self):
		names = {}
		for (pid, data) in self.__process.iteritems():
			name =data[0]
			user_cpu = data[1]
			system_cpu = data[2]
			if user_cpu > 0 or system_cpu > 0:
				print "%s(%d) %f %f"%(name, pid, user_cpu, system_cpu)
				if name not in names:
					names[name] = [0.0, 0.0]
				n = names[name]
				n[0] += user_cpu
				n[1] += system_cpu
		# Now aggregate by name
		for name, n in names.iteritems():
			print name, n[0], n[1]

if __name__ == '__main__':
	p = Profiler()
	p.AddMonitor('phantomjs')
	p.AddMonitor('python')
	p.Start()
	c = raw_input('Press q anytime if you want to quit\n')
	if c == 'q':
		p.Quit()
