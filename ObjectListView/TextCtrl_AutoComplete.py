# -*- coding: utf-8 -*-
__license__ = """Copyright (c) 2008-2010, Toni RuÅ¾a, All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS'
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE."""

__author__ = u"Toni RuÅ¾a <gmr.gaf@gmail.com>"
__url__  = "http://bitbucket.org/raz/wxautocompletectrl"

#Modified code from: https://bitbucket.org/raz/wxautocompletectrl/src/default/autocomplete.py

import wx
import wx.html

class SuggestionsPopup(wx.Frame):
	def __init__(self, parent, frame):
		# wx.Frame.__init__(self, frame, style = wx.FRAME_NO_TASKBAR|wx.FRAME_FLOAT_ON_PARENT|wx.STAY_ON_TOP)
		wx.Frame.__init__(self, frame, style = wx.FRAME_FLOAT_ON_PARENT|wx.STAY_ON_TOP|wx.RESIZE_BORDER)

		panel = wx.Panel(self, wx.ID_ANY)
		sizer = wx.BoxSizer(wx.VERTICAL)

		self._suggestions = self._listbox(panel)#, size = (parent.GetSize()[1], 100))#, size = (500, 400))
		self._suggestions.SetItemCount(0)
		self._unformated_suggestions = None

		sizer.Add(self._suggestions, 1, wx.ALL|wx.EXPAND, 5)
		panel.SetSizer(sizer)
		# sizer.Fit(self)

	class _listbox(wx.html.HtmlListBox):
		items = None

		def OnGetItem(self, n):
			return self.items[n]

	def SetSuggestions(self, suggestions, unformated_suggestions):
		self._suggestions.items = suggestions
		self._suggestions.SetItemCount(len(suggestions))
		self._suggestions.SetSelection(0)
	
		self._suggestions.Refresh()
		self.SendSizeEvent()

		self._unformated_suggestions = unformated_suggestions

	def CursorUp(self):
		selection = self._suggestions.GetSelection()
		if selection > 0:
			self._suggestions.SetSelection(selection - 1)

	def CursorDown(self):
		selection = self._suggestions.GetSelection()
		last = self._suggestions.GetItemCount() - 1
		if selection < last:
			self._suggestions.SetSelection(selection + 1)

	def CursorHome(self):
		if self.IsShown():
			self._suggestions.SetSelection(0)

	def CursorEnd(self):
		if self.IsShown():
			self._suggestions.SetSelection(self._suggestions.GetItemCount() - 1)

	def GetSelectedSuggestion(self):
		return self._unformated_suggestions[self._suggestions.GetSelection()]

	def GetSuggestion(self, n):
		return self._unformated_suggestions[n]


