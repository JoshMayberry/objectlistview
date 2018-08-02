# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Name:         ObjectListView.py
# Author:       Phillip Piper
# Created:      29 February 2008
# Copyright:    (c) 2008 Phillip Piper
# License:      wxWindows license
#----------------------------------------------------------------------------
# Change log:
# 2009-06-09  JPP   - AutoSizeColumns() now updates space filling columns
#                   - FastObjectListView.RepopulateList() now uses Freeze/Thaw
#                   - Fixed bug with virtual lists being clearws when scrolled vertically
# 2008-12-16  JPP   - Removed flicker from RefreshObject() on FastObjectListView and GroupListView
# 2008-12-01  JPP   - Handle wierd toggle check box on selection when there is no selection
#                   - Fixed bug in RefreshObjects() when the list is empty
# 2008-11-30  JPP   - Fixed missing variable bug in CancelCellEdit()
# v1.2
# 2008/09/02  JPP   - Added BatchedUpdate adaptor
#                   - Improved speed of selecting and refreshing by keeping a map
#                     of objects to indicies
#                   - Added GetIndexOf()
#                   - Removed flicker from FastObjectListView.AddObjects() and RefreshObjects()
# 2008/08/27  JPP   - Implemented filtering
#                   - Added GetObjects() and GetFilteredObjects()
#                   - Added resortNow parameter to SetSortColumn()
# 2008/08/23  JPP   - Added AddObjects()/RemoveObjects() and friends
#                   - Removed duplicate code when building/refreshing/adding objects
#                   - One step closer to secondary sort column support
# 2008/08/18  JPP   - Handle model objects that cannot be hashed
#                   - Added CELL_EDIT_STARTED and CELL_EDIT_FINISHED events
# 2008/08/16  JPP   - Added ensureVisible parameter to SelectObject()
# 2008/08/05  JPP   - GroupListView is now implemented as a virtual list. Much faster!
# v1.1
# 2008/07/19  JPP   - Added GroupListView
#                   - Broke common virtual list behaviour into AbstractVirtualListView
# 2008/07/13  JPP   - Added CopySelectionToClipboard and CopyObjectsToClipboard
# 2008/07/08  JPP   - Fixed several Linux specific bugs/limits
# 2008/07/03  JPP   - Allow headers to have images
# v1.0.1
# 2008/06/22  JPP   - Allowed for custom sorting, even on virtual lists
#                   - Fixed bug where an imageGetter that returned 0 was treated
#                     as if it returned -1 (i.e. no image)
# 2008/06/17  JPP   - Use binary searches when searching on sorted columns
# 2008/06/16  JPP   - Search by sorted column works, even on virtual lists
# 2008/06/12  JPP   - Added sortable parameter
#                   - Renamed sortColumn to be sortColumnIndex to make it clear
#                   - Allow returns in multiline cell editors
# v1.0
# 2008/05/29  JPP   Used named images internally
# 2008/05/26  JPP   Fixed pyLint annoyances
# 2008/05/24  JPP   Images can be referenced by name
# 2008/05/17  JPP   Checkboxes supported
# 2008/04/18  JPP   Cell editing complete
# 2008/03/31  JPP   Added space filling columns
# 2008/03/29  JPP   Added minimum, maximum and fixed widths for columns
# 2008/03/22  JPP   Added VirtualObjectListView and FastObjectListView
# 2008/02/29  JPP   Version converted from wax
# 2006/11/03  JPP   First version under wax
#----------------------------------------------------------------------------
# To do:
# - selectable columns, triggered on right click on header
# - secondary sort column
# - optionally preserve selection on RepopulateList
# - get rid of scrollbar when editing label in icon view
# - need a ChangeView() method to help when switching between views

"""
An `ObjectListView` provides a more convienent and powerful interface to a ListCtrl.

The major features of an `ObjectListView` are:

	* Automatically transforms a collection of model objects into a ListCtrl.
	* Automatically sorts rows by their data type.
	* Easily edits the values shown in the ListCtrl.
	* Supports all ListCtrl views (report, list, large and small icons).
	* Columns can be fixed-width, have a minimum and/or maximum width, or be space-filling.
	* Displays a "list is empty" message when the list is empty (obviously).
	* Supports custom formatting of rows
	* Supports alternate rows background colors.
	* Supports checkbox columns
	* Supports searching (by typing) on the sorted column -- even on virtual lists.
	* Supports filtering of rows
	* The `FastObjectListView` version can build a list of 10,000 objects in less than 0.1 seconds.
	* The `VirtualObjectListView` version supports millions of rows through ListCtrl's virtual mode.
	* The `GroupListView` version partitions it's rows into collapsible groups.

An `ObjectListView` works in a declarative manner: the programmer configures how it should
work, then gives it the list of objects to display. The primary configuration is in the
definitions of the columns. Columns are configured to know which aspect of their model
they should display, how it should be formatted, and even how new values should be written
back into the model. See `ColumnDefn` for more information.

"""

__author__ = "Phillip Piper"
__date__ = "18 June 2008"

import wx
import types
import wx.dataview
import datetime
import itertools
import locale
import operator
import string
import time
import six
import unicodedata

from . import DOLVEvent



