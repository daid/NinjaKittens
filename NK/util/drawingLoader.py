__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import os

from NK.util.drawingLoaders import dxf
from NK.util.drawingLoaders import svg

def loadSupportedExtensions():
	return ['.dxf', '.svg']

def saveSupportedExtensions():
	return []

def loadWildcardFilter():
	wildcardList = ';'.join(map(lambda s: '*' + s, loadSupportedExtensions()))
	return "2D files (%s)|%s;%s" % (wildcardList, wildcardList, wildcardList.upper())

def saveWildcardFilter():
	wildcardList = ';'.join(map(lambda s: '*' + s, saveSupportedExtensions()))
	return "2D files (%s)|%s;%s" % (wildcardList, wildcardList, wildcardList.upper())

#loadMeshes loads 1 or more printableObjects from a file.
# STL files are a single printableObject with a single mesh, these are most common.
# OBJ files usually contain a single mesh, but they can contain multiple meshes
# AMF can contain whole scenes of objects with each object having multiple meshes.
# DAE files are a mess, but they can contain scenes of objects as well as grouped meshes

def loadDrawings(filename):
	ext = os.path.splitext(filename)[1].lower()
	if ext == '.dxf':
		return [dxf.DXF(filename)]
	if ext == '.svg':
		return [svg.SVG(filename)]
	print 'Error: Unknown drawing extension: %s' % (ext)
	return []

def saveDrawings(filename, objects):
	ext = os.path.splitext(filename)[1].lower()
	print 'Error: Unknown drawing extension: %s' % (ext)
