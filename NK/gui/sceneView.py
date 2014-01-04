from __future__ import absolute_import
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import numpy
import os

import OpenGL
OpenGL.ERROR_CHECKING = False
from OpenGL.GLU import *
from OpenGL.GL import *

from NK.util import profile
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
		self._selectedObject = None
		self._selectedPath = None
		self._mouseX = 0
		self._mouseY = 0
		self._mouseState = ''

		self._loadButton = openglGui.glButton(self, 4, _("Load"), (0, 0), self.ShowLoadDialog)
		self._saveButton = openglGui.glButton(self, 3, _("Save"), (1, 0), self.ShowSaveDialog)
		self._pathCutButton = openglGui.glButton(self, 0, _("Cut"), (0, -1), lambda button: self.SetSelectedPathType('cut'))
		self._pathEngraveButton = openglGui.glButton(self, 0, _("Engrave"), (1, -1), lambda button: self.SetSelectedPathType('engrave'))
		self._pathIgnoreButton = openglGui.glButton(self, 0, _("Ignore"), (3, -1), lambda button: self.SetSelectedPathType('ignore'))

		self._notification = openglGui.glNotification(self, (0, 0))

		self._scene = objectScene.Scene(self.QueueRefresh)

		self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)

		self.updateProfileToControls()
		self._viewTarget[0] = self._machineSize[0] / 2.0
		self._viewTarget[1] = self._machineSize[1] / 2.0
		self._zoom = numpy.max(self._machineSize) * 1.5

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

	def ShowSaveDialog(self, button):
		if len(self._scene.engine._gcode) < 1:
			return
		dlg=wx.FileDialog(self, _("Save GCode"), os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
		dlg.SetWildcard("GCode (*.gcode)|*.gcode|*.g|*.G")
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return
		filename = dlg.GetPath()
		dlg.Destroy()
		f = open(filename, "w")
		for line in self._scene.engine._gcode:
			f.write(line)
			f.write('\n')
		f.close()

	def loadFiles(self, filenames):
		for filename in filenames:
			for drawing in drawingLoader.loadDrawings(filename):
				self._scene.addObject(drawing)
				p = drawing._position + (drawing.getMin() + drawing.getMax()) / 2.0
				self._viewTarget[0] = p.real
				self._viewTarget[1] = p.imag
				self._zoom = abs(drawing.getMax() - drawing.getMin()) * 1.5
		self._queueRefresh()

	def SetSelectedPathType(self, type):
		if self._selectedPath is None:
			return
		self._selectedPath.type = type
		self.sceneUpdated()

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

	def OnMouseDown(self, e):
		self._mouseX = e.GetX()
		self._mouseY = e.GetY()
		if e.ButtonDClick():
			self._mouseState = 'doubleClick'
		else:
			self._mouseState = 'dragOrClick'

	def OnMouseMotion(self,e):
		if e.Dragging() and self._mouseState.startswith('drag'):
			if e.LeftIsDown() and not e.RightIsDown():
				p0, p1 = self.getMouseRay(self._mouseX, self._mouseY)
				cursorZ0 = p0 - (p1 - p0) * (p0[2] / (p1[2] - p0[2]))
				p0, p1 = self.getMouseRay(e.GetX(), e.GetY())
				cursorZ1 = p0 - (p1 - p0) * (p0[2] / (p1[2] - p0[2]))
				if self._focusObj is None:
					self._viewTarget += cursorZ0 - cursorZ1
				else:
					self._focusObj._position += complex(cursorZ1[0] - cursorZ0[0], cursorZ1[1] - cursorZ0[1])
					self._selectedObject = self._focusObj
					self._selectedPath = None
					self._mouseState = 'dragObject'
					if self._scene.isUpdateDone():
						self._scene.update()
			elif not e.LeftIsDown() and e.RightIsDown():
				self._yaw += e.GetX() - self._mouseX
				self._pitch -= e.GetY() - self._mouseY
				if self._pitch > 90:
					self._pitch = 90
				if self._pitch < 0:
					self._pitch = 0
			elif (e.LeftIsDown() and e.RightIsDown()) or e.MiddleIsDown():
				self._zoom *= (1.0 + (e.GetY() - self._mouseY) * 0.01)
				if self._zoom < 1:
					self._zoom = 1
				if self._zoom > numpy.max(self._machineSize) * 3:
					self._zoom = numpy.max(self._machineSize) * 3

		self._mouseX = e.GetX()
		self._mouseY = e.GetY()

	def OnMouseUp(self,e):
		if self._mouseState == 'dragOrClick' and e.Button == 1:
			p0, p1 = self.getMouseRay(e.GetX(), e.GetY())
			cursorZ0 = p0 - (p1 - p0) * (p0[2] / (p1[2] - p0[2]))
			self._selectedObject, self._selectedPath = self._scene.getObjectAt(complex(cursorZ0[0], cursorZ0[1]))
		if self._mouseState == 'dragObject':
			self.sceneUpdated()
		if self._yaw > 180:
			self._yaw -= 360
		if self._yaw < -180:
			self._yaw += 360
		if self._pitch < 10:
			for n in [-180, -90, 0, 90, 180]:
				if -10 + n < self._yaw < 10 + n:
					self._pitch = 0
					self._yaw = n
		self._mouseState = ''
		self._queueRefresh()

	def OnKeyChar(self, keyCode):
		if keyCode == wx.WXK_DELETE or keyCode == wx.WXK_NUMPAD_DELETE or (keyCode == wx.WXK_BACK and platform.system() == "Darwin"):
			if self._selectedObject is not None:
				self._deleteObject(self._selectedObject)

	def _deleteObject(self, obj):
		if obj == self._selectedObject:
			self._selectedObject = None
		if obj == self._focusObj:
			self._focusObj = None
		self._scene.remove(obj)

	def getMouseRay(self, x, y):
		if self._viewport is None:
			return numpy.array([0,0,0],numpy.float32), numpy.array([0,0,1],numpy.float32)
		p0 = opengl.unproject(x, self._viewport[1] + self._viewport[3] - y, 0, self._modelMatrix, self._projMatrix, self._viewport)
		p1 = opengl.unproject(x, self._viewport[1] + self._viewport[3] - y, 1, self._modelMatrix, self._projMatrix, self._viewport)
		return p0, p1

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
		glEnable(GL_BLEND)
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

		glClearColor(0.8, 0.8, 0.8, 1.0)
		glClearStencil(0)
		glClearDepth(1.0)

		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		aspect = float(size.GetWidth()) / float(size.GetHeight())
		if self._pitch == 0:
			f = 534.0 / 646.0
			h = self._zoom * aspect / 2.0 * f
			v = self._zoom / 2.0 * f
			glOrtho(-h, h, -v, v, -numpy.max(self._machineSize) * 4, numpy.max(self._machineSize) * 4)
		else:
			gluPerspective(45.0, aspect, 1.0, numpy.max(self._machineSize) * 4)

		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)

		if self._pitch != 0:
			glTranslate(0,0,-self._zoom)
		glRotate(-self._pitch, 1,0,0)
		glRotate(self._yaw, 0,0,1)
		glTranslate(-self._viewTarget[0],-self._viewTarget[1],-self._viewTarget[2])

	def OnPaint(self,e):

		glClearColor(0.8, 0.8, 0.8, 1.0)
		glClearStencil(0)
		glClear(GL_DEPTH_BUFFER_BIT | GL_COLOR_BUFFER_BIT)

		self._init3DView()
		for obj in self._scene.getObjectList():
			glPushMatrix()
			glTranslatef(obj._position.real, obj._position.imag, 0)
			idx = self._scene.getObjectList().index(obj)
			glColor3ub(0, 0, idx)
			self._drawEvenOddPaths(filter(lambda p: p.isClosed() and p.type == 'cut', obj.paths), obj)

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

		if self._mouseX > -1 and self._mouseState != 'dragObject':
			glFlush()
			n = glReadPixels(self._mouseX, self.GetSize().GetHeight() - 1 - self._mouseY, 1, 1, GL_RGBA, GL_UNSIGNED_INT_8_8_8_8)[0][0] >> 8
			if n < len(self._scene.getObjectList()):
				self._focusObj = self._scene.getObjectList()[n]
			else:
				self._focusObj = None
			# f = glReadPixels(self._mouseX, self.GetSize().GetHeight() - 1 - self._mouseY, 1, 1, GL_DEPTH_COMPONENT, GL_FLOAT)[0][0]
			# self._mouse3Dpos = opengl.unproject(self._mouseX, self._viewport[1] + self._viewport[3] - self._mouseY, f, self._modelMatrix, self._projMatrix, self._viewport)
			# self._mouse3Dpos -= self._viewTarget

		glClearColor(0.8, 0.8, 0.8, 1.0)
		glClearStencil(0)
		glClear(GL_DEPTH_BUFFER_BIT | GL_COLOR_BUFFER_BIT)

		self._init3DView()

		glDisable(GL_DEPTH_TEST)
		self._drawMachine()
		glEnable(GL_DEPTH_TEST)

		self._viewport = glGetIntegerv(GL_VIEWPORT)
		self._modelMatrix = glGetDoublev(GL_MODELVIEW_MATRIX)
		self._projMatrix = glGetDoublev(GL_PROJECTION_MATRIX)

		for obj in self._scene.getObjectList():
			glPushMatrix()
			glTranslatef(obj._position.real, obj._position.imag, 0)
			if obj == self._focusObj:
				glColor3f(1.0, 0.9, 0.9)
			elif obj == self._selectedObject:
				glColor3f(0.9, 0.9, 1.0)
			else:
				glColor3f(0.9, 0.9, 0.9)
			self._drawEvenOddPaths(filter(lambda p: p.isClosed() and p.type == 'cut', obj.paths), obj)

			glColor3f(0.7, 0.7, 1.0)
			self._drawEvenOddPaths(filter(lambda p: p.isClosed() and p.type == 'engrave', obj.paths), obj)
			glPopMatrix()

		for obj in self._scene.getObjectList():
			glPushMatrix()
			glTranslatef(obj._position.real, obj._position.imag, 0)
			for path in obj.paths:
				if path.type == 'ignore':
					glColor4f(0,0,0,0.3)
				elif path.isClosed():
					glColor3f(0,0,0)
				else:
					glColor3f(1,0,0)
				glBegin(GL_LINE_STRIP)
				for p in path.getPoints(1.0):
					glVertex3f(p[0].real, p[0].imag, 0)
				glEnd()

			glPopMatrix()

		if self._selectedObject is not None and self._selectedPath is not None:
			glPushMatrix()
			glTranslatef(self._selectedObject._position.real, self._selectedObject._position.imag, 0)

			glDisable(GL_DEPTH_TEST)
			glLineWidth(4.0)
			glColor3f(0, 0, 0)
			glBegin(GL_LINE_STRIP)
			for p in self._selectedPath.getPoints(1.0):
				glVertex3f(p[0].real, p[0].imag, 0)
			glEnd()
			glLineWidth(1.0)
			glEnable(GL_DEPTH_TEST)
			glPopMatrix()

		glBegin(GL_LINE_STRIP)
		for p in self._scene.engine.resultPoints:
			if p[2] > 0:
				glColor4f(1,0,1, 0.2)
			else:
				glColor3f(1,0,1)
			glVertex3f(p[0], p[1], p[2])
		glEnd()

	def _drawEvenOddPaths(self, paths, obj):
		glDisable(GL_DEPTH_TEST)
		glClear(GL_STENCIL_BUFFER_BIT)
		glStencilFunc(GL_ALWAYS, 1, 1)
		glStencilOp(GL_INCR, GL_INCR, GL_INCR)
		glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
		glEnable(GL_STENCIL_TEST)
		for path in paths:
			glBegin(GL_TRIANGLE_STRIP)
			for p in path.getPoints(1.0):
				glVertex3f(p[0].real, p[0].imag, 0)
				glVertex3f(p[0].real, obj.getMax().imag, 0)
			glEnd()
		glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP)
		glStencilFunc(GL_EQUAL, 0x01, 0x01)
		glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
		glBegin(GL_TRIANGLE_STRIP)
		glVertex3f(obj.getMin().real, obj.getMin().imag, 0)
		glVertex3f(obj.getMax().real, obj.getMin().imag, 0)
		glVertex3f(obj.getMin().real, obj.getMax().imag, 0)
		glVertex3f(obj.getMax().real, obj.getMax().imag, 0)
		glEnd()
		glDisable(GL_STENCIL_TEST)
		glEnable(GL_DEPTH_TEST)

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
			[0, s[1]],
			[0, 0],
			[s[0], 0],
			[s[0], s[1]],
		]
		textureScale = 20
		if numpy.max(s) >= 1000:
			textureScale = 200
		for p in verts:
			glTexCoord2f(p[0]/textureScale, p[1]/textureScale)
			glVertex3f(p[0], p[1], 0)
		glEnd()
