from __future__ import absolute_import
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx

#from NK.gui import configWizard
from NK.gui import configBase
from NK.util import profile
from NK.util import resources

class preferencesDialog(wx.Dialog):
	def __init__(self, parent):
		super(preferencesDialog, self).__init__(None, title="Preferences")

		wx.EVT_CLOSE(self, self.OnClose)

		self.parent = parent
		self.panel = configBase.configPanelBase(self)

		left, right, main = self.panel.CreateDualConfigPanel(self)

		self.okButton = wx.Button(right, -1, 'Ok')
		right.GetSizer().Add(self.okButton, (right.GetSizer().GetRows(), 0), flag=wx.BOTTOM, border=5)
		self.okButton.Bind(wx.EVT_BUTTON, lambda e: self.Close())

		main.Fit()
		self.Fit()

	def OnClose(self, e):
		#self.parent.reloadSettingPanels()
		self.Destroy()

class machineSettingsDialog(wx.Dialog):
	def __init__(self, parent):
		super(machineSettingsDialog, self).__init__(None, title="Machine settings")

		wx.EVT_CLOSE(self, self.OnClose)

		self.parent = parent

		self.panel = configBase.configPanelBase(self)
		self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
		self.GetSizer().Add(self.panel, 1, wx.EXPAND)
		self.nb = wx.Notebook(self.panel)
		self.panel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		self.panel.GetSizer().Add(self.nb, 1, wx.EXPAND)

		for idx in xrange(0, profile.getMachineCount()):
			left, right, main = self.panel.CreateDualConfigPanel(self.nb)
			configBase.TitleRow(left, _("Machine settings"))
			configBase.SettingRow(left, 'machine_width', index=idx)
			configBase.SettingRow(left, 'machine_depth', index=idx)
			#configBase.SettingRow(left, 'machine_height', index=idx)

			self.nb.AddPage(main, profile.getMachineSetting('machine_name', idx).title())

		self.nb.SetSelection(int(profile.getPreferenceFloat('active_machine')))

		self.buttonPanel = wx.Panel(self.panel)
		self.panel.GetSizer().Add(self.buttonPanel)

		self.buttonPanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
		self.okButton = wx.Button(self.buttonPanel, -1, 'Ok')
		self.okButton.Bind(wx.EVT_BUTTON, lambda e: self.Close())
		self.buttonPanel.GetSizer().Add(self.okButton, flag=wx.ALL, border=5)

		self.addButton = wx.Button(self.buttonPanel, -1, 'Add new machine')
		self.addButton.Bind(wx.EVT_BUTTON, self.OnAddMachine)
		self.buttonPanel.GetSizer().Add(self.addButton, flag=wx.ALL, border=5)

		self.remButton = wx.Button(self.buttonPanel, -1, 'Remove machine')
		self.remButton.Bind(wx.EVT_BUTTON, self.OnRemoveMachine)
		self.buttonPanel.GetSizer().Add(self.remButton, flag=wx.ALL, border=5)

		main.Fit()
		self.Fit()

	def OnAddMachine(self, e):
		self.Hide()
		self.parent.Hide()
		profile.setActiveMachine(profile.getMachineCount())
		configWizard.configWizard(True)
		self.parent.Show()
		self.parent.reloadSettingPanels()
		self.parent.updateMachineMenu()

		prefDialog = machineSettingsDialog(self.parent)
		prefDialog.Centre()
		prefDialog.Show()
		wx.CallAfter(self.Close)

	def OnRemoveMachine(self, e):
		if profile.getMachineCount() < 2:
			wx.MessageBox(_("Cannot remove the last machine configuration in Cura"), _("Machine remove error"), wx.OK | wx.ICON_ERROR)
			return

		self.Hide()
		profile.removeMachine(self.nb.GetSelection())
		self.parent.reloadSettingPanels()
		self.parent.updateMachineMenu()

		prefDialog = machineSettingsDialog(self.parent)
		prefDialog.Centre()
		prefDialog.Show()
		wx.CallAfter(self.Close)

	def OnClose(self, e):
		self.parent.updateProfileToAllControls()
		self.Destroy()
