from __future__ import absolute_import
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import sys
import os
import platform
import shutil
import glob
import warnings

#Only import the _core to save import time
import wx._core

class NKApp(wx.App):
	def __init__(self, files):
		if platform.system() == "Windows" and not 'PYCHARM_HOSTED' in os.environ:
			super(NKApp, self).__init__(redirect=True, filename='output.txt')
		else:
			super(NKApp, self).__init__(redirect=False)

		self.mainWindow = None
		self.splash = None
		self.loadFiles = files

		if sys.platform.startswith('win') and len(files) > 0:
			#Check for an already running instance, if another instance is running load files in there
			from NK.util import version
			from ctypes import windll
			import ctypes
			import socket
			import threading

			other_hwnd = windll.user32.FindWindowA(None, ctypes.c_char_p('NK - ' + version.getVersion()))
			portNr = 0xCB00 + sum(map(ord, version.getVersion(False)))
			if other_hwnd != 0:
				sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
				sock.sendto('\0'.join(files), ("127.0.0.1", portNr))

				windll.user32.SetForegroundWindow(other_hwnd)
				return

			socketListener = threading.Thread(target=self.Win32SocketListener, args=(portNr,))
			socketListener.daemon = True
			socketListener.start()

		if sys.platform.startswith('darwin'):
			#Do not show a splashscreen on OSX, as by Apple guidelines
			self.afterSplashCallback()
		else:
			from NK.gui import splashScreen
			self.splash = splashScreen.splashScreen(self.afterSplashCallback)

	def MacOpenFile(self, path):
		try:
			self.mainWindow.OnDropFiles([path])
		except Exception as e:
			warnings.warn("File at {p} cannot be read: {e}".format(p=path, e=str(e)))

	def Win32SocketListener(self, port):
		import socket
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.bind(("127.0.0.1", port))
		while True:
			data, addr = sock.recvfrom(2048)
			self.mainWindow.OnDropFiles(data.split('\0'))

	def afterSplashCallback(self):
		#These imports take most of the time and thus should be done after showing the splashscreen
		from NK.gui import mainWindow
		from NK.util import profile
		from NK.util import resources

		resources.setupLocalization(profile.getPreference('language'))  # it's important to set up localization at very beginning to install _

		self.mainWindow = mainWindow.mainWindow()
		if self.splash is not None:
			self.splash.Show(False)
		self.mainWindow.Show()
		self.mainWindow.OnDropFiles(self.loadFiles)

		setFullScreenCapable(self.mainWindow)

if platform.system() == "Darwin":
	try:
		import ctypes, objc
		_objc = ctypes.PyDLL(objc._objc.__file__)

		# PyObject *PyObjCObject_New(id objc_object, int flags, int retain)
		_objc.PyObjCObject_New.restype = ctypes.py_object
		_objc.PyObjCObject_New.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]

		def setFullScreenCapable(frame):
			frameobj = _objc.PyObjCObject_New(frame.GetHandle(), 0, 1)

			NSWindowCollectionBehaviorFullScreenPrimary = 1 << 7
			window = frameobj.window()
			newBehavior = window.collectionBehavior() | NSWindowCollectionBehaviorFullScreenPrimary
			window.setCollectionBehavior_(newBehavior)
	except:
		def setFullScreenCapable(frame):
			pass

else:
	def setFullScreenCapable(frame):
		pass
