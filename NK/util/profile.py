from __future__ import absolute_import
from __future__ import division
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import os, traceback, math, re, zlib, base64, time, sys, platform, glob, string, stat, types
import cPickle as pickle
import numpy
if sys.version_info[0] < 3:
	import ConfigParser
else:
	import configparser as ConfigParser

from NK.util import resources
from NK.util import version
from NK.util import validators

#The settings dictionary contains a key/value reference to all possible settings. With the setting name as key.
settingsDictionary = {}
#The settings list is used to keep a full list of all the settings. This is needed to keep the settings in the proper order,
# as the dictionary will not contain insertion order.
settingsList = []

#Stored profile presets
presetList = []

#Currently selected machine (by index) Cura support multiple machines in the same preferences and can switch between them.
# Each machine has it's own index and unique name.
_selectedMachineIndex = 0

class setting(object):
	#A setting object contains a configuration setting. These are globally accessible trough the quick access functions
	# and trough the settingsDictionary function.
	# Settings can be:
	# * profile settings (settings that effect the slicing process and the print result)
	# * preferences (settings that effect how cura works and acts)
	# * machine settings (settings that relate to the physical configuration of your machine)
	# * alterations (bad name copied from Skeinforge. These are the start/end code pieces)
	# Settings have validators that check if the value is valid, but do not prevent invalid values!
	# Settings have conditions that enable/disable this setting depending on other settings. (Ex: Dual-extrusion)
	def __init__(self, name, default, type, category, subcategory):
		self._name = name
		self._label = name
		self._tooltip = ''
		self._default = unicode(default)
		self._values = []
		self._type = type
		self._category = category
		self._subcategory = subcategory
		self._validators = []
		self._conditions = []

		if type is types.FloatType:
			validators.validFloat(self)
		elif type is types.IntType:
			validators.validInt(self)

		global settingsDictionary
		settingsDictionary[name] = self
		global settingsList
		settingsList.append(self)

	def setLabel(self, label, tooltip = ''):
		self._label = label
		self._tooltip = tooltip
		return self

	def setRange(self, minValue=None, maxValue=None):
		if len(self._validators) < 1:
			print "Warning: No range validator for: %s" % (self.getName())
			return self
		self._validators[0].minValue = minValue
		self._validators[0].maxValue = maxValue
		return self

	def getLabel(self):
		return _(self._label)

	def getTooltip(self):
		return _(self._tooltip)

	def getCategory(self):
		return self._category

	def getSubCategory(self):
		return self._subcategory

	def isPreference(self):
		return self._category == 'preference'

	def isMachineSetting(self):
		return self._category == 'machine'

	def isAlteration(self):
		return self._category == 'alteration'

	def isProfile(self):
		return not self.isAlteration() and not self.isPreference() and not self.isMachineSetting()

	def getName(self):
		return self._name

	def getType(self):
		return self._type

	def getValue(self, index = None):
		if index is None:
			index = self.getValueIndex()
		if index >= len(self._values):
			return self._default
		return self._values[index]

	def getDefault(self):
		return self._default

	def setValue(self, value, index = None):
		if index is None:
			index = self.getValueIndex()
		while index >= len(self._values):
			self._values.append(self._default)
		self._values[index] = unicode(value)

	def getValueIndex(self):
		if self.isMachineSetting():
			global _selectedMachineIndex
			return _selectedMachineIndex
		return 0

	def validate(self):
		result = validators.SUCCESS
		msgs = []
		for validator in self._validators:
			res, err = validator.validate()
			if res == validators.ERROR:
				result = res
			elif res == validators.WARNING and result != validators.ERROR:
				result = res
			if res != validators.SUCCESS:
				msgs.append(err)
		return result, '\n'.join(msgs)

	def addCondition(self, conditionFunction):
		self._conditions.append(conditionFunction)

	def checkConditions(self):
		for condition in self._conditions:
			if not condition():
				return False
		return True

#########################################################
## Settings
#########################################################

#Define a fake _() function to fake the gettext tools in to generating strings for the profile settings.
def _(n):
	return n

