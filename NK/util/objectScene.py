__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

from NK.util import engine
from NK.util import util3d

class Scene(object):
	def __init__(self):
		self._objectList = []
		self.engine = engine.Engine(self._engineCallback)

	def addObject(self, obj):
		self._objectList.append(obj)
		obj._position = -(obj.getMin()) + complex(5, 5)
		for p in obj.paths:
			p.type = 'cut'
		util3d
		self.update()

	def getObjectList(self):
		return self._objectList

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

	def _engineCallback(self, process, ready):
		print process, ready