#----------------------------------------------------------------------------
# A DataView version of ObjectListView
class DataObjectListView(wx.dataview.DataViewCtrl):

	"""
	An atempt to recreate ObjectListView using a DataViewCtrl. Use at your own risk.

	* ownerDrawn
		If this property is True, custom renderers can be used. Note: This may slow things down.
	"""

	CELLEDIT_NONE = 0
	CELLEDIT_SINGLECLICK = 1
	CELLEDIT_DOUBLECLICK = 2
	CELLEDIT_F2ONLY = 3

	"""Names of standard images used within the ObjectListView. If you want to use your
	own image in place of a standard one, simple register it with AddNamedImages() using
	one of the following names."""
	NAME_DOWN_IMAGE = "objectListView.downImage"
	NAME_UP_IMAGE = "objectListView.upImage"
	NAME_CHECKED_IMAGE = "objectListView.checkedImage"
	NAME_UNCHECKED_IMAGE = "objectListView.uncheckedImage"
	NAME_UNDETERMINED_IMAGE = "objectListView.undeterminedImage"
	NAME_EXPANDED_IMAGE = "objectListView.expandedImage"
	NAME_COLLAPSED_IMAGE = "objectListView.collapsedImage"

	"""When typing into the list, a delay between keystrokes greater than this (in seconds)
	will be interpretted as a new search and any previous search text will be cleared"""
	SEARCH_KEYSTROKE_DELAY = 0.75

	"""When typing into a list and searching on an unsorted column, we don't even try to search
	if there are more than this many rows."""
	MAX_ROWS_FOR_UNSORTED_SEARCH = 100000

	def __init__(self, *args, **kwargs):
		"""
		Create a DataObjectListView.

		"""
		_log("@DataObjectListView.__init__")
		

		#Standard
		self.columns = {}
		self.modelObjects = []
		self.colorOverride = {}
		self.lastSelected = None

		self.noHeader 				= kwargs.pop("noHeader", False)
		self.rowFormatter 			= kwargs.pop("rowFormatter", None)
		self.singleSelect 			= kwargs.pop("singleSelect", True)
		self.verticalLines 			= kwargs.pop("verticalLines", False)
		self.horizontalLines 		= kwargs.pop("horizontalLines", False)
		
		self.groupBackColor			= kwargs.pop("groupBackColor", None)# wx.Colour(195, 144, 212))  # LIGHT MAGENTA
		self.oddRowsBackColor		= kwargs.pop("oddRowsBackColor", wx.Colour(255, 250, 205))  # LEMON CHIFFON
		self.evenRowsBackColor		= kwargs.pop("evenRowsBackColor", wx.Colour(240, 248, 255))  # ALICE BLUE
		self.useAlternateBackColors = kwargs.pop("useAlternateBackColors", True)
		self.backgroundColor 		= kwargs.pop("backgroundColor", None)
		self.foregroundColor 		= kwargs.pop("foregroundColor", None)
		
		#Sorting
		self.groups = []
		self.emptyGroups = []
		
		self.filter 					= kwargs.pop("filter", None)
		self.sortable 					= kwargs.pop("sortable", True)
		self.caseSensative 				= kwargs.pop("caseSensative", True)
		self.compareFunction			= kwargs.pop("compareFunction", None)
		self.groupCompareFunction 		= kwargs.pop("groupCompareFunction", None)
		self.typingSearchesSortColumn	= kwargs.pop("typingSearchesSortColumn", True)

		#Editing
		self.cellEditor = None
		self.cellBeingEdited = None
		self.selectionBeforeCellEdit = []

		self.cellEditMode 	= kwargs.pop("cellEditMode", self.CELLEDIT_NONE)

		#Searching
		self.searchPrefix = u""
		self.whenLastTypingEvent = 0

		#Groups
		self.groupTitle 				= kwargs.pop("groupTitle", "")
		self.showGroups 				= kwargs.pop("showGroups", False)
		self.showItemCounts 			= kwargs.pop("showItemCounts", True)
		self.separateGroupColumn 		= kwargs.pop("separateGroupColumn", False)
		self.alwaysGroupByColumnIndex	= kwargs.pop("alwaysGroupByColumnIndex", -1)
		self.putBlankLineBetweenGroups	= kwargs.pop("putBlankLineBetweenGroups", True)
		self.rebuildGroup_onColumnClick = kwargs.pop("rebuildGroup_onColumnClick", True)

		self.groupFont 					= kwargs.pop("groupFont", None) #(Bold, Italic, Color)
		self.groupTextColour 			= kwargs.pop("groupTextColour", wx.Colour(33, 33, 33, 255))
		self.groupBackgroundColour 		= kwargs.pop("groupBackgroundColour", wx.Colour(159, 185, 250, 249))

		#Etc
		self.handleStandardKeys = True
		self.emptyListMsg 	= kwargs.pop("emptyListMsg", "This list is empty")
		self.emptyListFont 	= kwargs.pop("emptyListFont", wx.Font(24, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))

		#Setup Style
		style = kwargs.pop("style", None) #Do NOT pass in wx.LC_REPORT, or it will call virtual functions A LOT
		if (style is None):
			style = "0"
			if (self.singleSelect):
				style += "|wx.dataview.DV_SINGLE"
			else:
				style += "|wx.dataview.DV_MULTIPLE"

			if (self.horizontalLines):
				style += "|wx.dataview.DV_HORIZ_RULES"

			if (self.verticalLines):
				style += "|wx.dataview.DV_VERT_RULES"

			if (self.noHeader):
				style += "|wx.dataview.DV_NO_HEADER"

			# if (self.useAlternateBackColors):
			# 	#Currently only supported by the native GTK and OS X implementations
			# 	style += "|wx.dataview.DV_ROW_LINES" #Cannot change colors?
			wx.dataview.DataViewCtrl.__init__(self, *args, style = eval(style), **kwargs)
		else:
			wx.dataview.DataViewCtrl.__init__(self, *args, style = style, **kwargs)

		if (self.backgroundColor != None):
			super().SetBackgroundColour(self.backgroundColor)
		if (self.foregroundColor != None):
			super().SetForegroundColour(self.foregroundColor)

		if (self.groupFont is None):
			font = self.GetFont()
			self.groupFont = wx.FFont(font.GetPointSize(), font.GetFamily(), wx.FONTFLAG_BOLD, font.GetFaceName())
		if (isinstance(self.groupFont, wx.Font)):
			self.groupFont = (self.groupFont.GetWeight() == wx.BOLD, self.groupFont.GetStyle() == wx.ITALIC, wx.Colour(0, 0, 0))

		self.SetModel()
		self.overlayEmptyListMsg = wx.Overlay()

		#Bind Functions
		self.Bind(wx.EVT_SIZE, self._HandleSize)
		self.Bind(wx.dataview.EVT_DATAVIEW_COLUMN_HEADER_CLICK, self._HandleColumnClick)

		for child in self.GetChildren():
			#The wx.Control is the top bar, and the wx.Window is the panel below it
			if (not isinstance(child, wx.Control)):
				child.Bind(wx.EVT_PAINT, self._HandleOverlays)

		#Bind Event Relays
		self.Bind(wx.dataview.EVT_DATAVIEW_SELECTION_CHANGED, self._RelaySelectionChanged)
		self.Bind(wx.dataview.EVT_DATAVIEW_ITEM_CONTEXT_MENU, self._RelayCellContextMenu)
		self.Bind(wx.dataview.EVT_DATAVIEW_ITEM_ACTIVATED, self._RelayCellActivated)
		self.Bind(wx.dataview.EVT_DATAVIEW_COLUMN_HEADER_CLICK, self._RelayColumnHeaderClick)
		self.Bind(wx.dataview.EVT_DATAVIEW_COLUMN_HEADER_RIGHT_CLICK, self._RelayColumnHeaderRightClick)
		self.Bind(wx.dataview.EVT_DATAVIEW_COLUMN_SORTED, self._RelaySorted)
		self.Bind(wx.dataview.EVT_DATAVIEW_COLUMN_REORDERED, self._RelayReorder)
		self.Bind(wx.dataview.EVT_DATAVIEW_ITEM_COLLAPSING, self._RelayCollapsing)
		self.Bind(wx.dataview.EVT_DATAVIEW_ITEM_COLLAPSED, self._RelayCollapsed)
		self.Bind(wx.dataview.EVT_DATAVIEW_ITEM_EXPANDING, self._RelayExpanding)
		self.Bind(wx.dataview.EVT_DATAVIEW_ITEM_EXPANDED, self._RelayExpanded)
		self.Bind(wx.dataview.EVT_DATAVIEW_ITEM_START_EDITING, self._RelayEditCellStarting)
		self.Bind(wx.dataview.EVT_DATAVIEW_ITEM_EDITING_STARTED, self._RelayEditCellStarted)
		self.Bind(wx.dataview.EVT_DATAVIEW_ITEM_EDITING_DONE, self._RelayEditCellFinishing)
		self.Bind(wx.dataview.EVT_DATAVIEW_ITEM_VALUE_CHANGED, self._RelayEditCellFinished)






		#FOR DEBUGGING
		# self.Bind(wx.dataview.EVT_DATAVIEW_ITEM_CONTEXT_MENU, self.on_expand)
	
	# def on_expand(self, event):
		#FOR DEBUGGING 
	# 	item = event.GetItem()
	# 	print("@5.1", item.IsOk())
	# 	_log("@5.1")
	# 	super().Expand(item)
	# 	_log("@5.2")
	# 	print("@5.2", self.IsExpanded(item), self.model.IsContainer(item))
	# 	event.Skip()

	# --------------------------------------------------------------#000000#FFFFFF
	# Setup


	#https://stackoverflow.com/questions/32711381/wxpython-wxdataviewlistctrl-get-all-selected-rows-items

	def SetModel(self, model = None):
		"""
		Associates the ListCtrl with the supplied model.
		If *model* is None, will use *NormalListModel*.
		"""
		_log("@DataObjectListView.SetModel", model)

		# Create an instance of our model...
		if model is None:
			self.model = NormalListModel(self)
		else:
			self.model = model

		# Tel the DVC to use the model
		self.AssociateModel(self.model)
		self.model.DecRef() # avoid memory leak

	def SetColumns(self, columns, repopulate = True):
		_log("@DataObjectListView.SetColumns", columns, repopulate)
		sortCol = self.GetSortColumn()
		self.ClearAll()
		self.ClearColumns()

		# TO DO: Change this to account for column re-ordering by user
		self.columns = {}
		for x in columns:
			if (isinstance(x, DataColumnDefn)):
				self.AddColumnDefn(x)
			else:
				self.AddColumnDefn(DataColumnDefn(*x))

		self.UpdateGroupColumn()

		#Try to preserve the sort column
		self.SetSortColumn(sortCol)
		if (repopulate):
			self.RepopulateList()
		self.AutoSizeColumns()

	def AddColumnDefn(self, defn, index = None):
		"""
		Append the given ColumnDefn object to our list of active columns.

		If this method is called directly, you must also call RepopulateList()
		to populate the new column with data.
		"""
		_log("@DataObjectListView.AddColumnDefn", defn)
		self.columns[len(self.columns)] = defn

		#https://wxpython.org/Phoenix/docs/html/wx.dataview.DataViewColumn.html
		#https://wxpython.org/Phoenix/docs/html/wx.dataview.DataViewColumnFlags.enumeration.html
		#https://wxpython.org/Phoenix/docs/html/wx.dataview.DataViewCtrl.html#wx.dataview.DataViewCtrl.AppendColumn
		defn.SetEditable()
		defn.column = wx.dataview.DataViewColumn(defn.title, defn.renderer, index or len(self.columns) - 1, width = defn.width, align = defn.GetAlignment())
		defn.SetSortable()
		defn.SetReorderable()
		defn.SetResizeable()
		defn.SetHidden()

		if (index):
			self.InsertColumn(index, defn.column)
		else:
			self.AppendColumn(defn.column)

	def SetObjects(self, modelObjects, preserveSelection = False, preserveExpansion = True):
		"""
		Set the list of modelObjects to be displayed by the control.
		"""
		_log("@DataObjectListView.SetObjects", modelObjects, preserveSelection)

		if (preserveSelection):
			selection = self.GetSelectedObjects()

		self.ClearAll()
		if (modelObjects is None):
			modelObjects = []

		self.AddObjects(modelObjects, preserveExpansion = preserveExpansion)

		if (preserveSelection):
			self.SelectObjects(selection)

	def SetEmptyListMsg(self, msg):
		"""
		When there are no objects in the list, show this message in the control
		"""
		self.emptyListMsg = msg

	def SetEmptyListMsgFont(self, font):
		"""
		In what font should the empty list msg be rendered?
		"""
		self.emptyListFont = font

	def SetBackgroundColour(self, model, color = None):
		"""
		Changes the background color for the specified model only.
		If *color* is None, the default color will be used.
		"""

		if (color != None):
			self.colorOverride[model] = color
		elif (model in self.colorOverride):
			del self.colorOverride[model]

		# self.model.ItemChanged(model)
		self.model.Cleared()

	#-------------------------------------------------------------------------
	# Accessing

	def GetItemCount(self):
		return len(self.modelObjects)

	def GetObjects(self):
		"""
		Return the model objects that are available to the control.

		If no filter is in effect, this is the same as GetFilteredObjects().
		"""
		return self.modelObjects

	def GetColumns(self):
		"""
		Returns a list of all columns.
		"""
		return self.columns

	def GetCurrentColumn(self):
		"""
		Returns the column that currently has focus.
		"""
		column = super().GetCurrentColumn()
		if (not column):
			return
		return self.columns[column.GetModelColumn()]

	#Selection Functions
	def YieldSelected(self):
		"""
		Progressively yield all selected items
		"""
		_log("@DataObjectListView.YieldSelected")

		for item in self.GetSelections():
			yield self.model.ItemToObject(item)

	def GetSelectedObject(self):
		"""
		Return the selected modelObject or None if nothing is selected
		"""
		_log("@DataObjectListView.GetSelectedObject")
		for model in self.YieldSelectedObjects():
			return model
		return None

	def GetSelectedObjects(self):
		"""
		Return a list of the selected modelObjects
		"""
		_log("@DataObjectListView.GetSelectedObjects")
		return list(self.YieldSelectedObjects())

	def YieldSelectedObjects(self):
		"""
		Progressively yield the selected modelObjects
		"""
		_log("@DataObjectListView.YieldSelectedObjects")

		for item in self.YieldSelected():
			if (not isinstance(item, DataListGroup)):
				yield item

	def GetSelectedGroup(self):
		"""
		Return the selected groups or None if nothing is selected
		"""
		_log("@DataObjectListView.GetSelectedGroup")
		for model in self.YieldSelectedGroups():
			return model
		return None

	def GetSelectedGroups(self):
		"""
		Return a list of the selected groups
		"""
		_log("@DataObjectListView.GetSelectedGroups")
		return list(self.YieldSelectedGroups())

	def YieldSelectedGroups(self):
		"""
		Progressively yield the selected groups
		"""
		_log("@DataObjectListView.YieldSelectedGroups")

		for item in self.YieldSelected():
			if (isinstance(item, DataListGroup)):
				yield item

	def IsObjectSelected(self, modelObject):
		"""
		Is the given modelObject selected?
		"""
		return modelObject in self.GetSelectedObjects()

	def IsGroupSelected(self, group):
		"""
		Is the given group selected?
		"""
		if (isinstance(group, str)):
			return group in [item.key for item in self.GetSelectedGroups()]
		else:
			return group in self.GetSelectedGroups()

	def SetSelections(self, modelObjects):
		self.UnselectAll()
		for item in modelObjects:
			self.Select(item)

	def Select(self, modelObject):
		item = self.model.ObjectToItem(modelObject)
		super().Select(item)

	def Unselect(self, modelObject):
		item = self.model.ObjectToItem(modelObject)
		super().Unselect(item)

	def SelectAll(self):
		"""
		Selected all model objects in the control.

		In a GroupListView, this does not select blank lines or groups
		"""
		super().SelectAll()

	def UnselectAll(self):
		"""
		Unselect all model objects in the control.
		"""
		super().UnselectAll()

	def SelectObject(self, modelObject, deselectOthers = True, ensureVisible = False):
		"""
		Select the given modelObject. If deselectOthers is True, all other rows will be deselected
		"""
		if (deselectOthers):
			self.UnselectAll()

		self.Select(modelObject)

		if (ensureVisible):
			self.EnsureVisible(modelObject)

	def SelectObjects(self, modelObjects, deselectOthers = True):
		"""
		Select all of the given modelObjects. If deselectOthers is True, all other rows will be deselected
		"""
		if (deselectOthers):
			self.UnselectAll()

		for x in modelObjects:
			self.SelectObject(x, deselectOthers = False)

	def SelectGroup(self, modelObject, deselectOthers = True, ensureVisible = False):
		"""
		Select the group of the given modelObject. If deselectOthers is True, all other rows will be deselected
		"""

		if (isinstance(modelObject, str)):
			modelObject = [group for group in self.groups if (group.key == modelObject)][0]

		self.SelectObject(modelObject, deselectOthers = deselectOthers, ensureVisible = ensureVisible)

	def SelectGroups(self, modelObjects, deselectOthers = True):
		"""
		Select all the groups of the given modelObjects. If deselectOthers is True, all other rows will be deselected
		"""
		if (deselectOthers):
			self.UnselectAll()

		for x in modelObjects:
			self.SelectGroup(x, deselectOthers = False)

	#Show functions
	def GetShowItemCounts(self):
		"""
		Return whether or not the number of items in a groups should be included in the title
		"""
		return self.showItemCounts

	def SetShowItemCounts(self, showItemCounts=True):
		"""
		Set whether or not the number of items in a groups should be included in the title
		"""
		if (showItemCounts != self.showItemCounts):
			self.showItemCounts = showItemCounts
			self._BuildGroupTitles(self.groups, self.GetGroupByColumn())
			self._SetGroups(self.groups)

	#Get column functions
	def GetPrimaryColumn(self, returnIndex = False):
		"""
		Return the primary column or None there is no primary column.

		The primary column is the first column given by the user.
		This column is edited when F2 is pressed.
		"""
		i = self.GetPrimaryColumnIndex()
		if (i == -1):
			return None
		elif (returnIndex):
			return i
		else:
			return self.columns[i]

	def GetPrimaryColumnIndex(self):
		"""
		Return the index of the primary column. Returns -1 when there is no primary column.

		The primary column is the first column given by the user.
		This column is edited when F2 is pressed.
		"""
		for i, x in self.columns.items():
			if (not x.isInternal):
				return i
		return -1

	#Groups
	def UpdateGroupColumn(self):
		if ((not self.showGroups) or (not self.separateGroupColumn)):
			self.columns.pop(None, None)
			return

		if (None not in self.columns):
			self.columns[None] = DataColumnDefn(title = self.groupTitle)
		else:
			defn.title = self.groupTitle

		defn = self.columns[None]
		if (defn.column and defn.column.GetOwner()):
			self.DeleteColumn(defn.column)

		defn.column = wx.dataview.DataViewColumn(defn.title, defn.renderer, 0, width = defn.width, align = defn.GetAlignment())
		self.InsertColumn(0, defn.column)

	def SetGroups(self, groups):
		"""
		Present the collection of DataListGroups in this control.

		Calling this automatically put the control into ShowGroup mode
		"""
		self.modelObjects = list()
		self.SetShowGroups(True)
		self._SetGroups(groups)

	def SetEmptyGroups(self, groups):
		"""
		A list of keys that should be included as groups, even if they have nothing in them.
		If a group already exists with that key, no empty group will be created.
		"""
		self.emptyGroups = groups

	def GetShowGroups(self):
		"""
		Return whether or not this control is showing groups of objects or a straight list
		"""
		return self.showGroups

	def SetShowGroups(self, showGroups = True):
		"""
		Set whether or not this control is showing groups of objects or a straight list
		"""
		if (showGroups == self.showGroups):
			return

		self.showGroups = showGroups
		if (not len(self.columns)):
			return

		self.model.Cleared()

	def GetGroupByColumn(self, *args, **kwargs):
		"""
		Return the column by which the rows should be grouped
		"""
		if (self.alwaysGroupByColumnIndex >= 0):
			return self.GetAlwaysGroupByColumn(*args, **kwargs)

		elif (self.GetSortColumn(*args, **kwargs) is None):
			return self.GetPrimaryColumn(*args, **kwargs)

		else:
			return self.GetSortColumn(*args, **kwargs)

	def GetAlwaysGroupByColumn(self, returnIndex = False):
		"""
		Get the column by which the rows should be always be grouped.
		"""
		if (self.alwaysGroupByColumnIndex == -1):
			index = max([i for i in self.columns.keys() if (i is not None)])
			if (returnIndex):
				return index
			return self.columns[index]
		try:
			column = self.columns[self.alwaysGroupByColumnIndex]
			if (returnIndex):
				return self.alwaysGroupByColumnIndex
			return column
		except KeyError:
			return None

	def SetAlwaysGroupByColumn(self, column):
		"""
		Set the column by which the rows should be always be grouped.

		'column' can be None (which clears the setting), a DataColumnDefn,
		or the index of the column desired
		"""
		if (column is None):
			self.alwaysGroupByColumnIndex = -1
		elif (isinstance(column, DataColumnDefn)):
			try:
				self.alwaysGroupByColumnIndex = [key for key, value in self.columns.items() if (value is column)][0]
			except IndexError:
				self.alwaysGroupByColumnIndex = -1
		else:
			self.alwaysGroupByColumnIndex = column

	def ToggleExpansion(self, group):
		"""
		Toggle the expanded/collapsed state of the given group and redisplay the list
		"""
		self._DoExpandCollapse([group], not group.IsExpanded())

	def Expand(self, group):
		"""
		Expand the given group and redisplay the list
		"""
		self._DoExpandCollapse([group], True)

	def Collapse(self, group):
		"""
		Collapse the given group and redisplay the list
		"""
		# _log("@DataObjectListView.Collapse", group)
		self._DoExpandCollapse([group], False)

	def ExpandAll(self, groups=None):
		"""
		Expand the given groups (or all groups) and redisplay the list
		"""
		if groups is None:
			groups = self.groups
		self._DoExpandCollapse(groups, True)

	def CollapseAll(self, groups=None):
		"""
		Collapse the given groups (or all groups) and redisplay the list
		"""
		if groups is None:
			groups = self.groups

		self._DoExpandCollapse(groups, False)

	def _DoExpandCollapse(self, groups, isExpanding):
		"""
		Do the real work of expanding/collapsing the given groups
		"""
		_log("@DataObjectListView._DoExpandCollapse", groups, isExpanding)
		# Cull groups that aren't going to change
		groups = [x for x in groups if x.IsExpanded() != isExpanding]
		if not groups:
			return

		# Expand/collapse the groups
		for x in event.groups:
			if (isExpanding):
				super().Expand(self.model.ObjectToItem(x))
			else:
				super().Collapse(self.model.ObjectToItem(x))

	def Reveal(self, modelObject):
		"""
		Ensure that the given modelObject is visible, expanding the group it belongs to,
		if necessary
		"""

		self.EnsureVisible(modelObject)


		# # Find which group (if any) the object belongs to, and
		# # expand it and then try to reveal it again
		#self.ExpandAncestors(self.model.ObjectToItem(modelObject))
		# for group in self.groups:
		# 	if not group.IsExpanded() and modelObject in group.modelObjects:
		# 		self.Expand(group)
		# 		return self.Reveal(modelObject)

		return False

	def FindGroupFor(self, modelObject):
		"""
		Return the group that contains the given object or None if the given
		object is not found
		"""
		for group in self.groups:
			if modelObject in group.modelObjects:
				return group
		return None

	#Sizing
	def AutoSizeColumns(self):
		"""
		Resize our auto sizing columns to match the data
		"""
		# _log("@DataObjectListView.AutoSizeColumns")
		for iCol, col in self.columns.items():
			if (col.width == wx.LIST_AUTOSIZE):
				col.column.SetWidth(wx.LIST_AUTOSIZE)

				# The new width must be within our minimum and maximum
				colWidth = col.column.GetWidth()
				boundedWidth = col.CalcBoundedWidth(colWidth)
				if (colWidth != boundedWidth):
					col.column.SetWidth(boundedWidth)

		self._ResizeSpaceFillingColumns()

	def _ResizeSpaceFillingColumns(self):
		"""
		Change the width of space filling columns so that they fill the
		unoccupied width of the listview
		"""
		# _log("@DataObjectListView._ResizeSpaceFillingColumns")
		# If the list isn't in report view or there are no space filling
		# columns, just return
		if (not self.InReportView()):
			return

		# Don't do anything if there are no space filling columns
		if (True not in set(x.isSpaceFilling for x in self.columns.values())):
			return

		# Calculate how much free space is available in the control
		totalFixedWidth = sum(x.column.GetWidth() for x in self.columns.values() if not x.isSpaceFilling)
		if ('phoenix' in wx.PlatformInfo):
			freeSpace = max(0, self.GetClientSize()[0] - totalFixedWidth)
		else:
			freeSpace = max(0, self.GetClientSizeTuple()[0] - totalFixedWidth)

		# Calculate the total number of slices the free space will be divided into
		totalProportion = sum(x.freeSpaceProportion for x in self.columns.values() if x.isSpaceFilling)

		# Space filling columns that would escape their boundary conditions are treated as fixed size columns
		columnsToResize = []
		for i, col in self.columns.items():
			if (col.isSpaceFilling):
				newWidth = freeSpace * col.freeSpaceProportion / totalProportion
				boundedWidth = col.CalcBoundedWidth(newWidth)
				if (newWidth == boundedWidth):
					columnsToResize.append(col)
				else:
					freeSpace -= boundedWidth
					totalProportion -= col.freeSpaceProportion
					if (col.column.GetWidth() != boundedWidth):
						col.column.SetWidth(boundedWidth)

		# Finally, give each remaining space filling column a proportion of the free space
		for col in columnsToResize:
			newWidth = freeSpace * col.freeSpaceProportion / totalProportion
			boundedWidth = col.CalcBoundedWidth(newWidth)
			if (col.column.GetWidth() != boundedWidth):
				col.column.SetWidth(boundedWidth)

	# --------------------------------------------------------------#000000#FFFFFF
	# Commands

	def InReportView(self):
		return True

	def ClearAll(self):
		self.modelObjects = []
		self.model.Cleared()

	def AddObject(self, modelObject):
		"""
		Add the given object to our collection of objects.

		The object will appear at its sorted location, or at the end of the list if
		the list is unsorted
		"""
		self.AddObjects([modelObject])

	def AddObjects(self, modelObjects, preserveExpansion = True):
		"""
		Add the given collections of objects to our collection of objects.

		The objects will appear at their sorted locations, or at the end of the list if
		the list is unsorted
		"""

		try:
			self.Freeze()
			self.modelObjects.extend(modelObjects)
			self.RebuildGroups(preserveExpansion = preserveExpansion)
			self.model.ItemsAdded(None, modelObjects)
		finally:
			pass
			self.Thaw()

		if (self.showGroups):
			#Groups not updating children correctly, but rebuilding it all over again fixes it
			#TO DO: Fix self.model.ItemsAdded for groups
			self.model.Cleared()

	def EnsureVisible(self, modelObject, column = None):
		"""
		Make sure the user can see the given model object.
		"""

		item = self.model.ObjectToItem(modelObject)

		if (column != None):
			column = self.columns[column].column

		super().EnsureVisible(item, column = column)

	def RepopulateList(self):
		"""
		Completely rebuild the contents of the list control
		"""
		_log("@DataObjectListView.RepopulateList")

		self.model.Cleared()

		#Ensure expansion matches our model
		# for group in self.groups:
		# 	item = self.model.ObjectToItem(group)
		# 	if (self.IsExpanded(item) != group.IsExpanded()):
		# 		if (group.IsExpanded()):
		# 			super().Expand(item)
		# 		else:
		# 			super().Collapse(item)

		# Auto-resize once all the data has been added
		# self.AutoSizeColumns()

	#-------------------------------------------------------------------------
	# Building

	def RebuildGroups(self, preserveExpansion = True):
		"""
		Completely rebuild our groups from our current list of model objects.

		Only use this if SetObjects() has been called. If you have specifically created
		your groups and called SetGroups(), do not use this method.
		"""
		_log("@DataObjectListView.RebuildGroups")
		if (not self.showGroups):
			return

		groups = self._BuildGroups(preserveExpansion = preserveExpansion)
		# self.SortGroups(groups)
		self._SetGroups(groups)

	def _SetGroups(self, groups):
		"""
		Present the collection of DataListGroups in this control.
		"""
		_log("@DataObjectListView._SetGroups", groups)
		self.groups = groups
		self.RepopulateList()

	def _BuildGroups(self, modelObjects = None, preserveExpansion = True):
		"""
		Partition the given list of objects into DataListGroups depending on the given groupBy column.

		Returns the created collection of DataListGroups
		"""
		_log("@DataObjectListView._BuildGroups", modelObjects)
		if (modelObjects is None):
			modelObjects = self.modelObjects
		if (self.filter):
			modelObjects = self.filter(modelObjects)

		if (preserveExpansion):
			expanded = {}
			for group in self.groups:
				expanded[group.key] = group.IsExpanded()

		groupingColumn = self.GetGroupByColumn()

		groupMap = {}
		for model in modelObjects:
			key = groupingColumn.GetGroupKey(model)
			group = groupMap.get(key)
			if (group is None):
				group = DataListGroup(self, key, groupingColumn.GetGroupKeyAsString(key))
				groupMap[key] = group
			group.Add(model)

		for key in self.emptyGroups:
			group = groupMap.get(key)
			if (group is None):
				groupMap[key] = DataListEmptyGroup(self, key, groupingColumn.GetGroupKeyAsString(key))

		#Not working Yet. super().Expand(item) does not expand the item.
		#TO DO: Find out why
		if (preserveExpansion):
			for key, isExpanded in expanded.items():
				group = groupMap.get(key)
				if (group is not None):
					group.Expand(isExpanded)

					# if (isExpanded):
					# 	super().Expand(self.model.ObjectToItem(group))
					# else:
					# 	super().Collapse(self.model.ObjectToItem(group))

		groups = groupMap.values()

		if (self.GetShowItemCounts()):
			self._BuildGroupTitles(groups, groupingColumn)

		# Let the world know that we are creating the given groups
		event = DOLVEvent.GroupCreationEvent(self, groups)
		self.GetEventHandler().ProcessEvent(event)

		return event.groups

	def _BuildGroupTitles(self, groups, groupingColumn):
		"""
		Rebuild the titles of the given groups
		"""
		_log("@DataObjectListView._BuildGroupTitles", groups, groupingColumn)
		for x in groups:
			x.title = groupingColumn.GetGroupTitle(x, self.GetShowItemCounts())

	# def _BuildInnerList(self):
	# 	"""
	# 	Build the list that will be used to populate the ListCtrl.

	# 	This internal list is an amalgum of model objects, DataListGroups
	# 	and None (which are blank rows).
	# 	"""
	# 	_log("@DataObjectListView._BuildInnerList")
	# 	self.objectToIndexMap = None
	# 	if not self.showGroups:
	# 		return ObjectListView._BuildInnerList(self)

	# 	if not self.modelObjects:
	# 		self.groups = list()
	# 		self.innerList = list()
	# 		return

	# 	if self.groups is None:
	# 		self.groups = self._BuildGroups()
	# 		self.SortGroups()

	# 	self.innerList = list()
	# 	for grp in self.groups:
	# 		if len(self.innerList) and self.putBlankLineBetweenGroups:
	# 			self.innerList.append(None)
	# 		self.innerList.append(grp)
	# 		if grp.IsExpanded():
	# 			self.innerList.extend(grp.modelObjects)

	# ---Sorting-------------------------------------------------------#000000#FFFFFF

	def EnableSorting(self, column = None, state = True):
		"""
		Enable automatic sorting when the user clicks on a column title
		If *column* is None, applies to all columns.
		"""
		_log("@DataObjectListView.EnableSorting")
		if (column != None):
			self.columns[column].SetSortable(state)
		else:
			for column in self.columns.values():
				column.SetSortable(state)

	def DisableSorting(self, column = None, state = True):
		"""
		Disable automatic sorting when the user clicks on a column title
		If *column* is None, applies to all columns.
		"""

		_log("@DataObjectListView.DisableSorting")
		self.EnableSorting(column = column, state = not state)

	def SortBy(self, newColumnIndex, ascending = True):
		"""
		Sort the items by the given column
		"""
		_log("@DataObjectListView.SortBy", newColumnIndex, ascending)
		self.SetSortColumn(newColumnIndex, ascending = ascending, resortNow = True)

	def GetSortColumn(self, returnIndex = False):
		"""
		Return the column by which the rows of this control should be sorted
		"""

		column = self.GetSortingColumn()
		if (column != None):
			index = column.GetModelColumn()
			if (returnIndex):
				return index
			return self.columns[index]
		else:
			index = -1
			if (returnIndex):
				return index

	def SetSortColumn(self, column, ascending = True, resortNow = False, unsortOnNone = True):
		"""
		Set the column by which the rows should be sorted.

		'column' can be None (which makes the list be unsorted), a ColumnDefn,
		or the index of the column desired
		*unsortOnNone* determines if the list unsorts itself when *column* is None.
		"""
		if (column is None):
			index = -1
		elif (isinstance(column, DataColumnDefn)):
			try:
				index = [key for key, value in self.columns.items() if (value is column)][0]
			except IndexError:
				index = -1
		else:
			index = column

		if (index != -1):
			self.columns[index].column.SetSortOrder(ascending) #`SetSortOrder` indicates that this column is currently used for sorting the control and also sets the sorting direction
		else:
			item = self.GetSortingColumn()
			if (item != None):
				item.UnsetAsSortKey() #`UnsetAsSortKey` is the reverse of SetSortOrder and is called to indicate that this column is not used for sorting any longer.
				if (unsortOnNone):
					self.model.Cleared()
		
		if (resortNow):
			self.model.Resort()

	def SetCompareFunction(self, function):
		"""
		Allows the user to use a different compare function for sorting items.

		The comparison function must accept two model objects as two parameters, the column it is in as another, and if the order is ascending as one more.
		ie: myCompare(item1, item2, column, ascending)
		The comparison function should return negative, null or positive value depending on whether the first item is less than, equal to or greater than the second one.
		"""
		self.compareFunction = function

	def SetGroupCompareFunction(self, function):
		"""
		Allows the user to use a different compare function for sorting groups.

		The comparison function must accept two DataListGroup objects as two parameters, the column it is in as another, and if the order is ascending as one more.
		ie: myCompare(item1, item2, column, ascending)
		The comparison function should return negative, null or positive value depending on whether the first item is less than, equal to or greater than the second one.
		"""
		self.groupCompareFunction = function

	#Editing
	# def _PossibleStartCellEdit(self, rowIndex, subItemIndex):
	# 	"""
	# 	Start an edit operation on the given cell after performing some sanity checks
	# 	"""
	# 	return
	# 	# if 0 > rowIndex >= self.GetItemCount():
	# 	# 	return

	# 	# if 0 > subItemIndex >= self.GetColumnCount():
	# 	# 	return

	# 	# if self.cellEditMode == self.CELLEDIT_NONE:
	# 	# 	return

	# 	# if not self.columns[subItemIndex].isEditable:
	# 	# 	return

	# 	# if self.GetObjectAt(rowIndex) is None:
	# 	# 	return

	# 	# self.StartCellEdit(rowIndex, subItemIndex)

	# def _PossibleFinishCellEdit(self):
	# 	"""
	# 	If a cell is being edited, finish and commit an edit operation on the given cell.
	# 	"""
	# 	return
	# 	# if self.IsCellEditing():
	# 	# 	self.FinishCellEdit()

	# def _PossibleCancelCellEdit(self):
	# 	"""
	# 	If a cell is being edited, cancel the edit operation.
	# 	"""
	# 	return
	# 	# if self.IsCellEditing():
	# 	# 	self.CancelCellEdit()

	#-------------------------------------------------------------------------
	# Calculating

	# def GetSubItemRect(self, rowIndex, subItemIndex, flag):
	# 	"""
	# 	Poor mans replacement for missing wxWindows method.

	# 	The rect returned takes scroll position into account, so negative x and y are
	# 	possible.
	# 	"""
	# 	_log("@DataObjectListView.GetSubItemRect", rowIndex, subItemIndex, flag)
	# 	# Linux doesn't handle wx.LIST_RECT_LABEL flag. So we always get
	# 	# the whole bounds then par it down to the cell we want
	# 	rect = self.GetItemRect(rowIndex, wx.LIST_RECT_BOUNDS)

	# 	if (self.InReportView()):
	# 		rect = [0 - self.GetScrollPos( wx.HORIZONTAL),
	# 			rect.Y,
	# 			0,
	# 			rect.Height]
	# 		for i in range(subItemIndex + 1):
	# 			rect[0] += rect[2]
	# 			rect[2] = self.GetColumnWidth(i)

	# 	# If we want only the label rect for sub items, we have to manually
	# 	# adjust for any image the subitem might have
	# 	if flag == wx.LIST_RECT_LABEL:
	# 		lvi = self.GetItem(rowIndex, subItemIndex)
	# 		if (lvi.GetImage() != -1):
	# 			if( self.HasFlag(wx.LC_ICON)):
	# 				imageWidth = self.normalImageList.GetSize(0)[0]
	# 				rect[1] += imageWidth
	# 				rect[3] -= imageWidth
	# 			else:
	# 				imageWidth = self.smallImageList.GetSize(0)[0] + 1
	# 				rect[0] += imageWidth
	# 				rect[2] -= imageWidth

	# 	# log "rect=%s" % rect
	# 	return rect

	# def HitTestSubItem(self, pt):
	# 	"""
	# 	Return a tuple indicating which (item, subItem) the given pt (client coordinates) is over.

	# 	This uses the buildin version on Windows, and poor mans replacement on other platforms.
	# 	"""
	# 	_log("@DataObjectListView.HitTestSubItem", pt)
	# 	# The buildin version works on Windows
	# 	if (wx.Platform == "__WXMSW__"):
	# 		return wx.ListCtrl.HitTestSubItem(self, pt)

	# 	(rowIndex, flags) = self.HitTest(pt)

	# 	# Did the point hit any item?
	# 	if (flags & wx.LIST_HITTEST_ONITEM) == 0:
	# 		return (-1, 0, -1)

	# 	# If it did hit an item and we are not in report mode, it must be the
	# 	# primary cell
	# 	if (not self.InReportView()):
	# 		return (rowIndex, wx.LIST_HITTEST_ONITEM, 0)

	# 	# Find which subitem is hit
	# 	right = 0
	# 	scrolledX = self.GetScrollPos(wx.HORIZONTAL) + pt.x
	# 	for i, col in self.columns.items():
	# 		left = right
	# 		right += col.column.GetWidth()
	# 		if (scrolledX < right):
	# 			flag = wx.LIST_HITTEST_ONITEMLABEL
	# 			# if (scrolledX - left) < self.smallImageList.GetSize(0)[0]:
	# 			# 	flag = wx.LIST_HITTEST_ONITEMICON
	# 			# else:
	# 			# 	flag = wx.LIST_HITTEST_ONITEMLABEL
	# 			return (rowIndex, flag, i)

	# 	return (rowIndex, 0, -1)


	# ----------------------------------------------------------------------
	# Utilities

	# def _IsPrintable(self, char):
	# 	"""
	# 	Check if char is printable using unicodedata as string.isPrintable
	# 	is only available in Py3.
	# 	"""
	# 	cat = unicodedata.category(char)
	# 	if cat[0] == "L":
	# 		return True
	# 	else:
	# 		return False

	# #-------------------------------------------------------------------------
	# # Event handling

	def _HandleColumnClick(self, event):
		"""
		The user has clicked on a column title.
		Sorts by ascending, descending, then unsorted.
		"""

		column = event.GetDataViewColumn()

		if ((not self.GetSortingColumn()) or (column.IsSortOrderAscending())):
			event.Skip()
		else:
			column.UnsetAsSortKey() #`UnsetAsSortKey` is the reverse of SetSortOrder and is called to indicate that this column is not used for sorting any longer.
			self.model.Cleared()

	def _HandleSize(self, event):
		"""
		The ListView is being resized
		"""
		_log("@DataObjectListView._HandleSize")
		# self._PossibleFinishCellEdit()
		event.Skip()
		self._ResizeSpaceFillingColumns()

	def _HandleOverlays(self, event):
		"""
		Draws all overlays on top of the DataList.
		"""

		def drawEmptyList(item):
			"""
			Draws the empty list message."""

			self.overlayEmptyListMsg.Reset()
			
			dc = wx.ClientDC(item)
			odc = wx.DCOverlay(self.overlayEmptyListMsg, dc)
			odc.Clear()

			if ('wxMac' not in wx.PlatformInfo):
				dc = wx.GCDC(dc) #Mac's DC is already the same as a GCDC

			size = item.GetClientSize()
			_drawText(dc, text = self.emptyListMsg, rectangle = wx.Rect(0, 0, size[0], size[1]), align = "center", color = wx.LIGHT_GREY, font = self.emptyListFont)

			del odc  # Make sure the odc is destroyed before the dc is.

		if (not self.modelObjects):
			wx.CallAfter(drawEmptyList, event.GetEventObject())
		event.Skip()

	#Event Relays
	def _getRelayInfo(self, relayEvent):
		kwargs = {}
		try:
			column = relayEvent.GetDataViewColumn()
			kwargs["index"] = column.GetModelColumn()
			kwargs["column"] = self.columns.get(kwargs["index"], None)
			if (not self.GetSortingColumn()):
				kwargs["ascending"] = None
			else:
				kwargs["ascending"] = column.IsSortOrderAscending()
		except AttributeError as error:
			kwargs["index"] = None
			kwargs["column"] = None
			kwargs["ascending"] = None

		try:
			kwargs["row"] = relayEvent.GetModel().ItemToObject(relayEvent.GetItem())
		except TypeError:
			kwargs["row"] = None
		kwargs["position"] = relayEvent.GetPosition()
		kwargs["value"] = relayEvent.GetValue()
		kwargs["editCanceled"] = relayEvent.IsEditCancelled()

		# print("@6", kwargs)
		return kwargs

	def TriggerEvent(self, eventFunction, **kwargs):
		"""
		Allows the user to easily trigger an event remotely.

		Example Use: myOLV.TriggerEvent(ObjectListView.SelectionChangedEvent, row = newItem)
		"""

		newEvent = eventFunction(self, **kwargs)
		self.GetEventHandler().ProcessEvent(newEvent)
		if (isinstance(newEvent, DOLVEvent.VetoableEvent)):
			if (newEvent.IsVetoed()):
				eventFrom.Veto()
				return
		return True
		eventFrom.Skip()

	def _RelayEvent(self, eventFrom, eventTo):
		if (self.TriggerEvent(eventTo, **self._getRelayInfo(eventFrom))):
			eventFrom.Skip()

		# event = eventTo(self, **self._getRelayInfo(eventFrom))
		# self.GetEventHandler().ProcessEvent(event)
		# if (isinstance(event, DOLVEvent.VetoableEvent)):
		# 	if (event.IsVetoed()):
		# 		return
		# eventFrom.Skip()

	def _RelaySelectionChanged(self, relayEvent):
		#Do not fire this event if that row is already selecetd
		row = relayEvent.GetModel().ItemToObject(relayEvent.GetItem())
		if (row != self.lastSelected):
			self.lastSelected = row
			if (isinstance(row, DataListGroup)):
				self._RelayEvent(relayEvent, DOLVEvent.GroupSelectedEvent)
			else:
				self._RelayEvent(relayEvent, DOLVEvent.SelectionChangedEvent)
		else:
			relayEvent.Skip()

	def _RelayCellContextMenu(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.CellContextMenuEvent)

	def _RelayCellActivated(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.CellActivatedEvent)

	def _RelayColumnHeaderClick(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.ColumnHeaderClickEvent)

	def _RelayColumnHeaderRightClick(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.ColumnHeaderRightClickEvent)

	def _RelaySorted(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.SortedEvent)

	def _RelayReorder(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.ReorderEvent)

	def _RelayCollapsing(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.CollapsingEvent)

	def _RelayCollapsed(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.CollapsedEvent)

	def _RelayExpanding(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.ExpandingEvent)

	def _RelayExpanded(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.ExpandedEvent)

	def _RelayEditCellStarting(self, relayEvent):
		#Do not start editing non-editable columns
		if (not self.columns[relayEvent.GetDataViewColumn().GetModelColumn()].isEditable):
			relayEvent.Veto()
		else:
			self._RelayEvent(relayEvent, DOLVEvent.EditCellStartingEvent)

	def _RelayEditCellStarted(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.EditCellStartedEvent)

	def _RelayEditCellFinishing(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.EditCellFinishingEvent)

	def _RelayEditCellFinished(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.EditCellFinishedEvent)

