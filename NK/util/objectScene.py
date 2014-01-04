__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

from NK.util import engine

def colorDist(c1, c2):
	dist = abs((c1 & 0xFF) - (c2 & 0xFF))
	dist += abs(((c1 >> 8) & 0xFF) - ((c2 >> 8) & 0xFF))
	dist += abs(((c1 >> 16) & 0xFF) - ((c2 >> 16) & 0xFF))
	return dist

class Scene(object):
	def __init__(self, updateCallback):
		self._objectList = []
		self.engine = engine.Engine(self._engineCallback)
		self._updateCallback = updateCallback

	def addObject(self, objInput):
		objInput._position = -(objInput.getMin()) + complex(5, 5)
		for obj in objInput.split():
			self._objectList.append(obj)
			obj._position = objInput._position
			for p in obj.paths:
				if colorDist(p.color, 0x0000FF) < 32:
					p.type = 'engrave'
				elif colorDist(p.color, 0x404040) < 32:
					p.type = 'ignore'
				else:
					p.type = 'cut'
		self.update()

	def getObjectList(self):
		return self._objectList

	def remove(self, obj):
		self._objectList.remove(obj)
		self.update()

	def getObjectAt(self, p):
		best = None
		bestPath = None
		bestDist = 10.0
		for obj in self._objectList:
			cursor = p - obj._position
			for path in obj.paths:
				points = path.getPoints(1.0)
				p0 = points[0][0]
				for p1, idx in points[1:]:
					diff = p1-p0
					length = abs(diff)
					if length == 0:
						continue
					diff2 = cursor - p0
					off = (diff.real * diff2.real + diff.imag * diff2.imag) / length
					if off < 0:
						off = 0
					if off > length:
						off = length
					Q = p0 + diff/length * off
					if abs(Q - cursor) < bestDist:
						bestDist = abs(Q - cursor)
						best = obj
						bestPath = path
					p0 = p1
		return best, bestPath

	def update(self):
		self.engine.runSlicer(self)

	def isUpdateDone(self):
		return self._updateReady

	def _engineCallback(self, process, ready):
		self._updateReady = ready
		self._updateCallback()