setting('cut_depth',                 5.0, float, 'basic',    _('Quality')).setRange(0.01).setLabel(_("Cut depth (mm)"), _(""))
setting('drill_diameter',            4.0, float, 'basic',    _('Quality')).setRange(0.0001).setLabel(_("Drill diameter (mm)"), _(""))
setting('cutting_feedrate',           10, float, 'basic',    _('Speed')).setRange(1).setLabel(_("Cutting speed (mm/s)"), _(""))
setting('cut_depth_step',            1.0, float, 'advanced', _('Quality')).setRange(1).setLabel(_("Cut depth step (mm)"), _(""))
setting('travel_height',             5.0, float, 'advanced', _('Quality')).setRange(0.1).setLabel(_("Travel height (mm)"), _(""))
setting('travel_speed',             50.0, float, 'advanced', _('Speed')).setRange(0.1).setLabel(_("Travel speed (mm/s)"), _("Speed at which travel moves are done."))

setting('engrave_depth',             1.5, float, 'basic',    _('Engrave')).setRange(0.01).setLabel(_("Engrave depth (mm)"), _(""))
setting('engrave_position',     'Inside', [_('Inside'), _('Outside'), _('Center')], 'basic',    _('Engrave')).setLabel(_("Engrave position"), _(""))

setting('tabs_enable',              True, bool,  'basic',    _('Holding tabs')).setLabel(_("Enable tabs"), _(""))
setting('tab_height',                1.0, float, 'advanced', _('Holding tabs')).setLabel(_("Tab depth"), _("Height of the holding tabs"))
setting('tab_width',                 5.0, float, 'advanced', _('Holding tabs')).setLabel(_("Tab width"), _("Width of each holding tab"))
setting('tab_min_distance',         50.0, float, 'advanced', _('Holding tabs')).setLabel(_("Minimal distance"), _("Minimal distance between each holding tab.\nThe tabs are placed somewhere between the minimal and maximal distance apart. While trying to avoid placing tabs on corners."))
setting('tab_max_distance',        150.0, float, 'advanced', _('Holding tabs')).setLabel(_("Maximal distance"), _("Maximal distance between each holding tab.\nThe tabs are placed somewhere between the minimal and maximal distance apart. While trying to avoid placing tabs on corners."))

setting('plugin_config', '', str, 'hidden', 'hidden')

setting('start.gcode', """;Generated at: {day} {date} {time}
G21 ; Scale in mm
G90 ; Absolute positioning
""", str, 'alteration', 'alteration')
#######################################################################################
setting('end.gcode', """;End GCode
;{profile_string}
""", str, 'alteration', 'alteration')
#######################################################################################

setting('lastFile', os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'resources', 'example', 'UltimakerRobot_support.stl')), str, 'preference', 'hidden')
setting('auto_detect_sd', 'True', bool, 'preference', 'hidden').setLabel(_("Auto detect SD card drive"), _("Auto detect the SD card. You can disable this because on some systems external hard-drives or USB sticks are detected as SD card."))
setting('language', 'English', str, 'preference', 'hidden').setLabel(_('Language'), _('Change the language in which Cura runs. Switching language requires a restart of Cura'))
setting('active_machine', '0', int, 'preference', 'hidden')

setting('model_colour', '#FFC924', str, 'preference', 'hidden').setLabel(_('Model colour'))
setting('model_colour2', '#CB3030', str, 'preference', 'hidden').setLabel(_('Model colour (2)'))
setting('model_colour3', '#DDD93C', str, 'preference', 'hidden').setLabel(_('Model colour (3)'))
setting('model_colour4', '#4550D3', str, 'preference', 'hidden').setLabel(_('Model colour (4)'))

setting('window_maximized', 'True', bool, 'preference', 'hidden')
setting('window_pos_x', '-1', float, 'preference', 'hidden')
setting('window_pos_y', '-1', float, 'preference', 'hidden')
setting('window_width', '-1', float, 'preference', 'hidden')
setting('window_height', '-1', float, 'preference', 'hidden')
setting('window_normal_sash', '320', float, 'preference', 'hidden')
setting('last_run_version', '', str, 'preference', 'hidden')