class DataListGroup(object):
	"""
	A DataListGroup is a partition of model objects that can be presented
	under a collapsible heading in a GroupListView.
	"""

	def __init__(self, olv, key, title):
		self.olv = olv
		self.key = key
		self.title = title

		self.modelObjects = list()

	def Add(self, model):
		"""
		Add the given model to those that belong to this group.
		"""
		self.modelObjects.append(model)

	def IsExpanded(self):
		"""
		Returns if this group is expaned or not.
		"""
		return self.olv.IsExpanded(self.olv.model.ObjectToItem(self))

	def Expand(self, state = True):
		"""
		Expands the group if *state* is True, otherwise collapses it.
		"""
		if (state):
			self.olv.Expand(self)
			# wx.dataview.DataViewCtrl.Expand(self.olv, self.olv.model.ObjectToItem(self))
		else:
			self.olv.Collapse(self)
			# wx.dataview.DataViewCtrl.Collapse(self.olv, self.olv.model.ObjectToItem(self))

class DataListEmptyGroup(DataListGroup):
	"""A list group that is empty."""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

class DataColumnDefn(object):
	"""
	An atempt to recreate ObjectListView using a DataViewCtrl. Use at your own risk.

	* sortGetter
		What is used insted of *valueGetter* to get the value that should be sorted for items
	
	* groupSortGetter
		What is used insted of *groupKeyGetter* to get the value that should be sorted for groups

	* renderer
		What is used to render items in this column. This can be one of your own, or one of the included ones.
		If None: The default renderer for a wxListItem will be used.
	"""

	def __init__(
			self,
			title="title",
			align="left",
			width=-1,
			valueGetter=None,
			sortGetter=None,
			imageGetter=None,
			stringConverter=None,
			valueSetter=None,
			isSortable=True,
			isEditable=True,
			isReorderable=True,
			isResizeable=True,
			isHidden=False,
			fixedWidth=None,
			minimumWidth=-1,
			maximumWidth=-1,
			isSpaceFilling=False,
			cellEditorCreator=None,
			autoCompleteCellEditor=False,
			autoCompleteComboBoxCellEditor=False,
			checkStateGetter=None,
			checkStateSetter=None,
			isSearchable=True,
			useBinarySearch=None,
			headerImage=-1,
			groupKeyGetter=None,
			groupKeyConverter=None,
			groupSortGetter=None,
			useInitialLetterForGroupKey=False,
			groupTitleSingleItem=None,
			groupTitlePluralItems=None,
			renderer=None,
			rendererArgs=[],
			rendererKwargs={}):
		"""
		Create a new ColumnDefn using the given attributes.
		"""
		_log("@DataColumnDefn.__init__")
		self.title = title
		self.align = align
		self.column = None
		self.valueGetter = valueGetter
		self.sortGetter = sortGetter
		self.imageGetter = imageGetter
		self.stringConverter = stringConverter
		self.valueSetter = valueSetter
		self.isSpaceFilling = isSpaceFilling
		self.cellEditorCreator = cellEditorCreator
		self.freeSpaceProportion = 1
		self.isEditable = isEditable
		self.isSortable = isSortable
		self.isReorderable = isReorderable
		self.isResizeable = isResizeable
		self.isHidden = isHidden
		self.isSearchable = isSearchable
		self.useBinarySearch = useBinarySearch
		self.headerImage = headerImage
		self.groupKeyGetter = groupKeyGetter
		self.groupSortGetter = groupSortGetter
		self.groupKeyConverter = groupKeyConverter
		self.useInitialLetterForGroupKey = useInitialLetterForGroupKey
		self.groupTitleSingleItem = groupTitleSingleItem or "%(title)s (%(count)d item)"
		self.groupTitlePluralItems = groupTitlePluralItems or "%(title)s (%(count)d items)"
		# was this column created internally by ObjectListView?
		self.isInternal = False
		self._EventHandler = None

		self.minimumWidth = minimumWidth
		self.maximumWidth = maximumWidth
		self.width = self.CalcBoundedWidth(width)

		if fixedWidth is not None:
			self.SetFixedWidth(fixedWidth)

		if autoCompleteCellEditor:
			self.cellEditorCreator = lambda olv, row, col: CellEditor.MakeAutoCompleteTextBox(
				olv, col)

		if autoCompleteComboBoxCellEditor:
			self.cellEditorCreator = lambda olv, row, col: CellEditor.MakeAutoCompleteComboBox(
				olv, col)

		self.checkStateGetter = checkStateGetter
		self.checkStateSetter = checkStateSetter

		self.SetRenderer(renderer, *rendererArgs, **rendererKwargs)

	#-------------------------------------------------------------------------
	# Column properties

	def RefreshColumn(self):
		"""
		Updates the column in the model with this one.
		"""

		if (self.column and self.column.GetOwner()):
			olv = self.column.GetOwner()
			index = self.column.GetModelColumn()

			#Delete the column, then put it back in
			olv.DeleteColumn(self.column)
			self.SetRenderer(self.renderer.type, refreshColumn = False) #Renderer gets destroyed, so remake it

			self.column = wx.dataview.DataViewColumn(self.title, self.renderer, index, width = self.width, align = self.GetAlignment())
			olv.InsertColumn(index, self.column)

	def GetWidth(self):
		"""
		Return the width of the column.
		"""
		_log("@DataColumnDefn.GetWidth")
		return self.column.GetWidth()

	def SetWidth(self, width = None):
		"""
		Change the width of the column.
		If 'width' is None, it will auto-size.
		"""
		_log("@DataColumnDefn.SetWidth", width)
		if (width == None):
			width = wx.LIST_AUTOSIZE

		return self.column.SetWidth(width)

	def GetAlignment(self):
		"""
		Return the alignment that this column uses
		"""
		_log("@DataColumnDefn.GetAlignment")
		#https://wxpython.org/Phoenix/docs/html/wx.Alignment.enumeration.html
		alignment = {
			None: wx.ALIGN_NOT,
			
			"l": wx.ALIGN_LEFT,
			"r": wx.ALIGN_RIGHT,
			"t": wx.ALIGN_TOP,
			"b": wx.ALIGN_BOTTOM,
		   
			"c": wx.ALIGN_CENTER,
			"h": wx.ALIGN_CENTER_HORIZONTAL,
			"v": wx.ALIGN_CENTER_VERTICAL,
		}.get(self.align[:1], wx.ALIGN_LEFT)

		return alignment

	def SetSortable(self, state = None):
		if (state is not None):
			self.isSortable = state

		self.column.SetSortable(self.isSortable)

	def GetSortable():
		return self.column.GetSortable()

	def SetEditable(self, state = None):
		if (state is not None):
			self.isEditable = state

		if (self.isEditable):
			key = "edit"
		else:
			key = "nonEdit"

		self.SetRenderer(self.renderer.Clone(mode = rendererCatalogue[self.renderer.type][key]))

	def GetEditable():
		return self.renderer.Mode == rendererCatalogue[self.renderer.type]["edit"]

	def SetReorderable(self, state = None):
		if (state is not None):
			self.isReorderable = state

		self.column.SetReorderable(self.isReorderable)

	def GetReorderable():
		return self.column.GetReorderable()

	def SetResizeable(self, state = None):
		if (state is not None):
			self.isResizeable = state

		self.column.SetResizeable(self.isResizeable)

	def GetResizeable():
		return self.column.GetResizeable()

	def SetHidden(self, state = None):
		if (state is not None):
			self.isHidden = state

		self.column.SetHidden(self.isHidden)

	def GetHidden():
		return self.column.GetHidden()


	#-------------------------------------------------------------------------
	# Value accessing

	def GetValue(self, modelObject):
		"""
		Return the value for this column from the given modelObject
		"""
		_log("@DataColumnDefn.GetValue", modelObject)
		return self._Munge(modelObject, self.valueGetter)

	def GetStringValue(self, modelObject):
		"""
		Return a string representation of the value for this column from the given modelObject
		"""
		value = self.GetValue(modelObject)
		return self._StringToValue(value, self.stringConverter)

	def _StringToValue(self, value, converter):
		"""
		Convert the given value to a string, using the given converter
		"""
		try:
			return converter(value)
		except TypeError:
			pass

		if converter and isinstance(
			value,
			(datetime.datetime,
			 datetime.date,
			 datetime.time)):
			return value.strftime(self.stringConverter)

		if converter and isinstance(value, wx.DateTime):
			return value.Format(self.stringConverter)

		# By default, None is changed to an empty string.
		if not converter and not value:
			return ""

		fmt = converter or "%s"
		try:
			return fmt % value
		except UnicodeError:
			return unicode(fmt) % value

	def GetGroupKey(self, modelObject):
		"""
		Return the group key for this column from the given modelObject
		"""
		if self.groupKeyGetter is None:
			key = self.GetValue(modelObject)
		else:
			key = self._Munge(modelObject, self.groupKeyGetter)
		if self.useInitialLetterForGroupKey:
			try:
				return key[:1].upper()
			except TypeError:
				return key
		else:
			return key

	def GetGroupKeyAsString(self, groupKey):
		"""
		Return the given group key as a human readable string
		"""
		# If there is no group key getter, we must have the normal aspect value. So if
		# there isn't a special key converter, use the normal aspect to string
		# converter.
		if self.groupKeyGetter is None and self.groupKeyConverter is None:
			return self._StringToValue(groupKey, self.stringConverter)
		else:
			return self._StringToValue(groupKey, self.groupKeyConverter)

	def GetGroupTitle(self, group, useItemCount):
		"""
		Return a title of the group
		"""
		title = self.GetGroupKeyAsString(group.key)
		if useItemCount:
			objectCount = len(group.modelObjects)
			if objectCount == 1:
				fmt = self.groupTitleSingleItem
			else:
				fmt = self.groupTitlePluralItems
			title = fmt % {"title": title, "count": objectCount}
		return title
	
	def SetValue(self, modelObject, value):
		"""
		Set this columns aspect of the given modelObject to have the given value.
		"""
		_log("@DataColumnDefn.SetValue", modelObject, value)
		if self.valueSetter is None:
			return self._SetValueUsingMunger(
				modelObject,
				value,
				self.valueGetter,
				False)
		else:
			return self._SetValueUsingMunger(
				modelObject,
				value,
				self.valueSetter,
				True)

	def _SetValueUsingMunger(
			self,
			modelObject,
			value,
			munger,
			shouldInvokeCallable):
		"""
		Look for ways to update modelObject with value using munger. If munger finds a
		callable, it will be called if shouldInvokeCallable == True.
		"""
		# If there isn't a munger, we can't do anything
		if munger is None:
			return

		# Is munger a function?
		if callable(munger):
			if shouldInvokeCallable:
				munger(modelObject, value)
			return

		# Try indexed access for dictionary or list like objects
		try:
			modelObject[munger] = value
			return
		except:
			pass

		# Is munger the name of some slot in the modelObject?
		try:
			attr = getattr(modelObject, munger)
		except TypeError:
			return
		except AttributeError:
			return

		# Is munger the name of a method?
		if callable(attr):
			if shouldInvokeCallable:
				attr(value)
			return

		# If we get to here, it seems that munger is the name of an attribute or
		# property on modelObject. Try to set, realising that many things could
		# still go wrong.
		try:
			setattr(modelObject, munger, value)
		except:
			pass

	def _Munge(self, modelObject, munger):
		"""
		Wrest some value from the given modelObject using the munger.
		With a description like that, you know this method is going to be obscure :-)

		'munger' can be:

		1) a callable.
		   This method will return the result of executing 'munger' with 'modelObject' as its parameter.

		2) the name of an attribute of the modelObject.
		   If that attribute is callable, this method will return the result of executing that attribute.
		   Otherwise, this method will return the value of that attribute.

		3) an index (string or integer) onto the modelObject.
		   This allows dictionary-like objects and list-like objects to be used directly.
		"""
		if munger is None:
			return None

		# THINK: The following code treats an instance variable with the value of None
		# as if it doesn't exist. Is that best?

		# Try attribute access
		try:
			attr = getattr(modelObject, munger, None)
			if attr is not None:
				try:
					return attr()
				except TypeError:
					return attr
		except TypeError:
			# Happens when munger is not a string
			pass

		# Use the callable directly, if possible.
		# In accordance with Guido's rules for Python 3, we just call it and catch the
		# exception
		try:
			return munger(modelObject)
		except TypeError:
			pass

		# Try dictionary-like indexing
		try:
			return modelObject[munger]
		except:
			return None

	#-------------------------------------------------------------------------
	# Width management

	def CalcBoundedWidth(self, width):
		"""
		Calculate the given width bounded by the (optional) minimum and maximum column widths
		"""
		_log("@DataColumnDefn.CalcBoundedWidth", width)
		# Values of < 0 have special meanings, so just return them
		if width < 0:
			return width

		if self.maximumWidth >= 0:
			width = min(self.maximumWidth, width)
		return max(self.minimumWidth, width)

	#-------------------------------------------------------------------------
	# Renderer

	def GetRenderer(self):
		"""
		Returns the default renderer for this column
		"""
		_log("@DataColumnDefn.GetRenderer")
		return self.renderer

	def SetRenderer(self, renderer, *args, refreshColumn = True, **kwargs):
		"""
		Applies the provided renderer
		"""
		global rendererCatalogue
		_log("@DataColumnDefn.SetRenderer", renderer, args, kwargs)

		try:
			self.renderer = rendererCatalogue[renderer]["class"](*args, **kwargs)
		except (AttributeError, KeyError):
			#https://github.com/wxWidgets/Phoenix/blob/master/samples/dataview/CustomRenderer.py
			self.renderer = renderer

		if (refreshColumn):
			self.RefreshColumn()

