__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

from NK.util import engine

class Scene(object):
	def __init__(self):
		self._objectList = []
		self.engine = engine.Engine(self._engineCallback)

	def addObject(self, obj):
		self._objectList.append(obj)
		obj._position = -((obj.getMin() + obj.getMax()) / 2.0)
		self.update()

	def getObjectList(self):
		return self._objectList

	def update(self):
		self.engine.runSlicer(self)

	def _engineCallback(self, process, ready):
		print process, ready
