__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

class Scene(object):
	def __init__(self):
		self._objectList = []

	def addObject(self, obj):
		self._objectList.append(obj)

	def getObjectList(self):
		return self._objectList