#Utility Functions
def _log(*data):
	pass
# 	with open("log.txt", "a") as f:
# 		f.write(f"{', '.join([f'{item}' for item in data])}\n")
# open('log.txt', 'w').close()

def printCurrentTrace(printout = True):
	"""Prints out the stack trace for the current place in the program.
	Modified Code from codeasone on https://stackoverflow.com/questions/1032813/dump-stacktraces-of-all-active-threads

	Example Input: printCurrentTrace()
	"""

	import sys
	import traceback
	code = []
	for threadId, stack in sys._current_frames().items():
		code.append("\n# ThreadID: %s" % threadId)
		for filename, lineno, name, line in traceback.extract_stack(stack):
			code.append('File: "%s", line %d, in %s' % (filename,
														lineno, name))
			if line:
				code.append("  %s" % (line.strip()))

	if (printout):
		for line in code:
			print (line)
		sys.exit()
	else:
		return code

def _StringToValue(value, converter):
	"""
	Convert the given value to a string, using the given converter
	"""
	try:
		return converter(value)
	except TypeError:
		pass

	if (converter and isinstance(value, (datetime.datetime, datetime.date, datetime.time))):
		return value.strftime(converter)

	if (converter and isinstance(value, wx.DateTime)):
		return value.Format(converter)

	# By default, None is changed to an empty string.
	if ((not converter) and (not value)):
		return ""

	fmt = converter or "%s"
	try:
		return fmt % value
	except UnicodeError:
		return unicode(fmt) % value