setting('machine_name', '', str, 'machine', 'hidden')
setting('machine_width', '120', float, 'machine', 'hidden').setLabel(_("Maximum width (mm)"), _("Size of the cutting area in mm"))
setting('machine_depth', '120', float, 'machine', 'hidden').setLabel(_("Maximum depth (mm)"), _("Size of the cutting area in mm"))
setting('machine_height', '5', float, 'machine', 'hidden').setLabel(_("Maximum height (mm)"), _("Size of the cutting area in mm"))
setting('serial_port', 'AUTO', str, 'machine', 'hidden').setLabel(_("Serial port"), _("Serial port to use for communication with the printer"))
setting('serial_port_auto', '', str, 'machine', 'hidden')
setting('serial_baud', 'AUTO', str, 'machine', 'hidden').setLabel(_("Baudrate"), _("Speed of the serial port communication\nNeeds to match your firmware settings\nCommon values are 250000, 115200, 57600"))
setting('serial_baud_auto', '', int, 'machine', 'hidden')

validators.warningAbove(settingsDictionary['travel_speed'], 300.0, _("It is highly unlikely that your machine can achieve a travel speed above 300mm/s"))

#Remove fake defined _() because later the localization will define a global _()
del _

#########################################################
## Profile and preferences functions
#########################################################

def getSubCategoriesFor(category):
	done = {}
	ret = []
	for s in settingsList:
		if s.getCategory() == category and not s.getSubCategory() in done and s.checkConditions():
			done[s.getSubCategory()] = True
			ret.append(s.getSubCategory())
	return ret

def getSettingsForCategory(category, subCategory = None):
	ret = []
	for s in settingsList:
		if s.getCategory() == category and (subCategory is None or s.getSubCategory() == subCategory) and s.checkConditions():
			ret.append(s)
	return ret

## Profile functions
def getBasePath():
	if platform.system() == "Windows":
		basePath = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
		#If we have a frozen python install, we need to step out of the library.zip
		if hasattr(sys, 'frozen'):
			basePath = os.path.normpath(os.path.join(basePath, ".."))
	else:
		basePath = os.path.expanduser('~/.nk/%s' % version.getVersion(False))
	if not os.path.isdir(basePath):
		os.makedirs(basePath)
	return basePath

def getAlternativeBasePaths():
	paths = []
	basePath = os.path.normpath(os.path.join(getBasePath(), '..'))
	for subPath in os.listdir(basePath):
		path = os.path.join(basePath, subPath)
		if os.path.isdir(path) and os.path.isfile(os.path.join(path, 'preferences.ini')) and path != getBasePath():
			paths.append(path)
		path = os.path.join(basePath, subPath, 'NinjaKittens')
		if os.path.isdir(path) and os.path.isfile(os.path.join(path, 'preferences.ini')) and path != getBasePath():
			paths.append(path)
	return paths

def getDefaultProfilePath():
	return os.path.join(getBasePath(), 'current_profile.ini')

def loadProfile(filename):
	#Read a configuration file as global config
	profileParser = ConfigParser.ConfigParser()
	try:
		profileParser.read(filename)
	except ConfigParser.ParsingError:
		return
	global settingsList
	for set in settingsList:
		if set.isPreference():
			continue
		section = 'profile'
		if set.isAlteration():
			section = 'alterations'
		if profileParser.has_option(section, set.getName()):
			set.setValue(unicode(profileParser.get(section, set.getName()), 'utf-8', 'replace'))

def saveProfile(filename):
	#Save the current profile to an ini file
	profileParser = ConfigParser.ConfigParser()
	profileParser.add_section('profile')
	profileParser.add_section('alterations')
	global settingsList
	for set in settingsList:
		if set.isPreference() or set.isMachineSetting():
			continue
		if set.isAlteration():
			profileParser.set('alterations', set.getName(), set.getValue().encode('utf-8'))
		else:
			profileParser.set('profile', set.getName(), set.getValue().encode('utf-8'))

	profileParser.write(open(filename, 'w'))

def resetProfile():
	#Read a configuration file as global config
	global settingsList
	for set in settingsList:
		if not set.isProfile():
			continue
		set.setValue(set.getDefault())

def setProfileFromString(options):
	options = base64.b64decode(options)
	options = zlib.decompress(options)
	(profileOpts, alt) = options.split('\f', 1)
	global settingsDictionary
	for option in profileOpts.split('\b'):
		if len(option) > 0:
			(key, value) = option.split('=', 1)
			if key in settingsDictionary:
				if settingsDictionary[key].isProfile():
					settingsDictionary[key].setValue(value)
	for option in alt.split('\b'):
		if len(option) > 0:
			(key, value) = option.split('=', 1)
			if key in settingsDictionary:
				if settingsDictionary[key].isAlteration():
					settingsDictionary[key].setValue(value)

