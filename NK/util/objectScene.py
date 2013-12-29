__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

class Scene(object):
	def __init__(self):
		self._objectList = []

	def addObject(self, obj):
		self._objectList.append(obj)
		obj._position = -((obj.getMin() + obj.getMax()) / 2.0)

	def getObjectList(self):
		return self._objectList