def _SetValueUsingMunger(modelObject, value, munger, shouldInvokeCallable):
	"""
	Look for ways to update modelObject with value using munger. If munger finds a
	callable, it will be called if shouldInvokeCallable == True.
	"""
	# If there isn't a munger, we can't do anything
	if (munger is None):
		return

	# Is munger a function?
	if (callable(munger)):
		if (shouldInvokeCallable):
			munger(modelObject, value)
		return

	# Try indexed access for dictionary or list like objects
	try:
		modelObject[munger] = value
		return
	except:
		pass

	# Is munger the name of some slot in the modelObject?
	try:
		attr = getattr(modelObject, munger)
	except TypeError:
		return
	except AttributeError:
		return

	# Is munger the name of a method?
	if (callable(attr)):
		if (shouldInvokeCallable):
			attr(value)
		return

	# If we get to here, it seems that munger is the name of an attribute or
	# property on modelObject. Try to set, realising that many things could
	# still go wrong.
	try:
		setattr(modelObject, munger, value)
	except:
		pass

def _Munge(modelObject, munger):
	"""
	Wrest some value from the given modelObject using the munger.
	With a description like that, you know this method is going to be obscure :-)

	'munger' can be:

	1) a callable.
	   This method will return the result of executing 'munger' with 'modelObject' as its parameter.

	2) the name of an attribute of the modelObject.
	   If that attribute is callable, this method will return the result of executing that attribute.
	   Otherwise, this method will return the value of that attribute.

	3) an index (string or integer) onto the modelObject.
	   This allows dictionary-like objects and list-like objects to be used directly.
	"""
	if (munger is None):
		return None

	# THINK: The following code treats an instance variable with the value of None
	# as if it doesn't exist. Is that best?

	# Try attribute access
	try:
		attr = getattr(modelObject, munger, None)
		if (attr is not None):
			try:
				return attr()
			except TypeError:
				return attr
	except TypeError:
		# Happens when munger is not a string
		pass

	# Use the callable directly, if possible.
	# In accordance with Guido's rules for Python 3, we just call it and catch the
	# exception
	try:
		return munger(modelObject)
	except TypeError:
		pass

	# Try dictionary-like indexing
	try:
		return modelObject[munger]
	except:
		return None

