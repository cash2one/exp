#!/usr/bin/python
__copyright__ = 'Copyright 2011-2014, Yuliang Wang(yuliang.leon@gmail.com).'

import sys
sys.path.append('/home/ec2-user/src/common')

from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
from ascommon import rand_string

class RequestHandler(SimpleXMLRPCRequestHandler):
	rpc_paths = ('/RPC2',)

class Chubby:
	""" Usage:
	import xmlrpclib
	s = xmlrpclib.ServerProxy('http://localhost:8180')
	s.GetUniqueKey()
	"""
	def __init__(self):
		# TODO. timeout and change this key.
		self.__unique_key = rand_string()

	def GetUniqueKey(self):
		return self.__unique_key

if __name__ == '__main__':
  server = SimpleXMLRPCServer(("localhost", 8180),
                              requestHandler=RequestHandler)
  server.register_introspection_functions()
  server.register_instance(Chubby())
  server.serve_forever()
