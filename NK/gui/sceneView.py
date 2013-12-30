from __future__ import absolute_import
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import numpy
import time
import os
import traceback
import threading
import math
import platform

import OpenGL
OpenGL.ERROR_CHECKING = False
from OpenGL.GLU import *
from OpenGL.GL import *

from NK.util import profile
from NK.util import resources
from NK.util import explorer
from NK.util import objectScene
from NK.util import drawingLoader
from NK.gui.util import opengl
from NK.gui.util import openglGui

class SceneView(openglGui.glGuiPanel):
	def __init__(self, parent):
		super(SceneView, self).__init__(parent)
		self._yaw = 0
		self._pitch = 0
		self._zoom = 300
		self._viewTarget = numpy.array([0,0,0], numpy.float32)
		self._platformTexture = None

		self._loadButton = openglGui.glButton(self, 4, _("Load"), (0, 0), self.ShowLoadDialog)

		self._notification = openglGui.glNotification(self, (0, 0))

		self._scene = objectScene.Scene()

		self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)

		self.updateProfileToControls()

	def sceneUpdated(self):
		self._scene.update()

	def ShowLoadDialog(self, button):
		dlg=wx.FileDialog(self, _("Open 3D model"), os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST|wx.FD_MULTIPLE)
		dlg.SetWildcard("2D file (*.dxf;*.svg)|*.dxf;*.svg")
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return
		filenames = dlg.GetPaths()
		dlg.Destroy()
		if len(filenames) < 1:
			return False
		profile.putPreference('lastFile', filenames[0])
		self.loadFiles(filenames)

	def loadFiles(self, filenames):
		for filename in filenames:
			for drawing in drawingLoader.loadDrawings(filename):
				self._scene.addObject(drawing)
		self._queueRefresh()

	def updateProfileToControls(self):
		self._machineSize = numpy.array([profile.getMachineSettingFloat('machine_width'), profile.getMachineSettingFloat('machine_depth'), profile.getMachineSettingFloat('machine_height')])

	def OnMouseWheel(self, e):
		delta = float(e.GetWheelRotation()) / float(e.GetWheelDelta())
		delta = max(min(delta,4),-4)
		self._zoom *= 1.0 - delta / 10.0
		if self._zoom < 1.0:
			self._zoom = 1.0
		if self._zoom > numpy.max(self._machineSize) * 3:
			self._zoom = numpy.max(self._machineSize) * 3
		self.Refresh()

	def OnMouseMotion(self,e):
		if e.Dragging():
			if not e.LeftIsDown() and e.RightIsDown():
				self._yaw += e.GetX() - self._mouseX
				self._pitch -= e.GetY() - self._mouseY
				if self._pitch > 90:
					self._pitch = 90
				if self._pitch < 0:
					self._pitch = 0
			elif (e.LeftIsDown() and e.RightIsDown()) or e.MiddleIsDown():
				self._zoom += e.GetY() - self._mouseY
				if self._zoom < 1:
					self._zoom = 1
				if self._zoom > numpy.max(self._machineSize) * 3:
					self._zoom = numpy.max(self._machineSize) * 3

		self._mouseX = e.GetX()
		self._mouseY = e.GetY()

	def _init3DView(self):
		# set viewing projection
		size = self.GetSize()
		glViewport(0, 0, size.GetWidth(), size.GetHeight())
		glLoadIdentity()

		glLightfv(GL_LIGHT0, GL_POSITION, [0.2, 0.2, 1.0, 0.0])

		glDisable(GL_RESCALE_NORMAL)
		glDisable(GL_LIGHTING)
		glDisable(GL_LIGHT0)
		glEnable(GL_DEPTH_TEST)
		glDisable(GL_CULL_FACE)
		glDisable(GL_BLEND)
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

		glClearColor(0.8, 0.8, 0.8, 1.0)
		glClearStencil(0)
		glClearDepth(1.0)

		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		aspect = float(size.GetWidth()) / float(size.GetHeight())
		gluPerspective(45.0, aspect, 1.0, numpy.max(self._machineSize) * 4)

		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)

	def OnPaint(self,e):
		glClearColor(0.8, 0.8, 0.8, 1.0)
		glClear(GL_DEPTH_BUFFER_BIT | GL_COLOR_BUFFER_BIT)

		self._init3DView()

		glTranslate(0,0,-self._zoom)
		glRotate(-self._pitch, 1,0,0)
		glRotate(self._yaw, 0,0,1)
		glTranslate(-self._viewTarget[0],-self._viewTarget[1],-self._viewTarget[2])

		glDisable(GL_DEPTH_TEST)
		self._drawMachine()
		glEnable(GL_DEPTH_TEST)

		self._viewport = glGetIntegerv(GL_VIEWPORT)
		self._modelMatrix = glGetDoublev(GL_MODELVIEW_MATRIX)
		self._projMatrix = glGetDoublev(GL_PROJECTION_MATRIX)

		for obj in self._scene.getObjectList():
			glPushMatrix()
			glTranslatef(obj._position.real, obj._position.imag, 0)
			for path in obj.paths:
				if path.isClosed():
					glColor3f(0,0,0)
				else:
					glColor3f(1,0,0)
				glBegin(GL_LINE_STRIP)
				for p in path.getPoints(1.0):
					glVertex3f(p[0].real, p[0].imag, 0)
				glEnd()
			glPopMatrix()

		glColor3f(0,1,1)
		glBegin(GL_LINE_STRIP)
		for p in self._scene.engine.resultPoints:
			glVertex3f(p[0], p[1], p[2])
		glEnd()

	def _drawMachine(self):
		if self._platformTexture is None:
			self._platformTexture = opengl.loadGLTexture('checkerboard.png')
			glBindTexture(GL_TEXTURE_2D, self._platformTexture)
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
		glColor4f(1,1,1,0.5)
		glBindTexture(GL_TEXTURE_2D, self._platformTexture)
		glEnable(GL_TEXTURE_2D)
		glBegin(GL_TRIANGLE_FAN)
		s = self._machineSize
		verts = [
			[-s[0]/2, s[0]/2],
			[-s[0]/2,-s[0]/2],
			[ s[0]/2,-s[0]/2],
			[ s[0]/2, s[0]/2],
		]
		for p in verts:
			glTexCoord2f(p[0]/20, p[1]/20)
			glVertex3f(p[0], p[1], 0)
		glEnd()
