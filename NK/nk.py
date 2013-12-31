#!/usr/bin/python
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

def main():
	from NK.gui import app
	from NK.util import profile

	profile.loadPreferences(profile.getPreferencePath())
	profile.loadProfile(profile.getDefaultProfilePath())

	args = []
	app.NKApp(args).MainLoop()

if __name__ == '__main__':
	main()