def getProfileString():
	p = []
	alt = []
	global settingsList
	for set in settingsList:
		if set.isProfile():
			if set.getName() in tempOverride:
				p.append(set.getName() + "=" + tempOverride[set.getName()])
			else:
				p.append(set.getName() + "=" + set.getValue())
		elif set.isAlteration():
			if set.getName() in tempOverride:
				alt.append(set.getName() + "=" + tempOverride[set.getName()])
			else:
				alt.append(set.getName() + "=" + set.getValue())
	ret = '\b'.join(p) + '\f' + '\b'.join(alt)
	ret = base64.b64encode(zlib.compress(ret, 9))
	return ret

def insertNewlines(string, every=64): #This should be moved to a better place then profile.
	lines = []
	for i in xrange(0, len(string), every):
		lines.append(string[i:i+every])
	return '\n'.join(lines)

def getPreferencesString():
	p = []
	global settingsList
	for set in settingsList:
		if set.isPreference():
			p.append(set.getName() + "=" + set.getValue())
	ret = '\b'.join(p)
	ret = base64.b64encode(zlib.compress(ret, 9))
	return ret


def getProfileSetting(name):
	if name in tempOverride:
		return tempOverride[name]
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isProfile():
		return settingsDictionary[name].getValue()
	traceback.print_stack()
	sys.stderr.write('Error: "%s" not found in profile settings\n' % (name))
	return ''

def getProfileSettingFloat(name):
	try:
		setting = getProfileSetting(name).replace(',', '.')
		return float(eval(setting, {}, {}))
	except:
		return 0.0

def putProfileSetting(name, value):
	#Check if we have a configuration file loaded, else load the default.
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isProfile():
		settingsDictionary[name].setValue(value)

def isProfileSetting(name):
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isProfile():
		return True
	return False

## Preferences functions
def getPreferencePath():
	return os.path.join(getBasePath(), 'preferences.ini')

def getPreferenceFloat(name):
	try:
		setting = getPreference(name).replace(',', '.')
		return float(eval(setting, {}, {}))
	except:
		return 0.0

def getPreferenceColour(name):
	colorString = getPreference(name)
	return [float(int(colorString[1:3], 16)) / 255, float(int(colorString[3:5], 16)) / 255, float(int(colorString[5:7], 16)) / 255, 1.0]

def loadPreferences(filename):
	global settingsList
	global presetList
	#Read a configuration file as global config
	profileParser = ConfigParser.ConfigParser()
	try:
		profileParser.read(filename)
	except ConfigParser.ParsingError:
		return

	for set in settingsList:
		if set.isPreference():
			if profileParser.has_option('preference', set.getName()):
				set.setValue(unicode(profileParser.get('preference', set.getName()), 'utf-8', 'replace'))

	n = 0
	while profileParser.has_section('machine_%d' % (n)):
		for set in settingsList:
			if set.isMachineSetting():
				if profileParser.has_option('machine_%d' % (n), set.getName()):
					set.setValue(unicode(profileParser.get('machine_%d' % (n), set.getName()), 'utf-8', 'replace'), n)
		n += 1

	presetList = []
	n = 0
	while profileParser.has_section('preset_%d' % (n)):
		if profileParser.has_option('preset_%d' % (n), 'name') and profileParser.has_option('preset_%d' % (n), 'data'):
			name = unicode(profileParser.get('preset_%d' % (n), 'name'), 'utf-8', 'replace')
			data = unicode(profileParser.get('preset_%d' % (n), 'data'), 'utf-8', 'replace')
			presetList.append((name, data))
			n += 1
		else:
			break

	setActiveMachine(int(getPreferenceFloat('active_machine')))

def loadMachineSettings(filename):
	global settingsList
	#Read a configuration file as global config
	profileParser = ConfigParser.ConfigParser()
	try:
		profileParser.read(filename)
	except ConfigParser.ParsingError:
		return

	for set in settingsList:
		if set.isMachineSetting():
			if profileParser.has_option('machine', set.getName()):
				set.setValue(unicode(profileParser.get('machine', set.getName()), 'utf-8', 'replace'))
	checkAndUpdateMachineName()

