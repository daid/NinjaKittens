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
from NK.gui.util import opengl
from NK.gui.util import openglGui

class SceneView(openglGui.glGuiPanel):
	def __init__(self, parent):
		super(SceneView, self).__init__(parent)

		self.loadButton = openglGui.glButton(self, 4, _("Load"), (0, 0), None)

		self.notification = openglGui.glNotification(self, (0, 0))

		self.updateProfileToControls()

	def sceneUpdated(self):
		pass

	def loadFiles(self, filenames):
		pass

	def updateProfileToControls(self):
		pass

	def OnPaint(self,e):
		glClearColor(0.8, 0.8, 0.8, 1.0)
		glClear(GL_DEPTH_BUFFER_BIT | GL_COLOR_BUFFER_BIT)
