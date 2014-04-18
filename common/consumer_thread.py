import threading
import time
import Queue

class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""
    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop = threading.Event()

    def Stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

class ConsumerThread(StoppableThread):
	""" consumer threads to work on a queue.
	"""
	def __init__(self, name, queue, func, trace = False):
		super(ConsumerThread, self).__init__()
		self.__name = name
		self.__q = queue
		self.__func = func
		self.__trace = trace

	def run(self):
		""" Called by threading
		"""
		self._Trace('Starting')
		while not self.stopped():
			data = 0
			try:
				data = self.__q.get(True, 0.1)
			except Queue.Empty:
				continue
			self._Trace('Processing ' + str(data))
			self.__func(self.__name, data, self.stopped)
			self.__q.task_done()
		self._Trace('Exiting')

	def _Trace(self, msg):
		if self.__trace:
			print('%s [ %s ]\n'%(self.__name, msg)),

class Consumers:
	""" For anyone want to leverage producer-consumer model.
	Thread safe
			Usage for Producer:
				assert c.Feed(data)
			Usage for Consumer:
				c = Consumers(ProcessingFunc)
				c.Start()
				...
				c.Stop()
	"""
	def __init__(self, f, num_threads = 10, queue_length = 1000):
		""" q is a queue.
				f is the function to process data, could be a function inside a class.
		"""
		self._stopped = True
		self.__q = Queue.Queue(queue_length)
		self.__threads = []
		for i in range(num_threads):
			thread = ConsumerThread("Consumer Thread %d : "%i, self.__q, f)
			self.__threads.append(thread)
	def Start(self):
		for thread in self.__threads:
			thread.start()
		self._stopped = False
	def Stop(self):
		self._stopped = True
		for thread in self.__threads:
			thread.Stop()
		for thread in self.__threads:
			thread.join()
	def Feed(self, data):
		if self._stopped:
			return False
		self.__q.put(data)
		return True

class ProducerThread(StoppableThread):
	""" producer thread to work on a queue
	func() should return new data
	"""
	def __init__(self, name, consumers, func, trace = False):
		super(ProducerThread, self).__init__()
		self.__name = name
		self.__consumers = consumers
		self.__func = func
		self.__trace = trace
	def run(self):
		""" Called by threading
		"""
		self._Trace('Starting')
		self.__func(self.__name, self.__consumers, self.stopped)
		self._Trace('Exiting')
	def _Trace(self, msg):
		if self.__trace:
			print('%s [ %s ]\n'%(self.__name, msg)),

class Producer():
	""" For now, we only support 1 producer
	user don't need to define thread, just throw a callback.
	main thread will not be blocking on producer because it's running in another thread
	"""
	def __init__(self, func, consumers):
		self.__thread = ProducerThread('producer', consumers, func)
	def Start(self):
		self.__thread.start()
	def Stop(self):
		self.__thread.Stop()
		self.__thread.join()

import signal
def ExampleProduce(thread_name, consumers, stopped):
	for i in range(1000):
		if not stopped():
			print 'produce ', i
			consumers.Feed(i)
		else:
			print 'already stopped in ', thread_name
			break

def ExampleConsume(thread_name, data):
	print 'process ', data
	time.sleep(1)

def OnQuit(signal, frame):
	print 'quit'

if __name__ == '__main__':
	consumers = Consumers(ExampleConsume, 5, 6)
	consumers.Start()
	producer = Producer(ExampleProduce, consumers)
	producer.Start()

	# user can quit anytime safely by press ctrl+C
	signal.signal(signal.SIGINT, OnQuit)
	signal.pause()
	producer.Stop()
	consumers.Stop()