def _drawText(dc, rectangle = wx.Rect(0, 0, 100, 100), text = "", isSelected = False, x_offset = 0, y_offset = 0, align = None, color = None, font = None):
	"""Draw a simple text label in appropriate colors.
	Special thanks to Milan Skala for how to center text on http://wxpython-users.1045709.n5.nabble.com/Draw-text-over-an-existing-bitmap-td5725527.html

	align (str) - Where the text should be aligned in the cell
		~ "left", "right", "center"
		- If None: No alignment will be done

	Example Input: _drawText(dc, rectangle, text, isSelected)
	Example Input: _drawText(dc, rectangle, text, isSelected, align = "left", color = textColor)
	"""

	oldColor = dc.GetTextForeground()
	oldFont = dc.GetFont()
	try:
		if (color != None):
			color = tuple(min(255, max(0, item)) for item in color) #Ensure numbers are between 0 and 255
		else:
			if (isSelected):
				#Use: https://wxpython.org/Phoenix/docs/html/wx.SystemColour.enumeration.html
				color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
				# color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
			else:
				color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
		dc.SetTextForeground(color)

		if (font != None):
			dc.SetFont(font)

		if (align == None):
			x_align = 0
			y_align = 0
		else:
			width, height = dc.GetTextExtent(text)
			y_align = (rectangle.height - height) / 2
		
			if (align.lower()[0] == "l"):
				x_align = 0
			elif (align.lower()[0] == "r"):
				x_align = rectangle.width - width
			else:
				x_align = (rectangle.width - width) / 2

		dc.DrawText(text, rectangle.x + x_offset + x_align, rectangle.y + y_offset + y_align)
	finally:
		dc.SetFont(oldFont)
		dc.SetTextForeground(oldColor)

def _drawBackground(dc, rectangle, isSelected, color = None):
	"""Draw an appropriate background based on selection state.

	Example Input: _drawBackground(dc, rectangle, isSelected)
	Example Input: _drawBackground(dc, rectangle, isSelected, color = cellColor)"""

	oldPen = dc.GetPen()
	oldBrush = dc.GetBrush()

	try:
		if (color != None):
			color = tuple(min(255, max(0, item)) for item in color) #Ensure numbers are between 0 and 255
		else:
			if (isSelected):
				color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
			else:
				color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
		dc.SetBrush(wx.Brush(color, style = wx.SOLID))
	
		dc.SetPen(wx.TRANSPARENT_PEN)
		dc.DrawRectangle(rectangle.x, rectangle.y, rectangle.width, rectangle.height)
	finally:
		dc.SetPen(oldPen)
		dc.SetBrush(oldBrush)

def _drawButton(dc, rectangle, isSelected, fitTo = None, radius = 1, borderWidth = 1,
	x_offset = 0, y_offset = 0, width_offset = 0, height_offset = 0,
	x_align = None, y_align = None, color = None, borderColor = None):
	"""Draw a button in appropriate colors.
	If both 'x_align' and 'y_align' are None, no alignment will be done

	fitTo (str)   - Determines the initial width and height of the button
		- If str: Will use the size of the text if it were drawn
		- If None: Will use 'rectangle'

	x_align (str) - Where the button should be aligned with respect to the x-axis in the cell
		~ "left", "right", "center"
		- If None: Will use "center"

	y_align (str) - Where the button should be aligned with respect to the x-axis in the cell
		~ "top", "bottom", "center"
		- If None: Will use "center"

	Example Input: _drawButton(dc, rectangle, isSelected)
	Example Input: _drawButton(dc, rectangle, isSelected, x_align = "right", y_align = "top")
	Example Input: _drawButton(dc, rectangle, isSelected, x_align = "center", y_align = "center", width_offset = -10, height_offset = -10)
	Example Input: _drawButton(dc, rectangle, isSelected, fitTo = "Lorem Ipsum", width_offset = 6)
	"""

	oldPen = dc.GetPen()
	oldBrush = dc.GetBrush()

	try:
		if (color != None):
			color = tuple(min(255, max(0, item)) for item in color) #Ensure numbers are between 0 and 255
		else:
			if (isSelected):
				color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNHIGHLIGHT)
			else:
				color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
		dc.SetBrush(wx.Brush(color, style = wx.SOLID))

		if (borderColor != None):
			borderColor = tuple(min(255, max(0, item)) for item in borderColor) #Ensure numbers are between 0 and 255
		else:
			borderColor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNSHADOW)
		dc.SetPen(wx.Pen(borderColor, width = borderWidth, style = wx.SOLID))
		# dc.SetPen(wx.TRANSPARENT_PEN)

		if (fitTo == None):
			width = rectangle.width
			height = rectangle.height
		else:
			width, height = dc.GetTextExtent(fitTo)

		if ((x_align == None) and (y_align == None)):
			x_align = 0
			y_align = 0
		else:
			if (x_align == None):
				x_align = "center"
			elif (y_align == None):
				y_align = "center"

			if (x_align.lower()[0] == "l"):
				x_align = 0
			elif (x_align.lower()[0] == "r"):
				x_align = rectangle.width - (width + width_offset)
			else:
				x_align = (rectangle.width - (width + width_offset)) / 2

			if (y_align.lower()[0] == "t"):
				y_align = 0
			elif (y_align.lower()[0] == "b"):
				y_align = rectangle.height - (height + height_offset)
			else:
				y_align = (rectangle.height - (height + height_offset)) / 2

		dc.DrawRoundedRectangle(rectangle.x + x_align + x_offset, rectangle.y + y_align + y_offset, width + width_offset, height + height_offset, radius)
	finally:
		dc.SetPen(oldPen)
		dc.SetBrush(oldBrush)
		
def _clip(dc, rectangle):
	"""Setup the clipping rectangle"""
	
	dc.SetClippingRegion(rectangle.x, rectangle.y, rectangle.width, rectangle.height)

def _unclip(dc):
	"""Destroy the clipping rectangle"""
	
	dc.DestroyClippingRegion()