def savePreferences(filename):
	global settingsList
	#Save the current profile to an ini file
	parser = ConfigParser.ConfigParser()
	parser.add_section('preference')

	for set in settingsList:
		if set.isPreference():
			parser.set('preference', set.getName(), set.getValue().encode('utf-8'))

	n = 0
	while getMachineSetting('machine_name', n) != '':
		parser.add_section('machine_%d' % (n))
		for set in settingsList:
			if set.isMachineSetting():
				parser.set('machine_%d' % (n), set.getName(), set.getValue(n).encode('utf-8'))
		n += 1

	for n in xrange(0, getPresetCount()):
		name, data = getPreset(n)
		parser.add_section('preset_%d' % (n))
		parser.set('preset_%d' % (n), 'name', name.encode('utf-8'))
		parser.set('preset_%d' % (n), 'data', data.encode('utf-8'))
	parser.write(open(filename, 'w'))

def getPreference(name):
	if name in tempOverride:
		return tempOverride[name]
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isPreference():
		return settingsDictionary[name].getValue()
	traceback.print_stack()
	sys.stderr.write('Error: "%s" not found in preferences\n' % (name))
	return ''

def putPreference(name, value):
	#Check if we have a configuration file loaded, else load the default.
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isPreference():
		settingsDictionary[name].setValue(value)
		savePreferences(getPreferencePath())
		return
	traceback.print_stack()
	sys.stderr.write('Error: "%s" not found in preferences\n' % (name))

def isPreference(name):
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isPreference():
		return True
	return False

def getMachineSettingFloat(name, index = None):
	try:
		setting = getMachineSetting(name, index).replace(',', '.')
		return float(eval(setting, {}, {}))
	except:
		return 0.0

def getMachineSetting(name, index = None):
	if name in tempOverride:
		return tempOverride[name]
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isMachineSetting():
		return settingsDictionary[name].getValue(index)
	traceback.print_stack()
	sys.stderr.write('Error: "%s" not found in machine settings\n' % (name))
	return ''

def putMachineSetting(name, value, index = None):
	#Check if we have a configuration file loaded, else load the default.
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isMachineSetting():
		settingsDictionary[name].setValue(value, index)
	savePreferences(getPreferencePath())

def isMachineSetting(name):
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isMachineSetting():
		return True
	return False

def checkAndUpdateMachineName():
	global _selectedMachineIndex
	name = getMachineSetting('machine_name')
	index = None
	if name == '':
		name = getMachineSetting('machine_type')
	for n in xrange(0, getMachineCount()):
		if n == _selectedMachineIndex:
			continue
		if index is None:
			if name == getMachineSetting('machine_name', n):
				index = 1
		else:
			if '%s (%d)' % (name, index) == getMachineSetting('machine_name', n):
				index += 1
	if index is not None:
		name = '%s (%d)' % (name, index)
	putMachineSetting('machine_name', name)
	putPreference('active_machine', _selectedMachineIndex)

def getMachineCount():
	n = 0
	while getMachineSetting('machine_name', n) != '':
		n += 1
	if n < 1:
		putMachineSetting('machine_name', 'Unknown', 0)
		return 1
	return n

def setActiveMachine(index):
	global _selectedMachineIndex
	_selectedMachineIndex = index
	putPreference('active_machine', _selectedMachineIndex)

def removeMachine(index):
	global _selectedMachineIndex
	global settingsList
	if getMachineCount() < 2:
		return
	for n in xrange(index, getMachineCount()):
		for setting in settingsList:
			if setting.isMachineSetting():
				setting.setValue(setting.getValue(n+1), n)

	if _selectedMachineIndex >= index:
		setActiveMachine(getMachineCount() - 1)

def getPresetCount():
	global presetList
	return len(presetList)

def getPreset(index):
	global presetList
	return presetList[index]

def savePreset(name):
	presetList.append((name, getProfileString()))

## Temp overrides for multi-extruder slicing and the project planner.
tempOverride = {}
def setTempOverride(name, value):
	tempOverride[name] = unicode(value).encode("utf-8")
