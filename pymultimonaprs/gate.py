#!/usr/bin/python2

import threading
import socket
import Queue
import pkg_resources
import sys

class IGate:
	def __init__(self, callsign, passcode, gateway):
		self.server, self.port = gateway.split(':')
		self.port = int(self.port)
		self.callsign = callsign
		self.passcode = passcode
		self.socket = None
		self._sending_queue = Queue.Queue(maxsize=1)
		self._connect()
		self._worker = threading.Thread(target=self._socket_worker)
		self._worker.setDaemon(True)
		self._worker.start()

	def _connect(self):
		# Connect
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		ip = socket.gethostbyname(self.server)
		print >> sys.stderr, "connecting... %s:%i" % (ip, self.port)
		self.socket.connect((ip, self.port))
		print >> sys.stderr, "connected"

		server_hello = self.socket.recv(1024)
		print >> sys.stderr, server_hello.strip(" \r\n")

		# Try to get my version
		try:
			version = pkg_resources.get_distribution("pymultimonaprs").version
		except:
			version = 'GIT'

		# Login
		print >> sys.stderr, "LOGIN: %s (PyMultimonAPRS %s)" % (self.callsign, version)
		self.socket.send("user %s pass %s vers PyMultimonAPRS %s filter r/38/-171/1\r\n" % (self.callsign, self.passcode, version))

		server_return = self.socket.recv(1024)
		print >> sys.stderr, server_return.strip(" \r\n")

		self.socket.setblocking(0)

	def send(self, tnc2_frame):
		self._sending_queue.put(tnc2_frame)

	def _socket_worker(self):
		"""
		Running as a thread, reading from socket, sending queue to socket
		"""
		while True:
			try:
				tnc2_frame = self._sending_queue.get(True, 1)
				print "sending: %s" % tnc2_frame
				self.socket.send("%s\r\n" % tnc2_frame)
			except Queue.Empty:
				pass
			except socket.error, e:
				if e.errno == 32:
					# socket disconnected
					print >> sys.stderr, "socket dead"
					self._connect()
			# read from socket to prevent buffer fillup
			try:
				self.socket.recv(40960)
			except socket.error, e:
				if e.errno == 11:
					# buffer empty
					pass
		print >> sys.stderr, "thread exit"