#Models
#https://github.com/wxWidgets/Phoenix/blob/master/samples/dataview/DataViewModel.py
class NormalListModel(wx.dataview.PyDataViewModel):
	"""Displays like an ObjectListView or GroupListView."""
	#https://wxpython.org/Phoenix/docs/html/wx.dataview.DataViewItemObjectMapper.html

	def __init__(self, olv):
		wx.dataview.PyDataViewModel.__init__(self)
		self.olv = olv
		self.colorCatalogue = {}

	#     # The PyDataViewModel derives from both DataViewModel and from
	#     # DataViewItemObjectMapper, which has methods that help associate
	#     # data view items with Python objects. Normally a dictionary is used
	#     # so any Python object can be used as data nodes. If the data nodes
	#     # are weak-referencable then the objmapper can use a
	#     # WeakValueDictionary instead.
		self.UseWeakRefs(True)

	def GetAttr(self, item, column, attribute):
		#Override this to indicate that the item has special font attributes.
		#The base class version always simply returns False.
		# _log("@model.GetAttr", item, column, attribute)
		# return super().GetAttr(item, column, attribute)

		changed = False
		node = self.ItemToObject(item)
		if (node in self.olv.colorOverride):
			attribute.SetBackgroundColour(self.olv.colorOverride[node])
		elif (node in self.colorCatalogue):
			attribute.SetBackgroundColour(self.colorCatalogue[node])

		if (isinstance(node, DataListGroup)):
			attribute.SetBold(self.olv.groupFont[0])
			attribute.SetItalic(self.olv.groupFont[1])
			attribute.SetColour(self.olv.groupFont[2])

		if (self.olv.rowFormatter is not None):
			self.olv.rowFormatter(item, node)

		if (changed):
			return True
		return False

	def GetChildren(self, parent, children):
		#Override this so the control can query the child items of an item.
		#Returns the number of items.
		_log("@model.GetChildren", parent, children, not parent)#, self.olv.modelObjects, self.olv.groups)

		def applyRowColor(rows):
			if (self.olv.useAlternateBackColors and self.olv.InReportView()):
				for index, row in enumerate(rows):
					#Determine row color outside of virtual function for speed
					if (index in self.olv.colorOverride):
						self.colorCatalogue[row] = self.olv.colorOverride[index]
					elif (index & 1):
						self.colorCatalogue[row] = self.olv.oddRowsBackColor
					else:
						self.colorCatalogue[row] = self.olv.evenRowsBackColor

		def applyGroupColor(group):
			if (self.olv.useAlternateBackColors and self.olv.InReportView()):
				if (self.olv.groupBackColor != None):
					if (index in self.olv.colorOverride):
						self.colorCatalogue[group] = self.olv.colorOverride[index]
					else:
						self.colorCatalogue[group] = self.olv.groupBackColor
				applyRowColor(group.modelObjects)

		# The view calls this method to find the children of any node in the
		# control. There is an implicit hidden root node, and the top level
		# item(s) should be reported as children of this node. A List view
		# simply provides all items as children of this hidden root. A Tree
		# view adds additional items as children of the other items, as needed,
		# to provide the tree hierachy.

		# If the parent item is invalid then it represents the hidden root
		# item, so we'll use the genre objects as its children and they will
		# end up being the collection of visible roots in our tree.
		if not parent:
			if (self.olv.showGroups):
				for group in self.olv.groups:
					applyGroupColor(group)
					children.append(self.ObjectToItem(group))
				return len(self.olv.groups)
			else:
				applyRowColor(self.olv.modelObjects)
				for row in self.olv.modelObjects:
					children.append(self.ObjectToItem(row))
				return len(self.olv.modelObjects)

		# Otherwise we'll fetch the python object associated with the parent
		# item and make DV items for each of it's child objects.
		node = self.ItemToObject(parent)
		_log("@model.GetChildren - node:", node)
		if isinstance(node, DataListGroup):
			applyGroupColor(node)
			applyRowColor(node.modelObjects)
			for row in node.modelObjects:
				children.append(self.ObjectToItem(row))
			_log("@model.GetChildren -", len(node.modelObjects))
			return len(node.modelObjects)
		_log("@model.GetChildren - None")
		return 0

	def GetParent(self, item):
		#Override this to indicate which wx.dataview.DataViewItem representing the parent of item 
		#or an invalid wx.dataview.DataViewItem if the root item is the parent item.
		_log("@model.GetParent", item)
		# Return the item which is this item's parent.

		if (not self.olv.showGroups):
			return wx.dataview.NullDataViewItem

		if (isinstance(item, wx.dataview.DataViewItem)):
			if (not item):
				return wx.dataview.NullDataViewItem
			node = self.ItemToObject(item)
		else:
			node = item

		if (isinstance(node, DataListGroup)):
			_log("@model.GetParent - Null 1")
			return wx.dataview.NullDataViewItem
		else:
			for group in self.olv.groups:
				if (node in group.modelObjects):
					_log("@model.GetParent -", group)
					return self.ObjectToItem(group)
			_log("@model.GetParent - Null 2")
			return wx.dataview.NullDataViewItem

	def GetValue(self, item, column, alternateGetter = None):
		#Override this to indicate the value of item.
		#A Variant is used to store the data.
		# _log("@model.GetValue", item, column)

		# Return the value to be displayed for this item and column. For this
		# example we'll just pull the values from the data objects we
		# associated with the items in GetChildren.

		# Fetch the data object for this item.
		node = self.ItemToObject(item)
		try:
			defn = self.olv.columns[column]
		except AttributeError:
			raise AttributeError(f"There is no column {column}")

		if (isinstance(node, DataListGroup)):
			return node.title

		if (alternateGetter):
			value = _Munge(node, alternateGetter)
		else:
			value = _Munge(node, defn.valueGetter)
		if (isinstance(defn.renderer, (wx.dataview.DataViewProgressRenderer, wx.dataview.DataViewSpinRenderer, Renderer_Spin, Renderer_Bmp, 
			wx.dataview.DataViewBitmapRenderer, wx.dataview.DataViewToggleRenderer, Renderer_Button, Renderer_Progress))):
				return value
		
		elif (isinstance(defn.renderer, (wx.dataview.DataViewIconTextRenderer, Renderer_Icon))):
			return wx.dataview.DataViewIconText(text = value[0], icon = value[1])
		
		elif (isinstance(defn.renderer, Renderer_MultiImage)):
			image = _Munge(node, defn.renderer.image)
			if (isinstance(image, (list, tuple, set, types.GeneratorType))):
				return image
			else:
				return [image] * value

		return _StringToValue(value, defn.stringConverter)

	def SetValue(self, value, item, column):
		# This gets called in order to set a value in the data model.
		# The most common scenario is that the wx.dataview.DataViewCtrl calls this method after the user changed some data in the view.
		# This is the function you need to override in your derived class but if you want to call it, ChangeValue is usually more convenient as otherwise you need to manually call ValueChanged to update the control itself.
		_log("@model.SetValue", value, item, column)

		# We're not allowing edits in column zero (see below) so we just need
		# to deal with Song objects and cols 1 - 5

		node = self.ItemToObject(item)
		if (isinstance(node, DataListGroup)):
			return True

		try:
			defn = self.olv.columns[column]
		except AttributeError:
			raise AttributeError(f"There is no column {column}")

		if (defn.valueSetter is None):
			_SetValueUsingMunger(node, value, defn.valueGetter, False)
		else:
			_SetValueUsingMunger(node, value, defn.valueSetter, True)
			
		return True

	#Checking ------------------------------------------------------------------------------------------------------
	def HasContainerColumns(self, item):
		#Override this method to indicate if a container item merely acts as a headline (or for categorisation) 
		#or if it also acts a normal item with entries for further columns.
		#By default returns False.
		# _log("@model.HasContainerColumns", item)
		return super().HasContainerColumns(item)

	def HasDefaultCompare(self):
		# Override this to indicate that the model provides a default compare function that the control should use if no wx.dataview.DataViewColumn has been chosen for sorting.
		# Usually, the user clicks on a column header for sorting, the data will be sorted alphanumerically.
		# If any other order (e.g. by index or order of appearance) is required, then this should be used. See wx.dataview.DataViewIndexListModel for a model which makes use of this.
		# _log("@model.HasDefaultCompare")
		return super().HasDefaultCompare()

	def HasValue(self, item, column):
		# Return True if there is a value in the given column of this item.

		# All normal items have values in all columns but the container items only show their label in the first column (column == 0) by default (but see HasContainerColumns ). 
		#So this function always returns True for the first column while for the other ones it returns True only if the item is not a container or HasContainerColumns was overridden to return True for it.
		# _log("@model.HasValue", item, column)
		return super().HasValue(item, column)

	def IsContainer(self, item):
		#Override this to indicate of item is a container, i.e. if it can have child items.
		#Return True if the item has children, False otherwise.
		#This creates groups and sub grops.

		# The hidden root is a container
		if (not item):
			return True

		# and in this model the genre objects are containers
		node = self.ItemToObject(item)
		# _log("@model.IsContainer", item, node)
		if (isinstance(node, DataListGroup)):
			return True


		# but everything else (the song objects) are not
		return False

	def IsEnabled(self, item, column):
		# Override this to indicate that the item should be disabled.
		# Disabled items are displayed differently (e.g. grayed out) and cannot be interacted with.
		# The base class version always returns True, thus making all items enabled by default.

		# _log("@model.IsEnabled", item, column)
		return super().IsEnabled(item, column)

	# Report how many columns this model provides data for.
	def GetColumnCount(self):
		#Override this to indicate the number of columns in the model.
		_log("@model.GetColumnCount")
		return len(self.olv.columns)

	# Map the data column numbers to the data type
	def GetColumnType(self, column):
		#Override this to indicate what type of data is stored in the column specified by column.
		#This should return a string indicating the type of data as reported by Variant .
		_log("@model.GetColumnType", column)
		hgjhghj

		mapper = { 0 : 'string',
				   1 : 'string',
				   2 : 'string',
				   3.: 'string', # the real value is an int, but the renderer should convert it okay
				   4 : 'datetime',
				   5 : 'bool',
				   }
		return mapper[column]

	#Structure Change Notifications ---------------------------------------------------------------------------------
	def Cleared(self):
		#Called to inform the model that all data has been cleared.
		#The control will reread the data from the model again.
		_log("@model.Cleared")
		return super().Cleared()

	def ChangeValue(self, variant, item, column):
		#Change the value of the given item and update the control to reflect it.
		#This function simply calls SetValue and, if it succeeded, ValueChanged .
		_log("@model.ChangeValue", variant, item, column)
		return super().ChangeValue(variant, item, column)

	def ValueChanged(self, item, column):
		# Call this to inform this model that a value in the model has been changed.
		# This is also called from wx.dataview.DataViewCtrl‘s internal editing code, e.g. when editing a text field in the control.
		# This will eventually emit a wxEVT_DATAVIEW_ITEM_VALUE_CHANGED event to the user.
		_log("@model.ValueChanged", item, column)
		return super().ValueChanged(item, column)

	def ItemAdded(self, parent, item):
		#Call this to inform the model that an item has been added to the data.
		_log("@model.ItemAdded", parent, item)

		if (parent is None):
			parent = self.GetParent(item)
			# self.ItemChanged(parent)
		if (not isinstance(item, wx.dataview.DataViewItem)):
			item = self.ObjectToItem(item)
		return super().ItemAdded(parent, item)

	def ItemChanged(self, item):
		#Call this to inform the model that an item has changed.
		# This will eventually emit a wxEVT_DATAVIEW_ITEM_VALUE_CHANGED event (in which the column fields will not be set) to the user.
		_log("@model.ItemChanged", item)
		if (not isinstance(item, wx.dataview.DataViewItem)):
			item = self.ObjectToItem(item)
		return super().ItemChanged(item)

	def ItemDeleted(self, parent, item):
		#Call this to inform the model that an item has been deleted from the data.
		_log("@model.ItemDeleted", parent, item)
		if (parent is None):
			parent = self.GetParent(item)
		if (not isinstance(item, wx.dataview.DataViewItem)):
			item = self.ObjectToItem(item)
		return super().ItemDeleted(parent, item)

	def ItemsAdded(self, parent, items):
		#Call this to inform the model that several items have been added to the data.
		_log("@model.ItemsAdded", parent, items)

		if (parent is not None):
			super().ItemsAdded(parent, items)
		else:
			for item in items:
				answer = self.ItemAdded(parent, item)
		return True

	def ItemsChanged(self, items):
		# Call this to inform the model that several items have changed.
		# This will eventually emit wxEVT_DATAVIEW_ITEM_VALUE_CHANGED events (in which the column fields will not be set) to the user.
		_log("@model.ItemsChanged", items)

		for item in items:
			answer = self.ItemChanged(item)
		return True

	def ItemsDeleted(self, parent, items):
		# Call this to inform the model that several items have been deleted.
		_log("@model.ItemsDeleted", items)

		if (parent is not None):
			return super().ItemsDeleted(parent, items)
		
		for item in items:
			answer = self.ItemDeleted(parent, item)
		return True

	#Sorting-------------------------------------------------------
	def Resort(self):
		# Call this to initiate a resort after the sort function has been changed.
		_log("@model.Resort")

		#Fire a SortEvent that can be catched by an OLV-using developer using Bind() for this event
		column = self.olv.GetSortingColumn()
		try:
			event = DOLVEvent.SortingEvent(self.olv, self.olv.columns.get(column.GetModelColumn(), None), column.GetModelColumn(), column.IsSortOrderAscending())
		except AttributeError as error:
			event = DOLVEvent.SortingEvent(self.olv, None, -1, None)
		self.olv.GetEventHandler().ProcessEvent(event)
		if (not (event.wasHandled or event.IsVetoed())):
			return super().Resort()

	def GetSortValue(self, item, column):
		"""Returns the value to be used for sorting."""

		try:
			defn = self.olv.columns[column]
		except AttributeError:
			raise AttributeError(f"There is no column {column}")

		if (isinstance(defn.renderer, (wx.dataview.DataViewBitmapRenderer, Renderer_Bmp, Renderer_MultiImage))):
			#Do not compare images
			return 0
		
		if (isinstance(defn.renderer, (wx.dataview.DataViewIconTextRenderer, Renderer_Icon))):
			#Only compare the text
			value = self.GetValue(item, column, alternateGetter = defn.groupSortGetter)
			value = value.GetText()
		else:
			value = self.GetValue(item, column, alternateGetter = defn.sortGetter)
		
		# When sorting large groups, this is called a lot. Make it efficent.
		# It is more efficient (by about 30%) to try to call lower() and catch the
		# exception than it is to test for the class
		if (not self.olv.caseSensative):
			try:
				value = value.lower()
			except AttributeError:
				pass
		return value

	def Compare(self, item1, item2, column, ascending):
		#The compare function to be used by control.
		#The default compare function sorts by container and other items separately and in ascending order. Override this for a different sorting behaviour.
		#The comparison function should return negative, null or positive value depending on whether the first item is less than, equal to or greater than the second one. 
		#The items should be compared using their values for the given column.
		_log("@model.Compare", item1, item2, column, ascending)

		if (isinstance(item1, DataListGroup)):
			if (self.olv.groupCompareFunction != None):
				return self.olv.groupCompareFunction(self.ItemToObject(item1), self.ItemToObject(item2), column, ascending)
		else:
			if (self.olv.compareFunction != None):
				return self.olv.compareFunction(self.ItemToObject(item1), self.ItemToObject(item2), column, ascending)
		
		value1 = self.GetSortValue(item1, column)
		value2 = self.GetSortValue(item2, column)

		#The builtin function cmp is depricated now
		#Account for None being a value
		if ((value1 is None, value1) > (value2 is None, value2)):
			return (1, -1)[ascending]
		elif ((value1 is None, value1) < (value2 is None, value2)):
			return (-1, 1)[ascending]
		else:
			return 0

	#Unused -----------------------------------------------------------------------------
	def AddNotifier(self, notifier):
		#Adds a wx.dataview.DataViewModelNotifier to the model.
		_log("@model.AddNotifier", notifier)
		return super().AddNotifier(notifier)

	def RemoveNotifier(self, notifier):
		# Remove the notifier from the list of notifiers.
		_log("@model.RemoveNotifier", notifier)
		return super().RemoveNotifier(notifier)

	def IsListModel(self):
		# _log("@model.IsListModel")
		return super().IsListModel()

	def IsVirtualListModel(self):
		# _log("@model.IsVirtualListModel", super().IsVirtualListModel(), super().IsListModel())
		return super().IsVirtualListModel()

#Renderers
class Renderer_MultiImage(wx.dataview.DataViewCustomRenderer):
	"""
	Places multiple images next to each other.

	If *image* is a list of bitmaps, each will be placed in the cell in the order they are in the list.
	Otherwise, *image* will be repeated n times, where n the value returned by *valueGetter* for the assigned *ColumnDefn*.
	"""

	def __init__(self, image = None, **kwargs):
		_log("@Renderer_MultiImage.__init__", kwargs)
		wx.dataview.DataViewCustomRenderer.__init__(self, **kwargs)
		self.type = "multi_bmp"
		self.buildingKwargs = {**kwargs, "image": image}

		self.value = None
		self.image = image

	def Clone(self, **kwargs):
		#Any keywords in kwargs will override keywords in buildingKwargs
		instructions = {**self.buildingKwargs, **kwargs}
		return super().__self_class__(**instructions)

	def SetValue(self, value):
		# _log("@Renderer_MultiImage.SetValue", value)
		self.value = value
		return True

	def GetValue(self):
		_log("@Renderer_MultiImage.GetValue")
		return self.value

	def GetSize(self):
		# _log("@Renderer_MultiImage.GetSize")
		# Return the size needed to display the value.  The renderer
		# has a helper function we can use for measuring text that is
		# aware of any custom attributes that may have been set for
		# this item.
		return (-1, -1)

	def Render(self, rect, dc, state):
		# _log("@Renderer_MultiImage.Render", rect, dc, state, self.image, self.value)

		x, y, width, height = rect
		totalWidth = 0
		for image in self.value:
			dc.DrawBitmap(image, x + totalWidth, y)
			totalWidth += image.GetWidth()
		return True

class Renderer_Button(wx.dataview.DataViewCustomRenderer):
	"""
	When pressed, runs the function returned by by *valueGetter* for the assigned *ColumnDefn*.
	This means that *valueGetter* should be a function that returns a function.
	For simplicity, you can use `lambda: yourFunction`.
	"""

	def __init__(self, text = "", mode = wx.dataview.DATAVIEW_CELL_ACTIVATABLE, useNativeRenderer = False, **kwargs):
		_log("@Renderer_Button.__init__", text, mode, kwargs)

		wx.dataview.DataViewCustomRenderer.__init__(self, mode = mode, **kwargs)
		self.type = "button"
		self.buildingKwargs = {**kwargs, "text": text, "mode": mode}
		
		self.value = None
		self.text = text
		self.useNativeRenderer = useNativeRenderer

	def Clone(self, **kwargs):
		#Any keywords in kwargs will override keywords in buildingKwargs
		instructions = {**self.buildingKwargs, **kwargs}
		return super().__self_class__(**instructions)

	def SetValue(self, value):
		# _log("@Renderer_Button.SetValue", value)
		self.value = value
		return True

	def GetValue(self):
		_log("@Renderer_Button.GetValue")
		return self.value

	def GetSize(self):
		# _log("@Renderer_Button.GetSize")
		return (-1, -1)

	def Render(self, rectangle, dc, state):
		# _log("@Renderer_Button.Render", rectangle, dc, state, self.value)

		isSelected = state == wx.dataview.DATAVIEW_CELL_SELECTED
		if (self.useNativeRenderer):
			#Use: https://github.com/wxWidgets/wxPython/blob/master/demo/RendererNative.py
			wx.RendererNative.Get().DrawPushButton(self.GetOwner().GetOwner(), dc, rectangle, state)
		else:
			rectangle.Deflate(2, 2)
			_drawButton(dc, rectangle, isSelected)
		if (self.text):
			_drawText(dc, rectangle, self.text, isSelected, align = "center")
		return True

	def LeftClick(self, pos, cellRect, model, item, col):
		_log("@Renderer_Button.LeftClick", pos, cellRect, model, item, col)
		self.value()
		return True

	def Activate(self, cellRect, model, item, col):
		_log("@Renderer_Button.Activate", cellRect, model, item, col)
		self.value()
		return True

