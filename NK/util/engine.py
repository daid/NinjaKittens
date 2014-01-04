__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import subprocess
import time
import math
import numpy
import os
import warnings
import threading
import traceback
import platform
import sys
import urllib
import urllib2
import hashlib

from NK.util import profile
from NK.util import version

def getEngineFilename():
	return 'C:/Software/NinjaKittens/Engine/.bin/Debug/Engine.exe'

def getCodeInt(line, code, default = None):
	n = line.find(code) + 1
	if n < 1:
		return default
	m = line.find(' ', n)
	try:
		if m < 0:
			return int(line[n:])
		return int(line[n:m])
	except:
		return default

def getCodeFloat(line, code, default = None):
	n = line.find(code) + 1
	if n < 1:
		return default
	m = line.find(' ', n)
	try:
		if m < 0:
			return float(line[n:])
		return float(line[n:m])
	except:
		return default

class Engine(object):
	def __init__(self, progressCallback):
		self._process = None
		self._thread = None
		self._callback = progressCallback
		self._objCount = 0
		self._gcode = []
		self._sliceLog = []
		self._id = 0
		self.resultPoints = []

	def abortSlicer(self):
		if self._process is not None:
			try:
				self._process.terminate()
			except:
				pass
			self._thread.join()
		self._thread = None

	def wait(self):
		if self._thread is not None:
			self._thread.join()

	def getGCodeFilename(self):
		return self._exportFilename

	def getSliceLog(self):
		return self._sliceLog

	def getID(self):
		return self._id

	def runSlicer(self, scene):
		if len(scene.getObjectList()) < 1:
			self._gcode = []
			self.resultPoints = []
			self._callback(1.0, False)
			return

		commandList = [getEngineFilename(), '-vv']
		for k, v in self._engineSettings().iteritems():
			commandList += ['-s', '%s=%s' % (k, str(v))]

		sendList = []
		for obj in scene.getObjectList():
			cutPaths = filter(lambda p: p.isClosed() and p.type == 'cut', obj.paths)
			sendList.append("%i\n" % (len(cutPaths)))
			for path in cutPaths:
				points = path.getPoints(profile.getProfileSettingFloat('drill_diameter') * 0.1)
				sendList.append("%i\n" % (len(points)))
				for p in points:
					sendList.append("%i %i\n" % ((p[0].real + obj._position.real) * 1000, (p[0].imag + obj._position.imag) * 1000))

			engravePaths = filter(lambda p: p.isClosed() and p.type == 'engrave', obj.paths)
			sendList.append("%i\n" % (len(engravePaths)))
			for path in engravePaths:
				points = path.getPoints(profile.getProfileSettingFloat('drill_diameter') * 0.1)
				sendList.append("%i\n" % (len(points)))
				for p in points:
					sendList.append("%i %i\n" % ((p[0].real + obj._position.real) * 1000, (p[0].imag + obj._position.imag) * 1000))

			commandList += ['-r']
		commandList += ['-p']
		self._thread = threading.Thread(target=self._watchProcess, args=(commandList, sendList, self._thread))
		self._thread.daemon = True
		self._thread.start()

	def _watchProcess(self, commandList, sendList, oldThread):
		if oldThread is not None:
			if self._process is not None:
				try:
					self._process.terminate()
				except:
					pass
			oldThread.join()
		self._id += 1
		self._callback(-1.0, False)
		try:
			self._process = self._runSliceProcess(commandList)
		except OSError:
			traceback.print_exc()
			return
		if self._thread != threading.currentThread():
			self._process.terminate()
		self._callback(0.0, False)
		self._gcode = []
		self._sliceLog = []

		sendThread = threading.Thread(target=self._sendProcess, args=(self._process.stdin, sendList))
		sendThread.daemon = True
		sendThread.start()

		line = self._process.stdout.readline()
		while len(line):
			line = line.strip()
			self._gcode.append(line.strip())
			line = self._process.stdout.readline()
		for line in self._process.stderr:
			self._sliceLog.append(line.strip())
		returnCode = self._process.wait()
		sendThread.join()
		for line in self._sliceLog:
			print line
		self.resultPoints = []
		if returnCode == 0:
			p = [0.0, 0.0, 0.0]
			for line in self._gcode:
				g = getCodeInt(line, 'G', None)
				if g == 0 or g == 1:
					p[0] = getCodeFloat(line, 'X', p[0])
					p[1] = getCodeFloat(line, 'Y', p[1])
					p[2] = getCodeFloat(line, 'Z', p[2])
				self.resultPoints.append(p[:])
			self._callback(1.0, True)
		else:
			self._callback(-1.0, False)
		self._process = None

	def _sendProcess(self, stdin, sendList):
		for item in sendList:
			try:
				stdin.write(item)
			except IOError:
				pass

	def _engineSettings(self):
		settings = {
			'cutPathOffset': int(profile.getProfileSettingFloat('drill_diameter') * 1000 / 2),
			'cutFeedrate': int(profile.getProfileSettingFloat('cutting_feedrate') * 60),
			'travelFeedrate': int(profile.getProfileSettingFloat('travel_speed') * 60),
			'travelHeight': int(profile.getProfileSettingFloat('travel_height') * 1000),
			'cutDepth': int(profile.getProfileSettingFloat('cut_depth') * 1000),
			'cutDepthStep': int(profile.getProfileSettingFloat('cut_depth_step') * 1000),
			'engravePathOffset': int(profile.getProfileSettingFloat('drill_diameter') * 1000 / 2),
			'engraveDepth': int(profile.getProfileSettingFloat('engrave_depth') * 1000),

			'startCode': profile.getAlterationFileContents('start.gcode'),
			'endCode': profile.getAlterationFileContents('end.gcode'),
		}
		if profile.getProfileSetting('engrave_position') == 'Center':
			settings['engravePathOffset'] = 0
		if profile.getProfileSetting('engrave_position') == 'Outside':
			settings['engravePathOffset'] = -settings['engravePathOffset']
		if profile.getProfileSetting('tabs_enable') == 'True':
			settings['tabDepth'] = settings['cutDepth'] - int(profile.getProfileSettingFloat('tab_height') * 1000)
			settings['tabWidth'] = int(profile.getProfileSettingFloat('tab_width') * 1000)
			settings['minTabDistance'] = int(profile.getProfileSettingFloat('tab_min_distance') * 1000)
			settings['maxTabDistance'] = int(profile.getProfileSettingFloat('tab_max_distance') * 1000)
		else:
			settings['tabDepth'] = settings['cutDepth']
		return settings

	def _runSliceProcess(self, cmdList):
		kwargs = {}
		if subprocess.mswindows:
			su = subprocess.STARTUPINFO()
			su.dwFlags |= subprocess.STARTF_USESHOWWINDOW
			su.wShowWindow = subprocess.SW_HIDE
			kwargs['startupinfo'] = su
			kwargs['creationflags'] = 0x00004000 #BELOW_NORMAL_PRIORITY_CLASS
		return subprocess.Popen(cmdList, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