class AutocompleteTextCtrl(wx.TextCtrl):
	def __init__(self, parent, height=300, completer=None, multiline=False, frequency=250, style = None, **kwargs):
		style = style or 0

		style = style | wx.TE_PROCESS_ENTER
		if multiline:
			style = style | wx.TE_MULTILINE
		wx.TextCtrl.__init__(self, parent, style=style, **kwargs)
		self.height = height
		self.frequency = frequency
		if completer:
			self.SetCompleter(completer)
		self.queued_popup = False
		self.skip_event = False

	def default_completer(self, a_list):
		"""Modified code from: https://bitbucket.org/raz/wxautocompletectrl/src/default/test_autocomplete.py"""
		
		template = "%s<b><u>%s</b></u>%s"

		def completer(query):
			nonlocal template

			formatted, unformatted = [], []
			if query:
				unformatted = [item for item in a_list if query in item]
				for item in unformatted:
					s = item.find(query)
					formatted.append(
						template % (item[:s], query, item[s + len(query):])
					)

			return formatted, unformatted
		return completer

	def SetCompleter(self, completer):
		"""
		Initializes the autocompletion. The 'completer' has to be a function
		with one argument (the current value of the control, ie. the query)
		and it has to return two lists: formated (html) and unformated
		suggestions.
		"""
		
		if (callable(completer)):
			self.completer = completer
		else:
			self.completer = self.default_completer(completer)

		frame = self.Parent
		while not isinstance(frame, wx.Frame):
			frame = frame.Parent

		self.popup = SuggestionsPopup(self, frame)

		frame.Bind(wx.EVT_MOVE, self.OnMove)
		self.Bind(wx.EVT_TEXT, self.OnTextUpdate)
		self.Bind(wx.EVT_SIZE, self.OnSizeChange)
		self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
		self.popup._suggestions.Bind(wx.EVT_LEFT_DOWN, self.OnSuggestionClicked)
		self.popup._suggestions.Bind(wx.EVT_KEY_DOWN, self.OnSuggestionKeyDown)
		self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)

	def AdjustPopupPosition(self):
		self.popup.Position = self.ClientToScreen((0, self.Size.height)).Get()

	def OnMove(self, event):
		self.AdjustPopupPosition()
		event.Skip()

	def OnTextUpdate(self, event):
		if self.skip_event:
			self.skip_event = False
		elif not self.queued_popup:
			wx.CallLater(self.frequency, self.AutoComplete)
			self.queued_popup = True
		event.Skip()

	def AutoComplete(self):
		self.queued_popup = False

		if self.Value != "":
			formated, unformated = self.completer(self.Value)
			if len(formated) > 0:
				self.popup.SetSuggestions(formated, unformated)
				self.AdjustPopupPosition()
				# self.Unbind(wx.EVT_KILL_FOCUS)

				self.popup.ShowWithoutActivating()
				self.SetFocus()
				# self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
			else:
				self.popup.Hide()
		else:
			self.popup.Hide()

	def OnSizeChange(self, event):
		self.popup.Size = (self.Size[0], self.height)
		event.Skip()

	def OnKeyDown(self, event):
		key = event.GetKeyCode()

		if key == wx.WXK_UP:
			self.popup.CursorUp()
			return

		elif key == wx.WXK_DOWN:
			self.popup.CursorDown()
			return

		elif key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and self.popup.Shown:
			self.skip_event = True
			self.SetValue(self.popup.GetSelectedSuggestion())
			self.SetInsertionPointEnd()
			self.popup.Hide()
			return

		elif key == wx.WXK_HOME:
			self.popup.CursorHome()

		elif key == wx.WXK_END:
			self.popup.CursorEnd()

		elif event.ControlDown() and unichr(key).lower() == "a":
			self.SelectAll()

		elif key == wx.WXK_ESCAPE:
			self.popup.Hide()
			return

		event.Skip()

	def OnSuggestionClicked(self, event):
		self.skip_event = True
		n = self.popup._suggestions.VirtualHitTest(event.Position[1])
		self.Value = self.popup.GetSuggestion(n)
		self.SetInsertionPointEnd()
		wx.CallAfter(self.SetFocus)
		event.Skip()

	def OnSuggestionKeyDown(self, event):
		key = event.GetKeyCode()
		if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
			self.skip_event = True
			self.SetValue(self.popup.GetSelectedSuggestion())
			self.SetInsertionPointEnd()
			self.popup.Hide()
		event.Skip()

	def OnKillFocus(self, event):
		if not self.popup.IsActive():
			self.popup.Hide()
		event.Skip()

if __name__ == "__main__":
	import sys
	import os
	import random
	import string
	import wx


	template = "%s<b><u>%s</b></u>%s"


	def random_list_generator(query):
		formatted, unformatted = list(), list()
		if query:
			for i in range(random.randint(0, 30)):
				prefix = "".join(random.sample(string.ascii_letters, random.randint(0, 10)))
				postfix = "".join(random.sample(string.ascii_letters, random.randint(0, 10)))
				value = (prefix, query, postfix)
				formatted.append(template % value)
				unformatted.append("".join(value))

		return formatted, unformatted


	def list_completer(a_list):
		def completer(query):
			formatted, unformatted = list(), list()
			if query:
				unformatted = [item for item in a_list if query in item]
				for item in unformatted:
					s = item.find(query)
					formatted.append(
						template % (item[:s], query, item[s + len(query):])
					)

			return formatted, unformatted
		return completer


	def test():
		some_files = [
			name
			for path in sys.path if os.path.isdir(path)
			for name in os.listdir(path)
		]
		# quotes = open("taglines.txt").read().split("%%")
		quotes = some_files

		app = wx.App(False)
		app.TopWindow = frame = wx.Frame(None)
		frame.Sizer = wx.FlexGridSizer(3, 2, 5, 5)
		frame.Sizer.AddGrowableCol(1)
		frame.Sizer.AddGrowableRow(2)

		# A completer must return two lists of the same length based
		# on the "query" (current value in the TextCtrl).
		#
		# The first list contains items to be shown in the popup window
		# to the user. These items can use HTML formatting. The second list
		# contains items that will be put in to the TextCtrl, usually the
		# items from the first list striped of formating.

		field1 = AutocompleteTextCtrl(frame, completer=random_list_generator)
		field2 = AutocompleteTextCtrl(frame, completer=some_files)
		field3 = AutocompleteTextCtrl(
			frame, completer=list_completer(quotes), multiline=True
		)

		frame.Sizer.Add(wx.StaticText(frame, label="Random strings"))
		frame.Sizer.Add(field1, 0, wx.EXPAND)
		frame.Sizer.Add(wx.StaticText(frame, label="Files in sys.path"))
		frame.Sizer.Add(field2, 0, wx.EXPAND)
		frame.Sizer.Add(wx.StaticText(frame, label="Famous quotes"))
		frame.Sizer.Add(field3, 0, wx.EXPAND)
		frame.Show()
		app.MainLoop()

	test()