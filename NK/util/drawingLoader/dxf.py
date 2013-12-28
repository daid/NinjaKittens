from __future__ import absolute_import
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import math
import re
import sys
import numpy
from xml.etree import ElementTree

from Cura.util.drawingLoader import drawing

class DXF(drawing.Drawing):
	def __init__(self, filename):
		super(DXF, self).__init__()
		self._lastLine = None
		self._polyLine = None

		entityType = 'UNKNOWN'
		sectionName = 'UNKNOWN'
		activeObject = None
		f = open(filename, "r")
		while True:
			groupCode = f.readline().strip()
			if groupCode == '':
				break
			groupCode = int(groupCode)
			value = f.readline().strip()
			if groupCode == 0:
				if sectionName == 'ENTITIES':
					self._checkForNewPath(entityType, activeObject)
				entityType = value
				activeObject = {}
			elif entityType == 'SECTION':
				if groupCode == 2:
					sectionName = value
			else:
				activeObject[groupCode] = value
		if sectionName == 'ENTITIES':
			self._checkForNewPath(entityType, activeObject)
		f.close()

		self._postProcessPaths()

	def _checkForNewPath(self, type, obj):
		if type == 'LINE':
			if self._lastLine is not None and self._lastLinePoint == complex(float(obj[10]), float(obj[20])):
				self._lastLine.addLineTo(float(obj[11]), float(obj[21]))
			else:
				p = self.addPath(float(obj[10]), float(obj[20]))
				p.addLineTo(float(obj[11]), float(obj[21]))
				self._lastLine = p
			self._lastLinePoint = complex(float(obj[11]), float(obj[21]))
		elif type == 'POLYLINE':
			self._polyLine = None
		elif type == 'VERTEX':
			if self._polyLine is None:
				self._polyLine = self.addPath(float(obj[10]), float(obj[20]))
			else:
				self._polyLine.addLineTo(float(obj[10]), float(obj[20]))
		else:
			print type

if __name__ == '__main__':
	for n in xrange(1, len(sys.argv)):
		print 'File: %s' % (sys.argv[n])
		dxf = DXF(sys.argv[n])

	dxf.saveAsHtml("test_export.html")