def clearTempOverride(name):
	del tempOverride[name]
def resetTempOverride():
	tempOverride.clear()

#########################################################
## Utility functions to calculate common profile values
#########################################################
def calculateEdgeWidth():
	wallThickness = getProfileSettingFloat('wall_thickness')
	nozzleSize = getProfileSettingFloat('nozzle_size')

	if getProfileSetting('spiralize') == 'True':
		return wallThickness

	if wallThickness < 0.01:
		return nozzleSize
	if wallThickness < nozzleSize:
		return wallThickness

	lineCount = int(wallThickness / (nozzleSize - 0.0001))
	if lineCount == 0:
		return nozzleSize
	lineWidth = wallThickness / lineCount
	lineWidthAlt = wallThickness / (lineCount + 1)
	if lineWidth > nozzleSize * 1.5:
		return lineWidthAlt
	return lineWidth

def calculateLineCount():
	wallThickness = getProfileSettingFloat('wall_thickness')
	nozzleSize = getProfileSettingFloat('nozzle_size')

	if wallThickness < 0.01:
		return 0
	if wallThickness < nozzleSize:
		return 1
	if getProfileSetting('spiralize') == 'True':
		return 1

	lineCount = int(wallThickness / (nozzleSize - 0.0001))
	if lineCount < 1:
		lineCount = 1
	lineWidth = wallThickness / lineCount
	lineWidthAlt = wallThickness / (lineCount + 1)
	if lineWidth > nozzleSize * 1.5:
		return lineCount + 1
	return lineCount

def calculateSolidLayerCount():
	layerHeight = getProfileSettingFloat('layer_height')
	solidThickness = getProfileSettingFloat('solid_layer_thickness')
	if layerHeight == 0.0:
		return 1
	return int(math.ceil(solidThickness / (layerHeight - 0.0001)))

def calculateObjectSizeOffsets():
	size = 0.0

	if getProfileSetting('platform_adhesion') == 'Brim':
		size += getProfileSettingFloat('brim_line_count') * calculateEdgeWidth()
	elif getProfileSetting('platform_adhesion') == 'Raft':
		pass
	else:
		if getProfileSettingFloat('skirt_line_count') > 0:
			size += getProfileSettingFloat('skirt_line_count') * calculateEdgeWidth() + getProfileSettingFloat('skirt_gap')

	#if getProfileSetting('enable_raft') != 'False':
	#	size += profile.getProfileSettingFloat('raft_margin') * 2
	#if getProfileSetting('support') != 'None':
	#	extraSizeMin = extraSizeMin + numpy.array([3.0, 0, 0])
	#	extraSizeMax = extraSizeMax + numpy.array([3.0, 0, 0])
	return [size, size]

def getMachineCenterCoords():
	if getMachineSetting('machine_center_is_zero') == 'True':
		return [0, 0]
	return [getMachineSettingFloat('machine_width') / 2, getMachineSettingFloat('machine_depth') / 2]

#Returns a list of convex polygons, first polygon is the allowed area of the machine,
# the rest of the polygons are the dis-allowed areas of the machine.
def getMachineSizePolygons():
	size = numpy.array([getMachineSettingFloat('machine_width'), getMachineSettingFloat('machine_depth'), getMachineSettingFloat('machine_height')], numpy.float32)
	ret = []
	ret.append(numpy.array([[-size[0]/2,-size[1]/2],[ size[0]/2,-size[1]/2],[ size[0]/2, size[1]/2], [-size[0]/2, size[1]/2]], numpy.float32))

	# Circle platform for delta printers...
	# circle = []
	# steps = 16
	# for n in xrange(0, steps):
	# 	circle.append([math.cos(float(n)/steps*2*math.pi) * size[0]/2, math.sin(float(n)/steps*2*math.pi) * size[0]/2])
	# ret.append(numpy.array(circle, numpy.float32))

	if getMachineSetting('machine_type') == 'ultimaker2':
		#UM2 no-go zones
		w = 25
		h = 10
		ret.append(numpy.array([[-size[0]/2,-size[1]/2],[-size[0]/2+w+2,-size[1]/2], [-size[0]/2+w,-size[1]/2+h], [-size[0]/2,-size[1]/2+h]], numpy.float32))
		ret.append(numpy.array([[ size[0]/2-w-2,-size[1]/2],[ size[0]/2,-size[1]/2], [ size[0]/2,-size[1]/2+h],[ size[0]/2-w,-size[1]/2+h]], numpy.float32))
		ret.append(numpy.array([[-size[0]/2+w+2, size[1]/2],[-size[0]/2, size[1]/2], [-size[0]/2, size[1]/2-h],[-size[0]/2+w, size[1]/2-h]], numpy.float32))
		ret.append(numpy.array([[ size[0]/2, size[1]/2],[ size[0]/2-w-2, size[1]/2], [ size[0]/2-w, size[1]/2-h],[ size[0]/2, size[1]/2-h]], numpy.float32))
	return ret