class Renderer_CheckBox(wx.dataview.DataViewToggleRenderer):
	"""
	Changed the default behavior from Inert to Active.
	"""

	def __init__(self, mode = wx.dataview.DATAVIEW_CELL_ACTIVATABLE, **kwargs):
		_log("@Renderer_CheckBox.__init__", mode, kwargs)

		wx.dataview.DataViewToggleRenderer.__init__(self, mode = mode, **kwargs)
		self.type = "check"
		self.buildingKwargs = {**kwargs, "mode": mode}

	def Clone(self, **kwargs):
		#Any keywords in kwargs will override keywords in buildingKwargs
		instructions = {**self.buildingKwargs, **kwargs}
		return super().__self_class__(**instructions)

class Renderer_Progress(wx.dataview.DataViewCustomRenderer):
	"""
	Renders a simple progress bar.
	The bar can be customized by passing in 'color', or for more control 'pen' and 'brush' can also be passed in.
	All three can be callable functions that return a color, pen, and brush respectively.
	'minimum' and 'maximum' can also be callable functions that return integers.

	'editor' determines what type of editor is used to change the value of the progress bar.
	Possible editors are: "text" for a wxTextCtrl, "spin" for a wxSpinCtrl, and "slider" for a wxSlider.
	"""

	def __init__(self, minimum = 0, maximum = 100, editor = "slider",
		color = wx.BLUE, pen = None, brush = None, 
		mode = wx.dataview.DATAVIEW_CELL_EDITABLE, **kwargs):
		_log("@Renderer_Progress.__init__", mode, kwargs)

		wx.dataview.DataViewCustomRenderer.__init__(self, mode = mode, **kwargs)
		self.type = "progress"
		self.buildingKwargs = {**kwargs, "mode": mode}

		self.value = None

		self.SetEditor(editor)
		self.SetMin(minimum)
		self.SetMax(maximum)
		self.SetColor(color)
		self.SetPen(pen)
		self.SetBrush(brush)

	def Clone(self, **kwargs):
		#Any keywords in kwargs will override keywords in buildingKwargs
		instructions = {**self.buildingKwargs, **kwargs}
		return super().__self_class__(**instructions)

	def SetEditor(self, editor = None):
		self.editor = editor or "slider"
		self.buildingKwargs["editor"] = editor

	def SetMax(self, maximum = None):
		self.maximum = maximum or 100
		self.buildingKwargs["maximum"] = maximum

	def SetMin(self, minimum = None):
		self.minimum = minimum or 0
		self.buildingKwargs["minimum"] = minimum

	def SetColor(self, color = None):
		self.color = color or wx.BLUE
		self.buildingKwargs["color"] = color

	def SetPen(self, pen = None):
		if ((pen is None) and (not callable(self.color))):
			self.pen = wx.Pen(wx.BLACK, 1)
		else:
			self.pen = pen
		self.buildingKwargs["pen"] = pen

	def SetBrush(self, brush = None):
		if ((brush is None) and (not callable(self.color))):
			self.brush = wx.Brush(self.color)
		else:
			self.brush = brush
		self.buildingKwargs["brush"] = brush

	def SetValue(self, value):
		# _log("@Renderer_Progress.SetValue", value)
		try:
			self.value = int(value)
		except TypeError:
			self.value = 0
		return True

	def GetValue(self):
		# _log("@Renderer_Progress.GetValue")
		return self.value

	def GetSize(self):
		# _log("@Renderer_Progress.GetSize")
		return (-1, -1)

	def Render(self, rectangle, dc, state):
		# _log("@Renderer_Progress.Render", rectangle, dc, state, self.value)

		if (callable(self.pen)):
			pen = self.pen()
		else:
			pen = self.pen
		if (pen is None):
			pen = wx.Pen(wx.BLACK, 1)

		if (callable(self.brush)):
			brush = self.brush()
		else:
			brush = self.brush
		if (brush is None):
			if (callable(self.color)):
				color = self.color()
			else:
				color = self.color
			if (color is None):
				color = wx.BLUE
			brush = wx.Brush(color)

		if (callable(self.minimum)):
			minimum = self.minimum()
		else:
			minimum = self.minimum
		if (minimum is None):
			minimum = 0

		if (callable(self.maximum)):
			maximum = self.maximum()
		else:
			maximum = self.maximum
		if (maximum is None):
			maximum = 100

		dc.SetPen(pen)
		dc.SetBrush(brush)
		
		rectangle.Deflate(1, rectangle.GetHeight() / 4)
		try:
			width = max(0, rectangle.GetWidth() / ((int(maximum) - int(minimum)) / (min(int(self.value), int(maximum)) - int(minimum))))
		except ZeroDivisionError:
			width = 0

		dc.DrawRectangle(rectangle.GetTopLeft(), (width, rectangle.GetHeight()))

		return True

	def HasEditorCtrl(self):
		# _log("@Renderer_Progress.HasEditorCtrl")
		return True

	def CreateEditorCtrl(self, parent, labelRect, value):
		# _log("@Renderer_Progress.CreateEditorCtrl", parent, labelRect, value)
		
		if (self.editor.lower() == "text"):
			ctrl = wx.TextCtrl(parent, value = str(value), pos = labelRect.Position, size = labelRect.Size)
			ctrl.SetInsertionPointEnd()
			ctrl.SelectAll()

		else:
			if (callable(self.minimum)):
				minimum = self.minimum()
			else:
				minimum = self.minimum
			if (minimum is None):
				minimum = 0

			if (callable(self.maximum)):
				maximum = self.maximum()
			else:
				maximum = self.maximum
			if (maximum is None):
				maximum = 100

			if (self.editor.lower() == "slider"):
				ctrl = wx.Slider(parent, value = int(value), minValue = int(minimum), maxValue = int(maximum), pos = labelRect.Position, size = labelRect.Size)
			else:
				ctrl = wx.SpinCtrl(parent, pos = labelRect.Position, size = labelRect.Size, min = int(minimum), max = int(maximum), initial = int(value))

		return ctrl

	def GetValueFromEditorCtrl(self, editor):
		# _log("@Renderer_Progress.GetValueFromEditorCtrl", editor, editor.GetValue())
		if (callable(self.minimum)):
			minimum = self.minimum()
		else:
			minimum = self.minimum
		if (minimum is None):
			minimum = 0

		if (callable(self.maximum)):
			maximum = self.maximum()
		else:
			maximum = self.maximum
		if (maximum is None):
			maximum = 100

		return min(max(minimum, editor.GetValue()), maximum)

class Renderer_Choice(wx.dataview.DataViewChoiceRenderer):
	"""
	*choices* can now be a function that returns a list of choices.
	"""

	def __init__(self, choices = [], ellipsize = True, **kwargs):
		# _log("@Renderer_Choice.__init__", choices, kwargs)

		self.choices = choices
		if (callable(choices)):
			wx.dataview.DataViewChoiceRenderer.__init__(self, [], **kwargs)
		else:
			wx.dataview.DataViewChoiceRenderer.__init__(self, choices, **kwargs)
		self.type = "choice"
		self.buildingKwargs = {**kwargs, "choices": choices, "ellipsize": ellipsize}

		if (not ellipsize):
			self.DisableEllipsize()

	def Clone(self, **kwargs):
		#Any keywords in kwargs will override keywords in buildingKwargs
		instructions = {**self.buildingKwargs, **kwargs}
		return super().__self_class__(**instructions)

	def CreateEditorCtrl(self, parent, labelRect, value):
		# _log("@Renderer_Choice.CreateEditorCtrl", parent, labelRect, value, self.choices)

		if (callable(self.choices)):
			choices = self.choices()
		else:
			choices = self.choices

		window = wx.Choice(parent, id = wx.ID_ANY, pos = labelRect.GetTopLeft(), size = labelRect.GetSize(), choices = choices)
		try:
			window.SetSelection(choices.index(value))
		except ValueError as error:
			pass
		return window

class Renderer_Text(wx.dataview.DataViewTextRenderer):
	"""
	"""

	def __init__(self, **kwargs):
		_log("@Renderer_Text.__init__", kwargs)

		wx.dataview.DataViewTextRenderer.__init__(self, **kwargs)
		self.type = "text"
		self.buildingKwargs = {**kwargs}

	def Clone(self, **kwargs):
		#Any keywords in kwargs will override keywords in buildingKwargs
		instructions = {**self.buildingKwargs, **kwargs}
		return super().__self_class__(**instructions)

class Renderer_Spin(wx.dataview.DataViewSpinRenderer):
	"""
	"""

	def __init__(self, minimum = 0, maximum = 10, **kwargs):
		_log("@Renderer_Spin.__init__", kwargs)

		wx.dataview.DataViewSpinRenderer.__init__(self, minimum, maximum, **kwargs)
		self.type = "spin"
		self.buildingKwargs = {**kwargs, "minimum": minimum, "maximum": maximum}

	def Clone(self, **kwargs):
		#Any keywords in kwargs will override keywords in buildingKwargs
		instructions = {**self.buildingKwargs, **kwargs}
		return super().__self_class__(**instructions)

class Renderer_Bmp(wx.dataview.DataViewBitmapRenderer):
	"""
	"""

	def __init__(self, **kwargs):
		_log("@Renderer_Bmp.__init__", kwargs)

		wx.dataview.DataViewBitmapRenderer.__init__(self, **kwargs)
		self.type = "bmp"
		self.buildingKwargs = {**kwargs}

	def Clone(self, **kwargs):
		#Any keywords in kwargs will override keywords in buildingKwargs
		instructions = {**self.buildingKwargs, **kwargs}
		return super().__self_class__(**instructions)

class Renderer_Icon(wx.dataview.DataViewIconTextRenderer):
	"""
	"""

	def __init__(self, **kwargs):
		_log("@Renderer_Icon.__init__", kwargs)

		wx.dataview.DataViewIconTextRenderer.__init__(self, **kwargs)
		self.type = "icon"
		self.buildingKwargs = {**kwargs}

	def Clone(self, **kwargs):
		#Any keywords in kwargs will override keywords in buildingKwargs
		instructions = {**self.buildingKwargs, **kwargs}
		return super().__self_class__(**instructions)


rendererCatalogue = {
	None:        {"edit": wx.dataview.DATAVIEW_CELL_EDITABLE, 		"nonEdit": wx.dataview.DATAVIEW_CELL_ACTIVATABLE, 	"class": Renderer_Text},
	"text":      {"edit": wx.dataview.DATAVIEW_CELL_EDITABLE, 		"nonEdit": wx.dataview.DATAVIEW_CELL_ACTIVATABLE, 	"class": Renderer_Text},
	"spin":      {"edit": wx.dataview.DATAVIEW_CELL_EDITABLE, 		"nonEdit": wx.dataview.DATAVIEW_CELL_INERT, 		"class": Renderer_Spin},
	"bmp":       {"edit": wx.dataview.DATAVIEW_CELL_ACTIVATABLE, 	"nonEdit": wx.dataview.DATAVIEW_CELL_INERT, 		"class": Renderer_Bmp},
	"icon":      {"edit": wx.dataview.DATAVIEW_CELL_EDITABLE, 		"nonEdit": wx.dataview.DATAVIEW_CELL_ACTIVATABLE, 	"class": Renderer_Icon},
	"progress":  {"edit": wx.dataview.DATAVIEW_CELL_EDITABLE, 		"nonEdit": wx.dataview.DATAVIEW_CELL_ACTIVATABLE, 	"class": Renderer_Progress},
	"check":     {"edit": wx.dataview.DATAVIEW_CELL_ACTIVATABLE,	"nonEdit": wx.dataview.DATAVIEW_CELL_INERT, 		"class": Renderer_CheckBox},
	"multi_bmp": {"edit": wx.dataview.DATAVIEW_CELL_ACTIVATABLE, 	"nonEdit": wx.dataview.DATAVIEW_CELL_INERT, 		"class": Renderer_MultiImage},
	"button":    {"edit": wx.dataview.DATAVIEW_CELL_ACTIVATABLE, 	"nonEdit": wx.dataview.DATAVIEW_CELL_INERT, 		"class": Renderer_Button},
	"choice":    {"edit": wx.dataview.DATAVIEW_CELL_EDITABLE, 		"nonEdit": wx.dataview.DATAVIEW_CELL_ACTIVATABLE, 	"class": Renderer_Choice},
}

