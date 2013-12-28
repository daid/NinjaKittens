from __future__ import absolute_import
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import os
import sys
import urllib2
import platform
import subprocess
try:
	from xml.etree import cElementTree as ElementTree
except:
	from xml.etree import ElementTree

from NK.util import resources

def getVersion(getGitVersion = True):
	gitPath = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../.."))
	if hasattr(sys, 'frozen'):
		versionFile = os.path.normpath(os.path.join(resources.resourceBasePath, "version"))
	else:
		versionFile = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../version"))

	if getGitVersion:
		try:
			gitProcess = subprocess.Popen(args = "git show -s --pretty=format:%H", shell = True, cwd = gitPath, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
			(stdoutdata, stderrdata) = gitProcess.communicate()

			if gitProcess.returncode == 0:
				return stdoutdata
		except:
			pass

	gitHeadFile = gitPath + "/.git/refs/heads/master"
	if os.path.isfile(gitHeadFile):
		if not getGitVersion:
			return "dev"
		f = open(gitHeadFile, "r")
		version = f.readline()
		f.close()
		return version.strip()
	if os.path.exists(versionFile):
		f = open(versionFile, "r")
		version = f.readline()
		f.close()
		return version.strip()
	versionFile = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../../version"))
	if os.path.exists(versionFile):
		f = open(versionFile, "r")
		version = f.readline()
		f.close()
		return version.strip()
	return "?"

def isDevVersion():
	gitPath = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../../.git"))
	return os.path.exists(gitPath)

if __name__ == '__main__':
	print(getVersion())