#returns the number of extruders minimal used. Normally this returns 1, but with dual-extrusion support material it returns 2
def minimalExtruderCount():
	if int(getMachineSetting('extruder_amount')) < 2:
		return 1
	if getProfileSetting('support') == 'None':
		return 1
	if getProfileSetting('support_dual_extrusion') == 'Second extruder':
		return 2
	return 1

#########################################################
## Alteration file functions
#########################################################
def replaceTagMatch(m):
	pre = m.group(1)
	tag = m.group(2)
	if tag == 'time':
		return pre + time.strftime('%H:%M:%S')
	if tag == 'date':
		return pre + time.strftime('%d-%m-%Y')
	if tag == 'day':
		return pre + ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][int(time.strftime('%w'))]
	if tag == 'print_time':
		return pre + '#P_TIME#'
	if tag == 'filament_amount':
		return pre + '#F_AMNT#'
	if tag == 'filament_weight':
		return pre + '#F_WGHT#'
	if tag == 'filament_cost':
		return pre + '#F_COST#'
	if tag == 'profile_string':
		return pre + 'NINJA_PROFILE_STRING:%s' % (getProfileString())
	if pre == 'F' and tag == 'max_z_speed':
		f = getProfileSettingFloat('travel_speed') * 60
	if pre == 'F' and tag in ['print_speed', 'retraction_speed', 'travel_speed', 'bottom_layer_speed', 'cool_min_feedrate']:
		f = getProfileSettingFloat(tag) * 60
	elif isProfileSetting(tag):
		f = getProfileSettingFloat(tag)
	elif isPreference(tag):
		f = getProfileSettingFloat(tag)
	else:
		return '%s?%s?' % (pre, tag)
	if (f % 1) == 0:
		return pre + str(int(f))
	return pre + str(f)

def replaceGCodeTags(filename, gcodeInt):
	f = open(filename, 'r+')
	data = f.read(2048)
	data = data.replace('#P_TIME#', ('%5d:%02d' % (int(gcodeInt.totalMoveTimeMinute / 60), int(gcodeInt.totalMoveTimeMinute % 60)))[-8:])
	data = data.replace('#F_AMNT#', ('%8.2f' % (gcodeInt.extrusionAmount / 1000))[-8:])
	data = data.replace('#F_WGHT#', ('%8.2f' % (gcodeInt.calculateWeight() * 1000))[-8:])
	cost = gcodeInt.calculateCost()
	if cost is None:
		cost = 'Unknown'
	data = data.replace('#F_COST#', ('%8s' % (cost.split(' ')[0]))[-8:])
	f.seek(0)
	f.write(data)
	f.close()

def replaceGCodeTagsFromSlicer(filename, slicerInt):
	f = open(filename, 'r+')
	data = f.read(2048)
	data = data.replace('#P_TIME#', slicerInt.getPrintTime())
	data = data.replace('#F_AMNT#', slicerInt.getFilamentAmount())
	data = data.replace('#F_WGHT#', ('%8.2f' % (float(slicerInt.getFilamentWeight()) * 1000))[-8:])
	cost = slicerInt.getFilamentCost()
	if cost is None:
		cost = 'Unknown'
	data = data.replace('#F_COST#', ('%8s' % (cost.split(' ')[0]))[-8:])
	f.seek(0)
	f.write(data)
	f.close()

### Get aleration raw contents. (Used internally in Cura)
def getAlterationFile(filename):
	if filename in tempOverride:
		return tempOverride[filename]
	global settingsDictionary
	if filename in settingsDictionary and settingsDictionary[filename].isAlteration():
		return settingsDictionary[filename].getValue()
	traceback.print_stack()
	sys.stderr.write('Error: "%s" not found in alteration settings\n' % (filename))
	return ''

def setAlterationFile(name, value):
	#Check if we have a configuration file loaded, else load the default.
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isAlteration():
		settingsDictionary[name].setValue(value)
	saveProfile(getDefaultProfilePath())

def isTagIn(tag, contents):
	contents = re.sub(';[^\n]*\n', '', contents)
	return tag in contents

### Get the alteration file for output.
def getAlterationFileContents(filename):
	prefix = ''
	postfix = ''
	alterationContents = getAlterationFile(filename)
	return unicode(prefix + re.sub("(.)\{([^\}]*)\}", replaceTagMatch, alterationContents).rstrip() + '\n' + postfix).strip().encode('utf-8') + '\n'

###### PLUGIN #####

def getPluginConfig():
	try:
		return pickle.loads(str(getProfileSetting('plugin_config')))
	except:
		return []

def setPluginConfig(config):
	putProfileSetting('plugin_config', pickle.dumps(config))

def getPluginBasePaths():
	ret = []
	if platform.system() != "Windows":
		ret.append(os.path.expanduser('~/.ninja/plugins/'))
	if platform.system() == "Darwin" and hasattr(sys, 'frozen'):
		ret.append(os.path.normpath(os.path.join(resources.resourceBasePath, "NK/plugins")))
	else:
		ret.append(os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'plugins')))
	return ret

def getPluginList():
	ret = []
	for basePath in getPluginBasePaths():
		for filename in glob.glob(os.path.join(basePath, '*.py')):
			filename = os.path.basename(filename)
			if filename.startswith('_'):
				continue
			with open(os.path.join(basePath, filename), "r") as f:
				item = {'filename': filename, 'name': None, 'info': None, 'type': None, 'params': []}
				for line in f:
					line = line.strip()
					if not line.startswith('#'):
						break
					line = line[1:].split(':', 1)
					if len(line) != 2:
						continue
					if line[0].upper() == 'NAME':
						item['name'] = line[1].strip()
					elif line[0].upper() == 'INFO':
						item['info'] = line[1].strip()
					elif line[0].upper() == 'TYPE':
						item['type'] = line[1].strip()
					elif line[0].upper() == 'DEPEND':
						pass
					elif line[0].upper() == 'PARAM':
						m = re.match('([a-zA-Z][a-zA-Z0-9_]*)\(([a-zA-Z_]*)(?::([^\)]*))?\) +(.*)', line[1].strip())
						if m is not None:
							item['params'].append({'name': m.group(1), 'type': m.group(2), 'default': m.group(3), 'description': m.group(4)})
					else:
						print "Unknown item in effect meta data: %s %s" % (line[0], line[1])
				if item['name'] is not None and item['type'] == 'postprocess':
					ret.append(item)
	return ret

def runPostProcessingPlugins(gcodefilename):
	pluginConfigList = getPluginConfig()
	pluginList = getPluginList()

	for pluginConfig in pluginConfigList:
		plugin = None
		for pluginTest in pluginList:
			if pluginTest['filename'] == pluginConfig['filename']:
				plugin = pluginTest
		if plugin is None:
			continue

		pythonFile = None
		for basePath in getPluginBasePaths():
			testFilename = os.path.join(basePath, pluginConfig['filename'])
			if os.path.isfile(testFilename):
				pythonFile = testFilename
		if pythonFile is None:
			continue

		locals = {'filename': gcodefilename}
		for param in plugin['params']:
			value = param['default']
			if param['name'] in pluginConfig['params']:
				value = pluginConfig['params'][param['name']]

			if param['type'] == 'float':
				try:
					value = float(value)
				except:
					value = float(param['default'])

			locals[param['name']] = value
		try:
			execfile(pythonFile, locals)
		except:
			locationInfo = traceback.extract_tb(sys.exc_info()[2])[-1]
			return "%s: '%s' @ %s:%s:%d" % (str(sys.exc_info()[0].__name__), str(sys.exc_info()[1]), os.path.basename(locationInfo[0]), locationInfo[2], locationInfo[1])
	return None
