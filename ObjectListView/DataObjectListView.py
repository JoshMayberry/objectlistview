__author__ = "Phillip Piper and Joshua Mayberry"

import os
import ast
import time
import types
import datetime

import operator
import functools

import wx
import wx.dataview
import wx.lib.wordwrap

from . import DOLVEvent
import MyUtilities.wxPython
AutocompleteTextCtrl = MyUtilities.wxPython.AutocompleteTextCtrl

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

		#Standard
		self.columns = {}
		self.modelObjects = []
		self.colorOverride_row = {}
		self.colorOverride_cell = {}
		self.colorOverride_column = {}
		self.colorOverride_function = None
		self.colorOverride_groupFunction = None
		self.lastSelected = None

		useWeakRefs 			= kwargs.pop("useWeakRefs", True)
		self.noHeader 			= kwargs.pop("noHeader", False)
		self.rowFormatter 		= kwargs.pop("rowFormatter", None)
		self.singleSelect 		= kwargs.pop("singleSelect", True)
		self.verticalLines 		= kwargs.pop("verticalLines", False)
		self.horizontalLines 	= kwargs.pop("horizontalLines", False)
		
		self.groupBackColor			= kwargs.pop("groupBackColor", None)# wx.Colour(195, 144, 212))  # LIGHT MAGENTA
		self.oddRowsBackColor		= kwargs.pop("oddRowsBackColor", wx.Colour(255, 250, 205))  # LEMON CHIFFON
		self.evenRowsBackColor		= kwargs.pop("evenRowsBackColor", wx.Colour(240, 248, 255))  # ALICE BLUE
		self.useAlternateBackColors = kwargs.pop("useAlternateBackColors", True)
		self.backgroundColor 		= kwargs.pop("backgroundColor", None)
		self.foregroundColor 		= kwargs.pop("foregroundColor", None)
		
		#Sorting
		self.sortable 				= kwargs.pop("sortable", True)
		self.caseSensitive 			= kwargs.pop("caseSensitive", True)
		self.compareFunction		= kwargs.pop("compareFunction", None)
		self.unsortedFunction 		= kwargs.pop("unsortedFunction", None)
		self.groupCompareFunction 	= kwargs.pop("groupCompareFunction", None)

		#Filtering
		self.filter 					= kwargs.pop("filter", None)
		self.typingSearchesSortColumn	= kwargs.pop("typingSearchesSortColumn", True)

		#Editing
		self.cellEditor = None
		self.cellBeingEdited = None
		self.selectionBeforeCellEdit = []

		self.readOnly 		= kwargs.pop("readOnly", False)
		self.cellEditMode 	= kwargs.pop("cellEditMode", self.CELLEDIT_NONE)

		#Searching
		self.searchPrefix = u""
		self.whenLastTypingEvent = 0

		#Context Menu
		self.contextMenu = ContextMenu(self)
		self.columnContextMenu = ContextMenu(self)

		self.showContextMenu 		= kwargs.pop("showContextMenu", False)
		self.showColumnContextMenu 	= kwargs.pop("showColumnContextMenu", False)

		#Groups
		self.groups = []
		self.emptyGroups = []

		groupIndent 					= kwargs.pop("groupIndent", False)
		self.groupTitle 				= kwargs.pop("groupTitle", "")
		self.showGroups 				= kwargs.pop("showGroups", False)
		self.showItemCounts 			= kwargs.pop("showItemCounts", True)
		self.hideFirstIndent 			= kwargs.pop("hideFirstIndent", False)
		self.showEmptyGroups 			= kwargs.pop("showEmptyGroups", False)
		self.separateGroupColumn 		= kwargs.pop("separateGroupColumn", False)
		self.alwaysGroupByColumnIndex	= kwargs.pop("alwaysGroupByColumnIndex", -1)
		self.putBlankLineBetweenGroups	= kwargs.pop("putBlankLineBetweenGroups", True)
		self.rebuildGroup_onColumnClick = kwargs.pop("rebuildGroup_onColumnClick", True)

		self.groupFont 				= kwargs.pop("groupFont", None) #(Bold, Italic, Color)
		self.groupTextColour 		= kwargs.pop("groupTextColour", wx.Colour(33, 33, 33, 255))
		self.groupBackgroundColour 	= kwargs.pop("groupBackgroundColour", wx.Colour(159, 185, 250, 249))

		#Key Events
		self.key_edit 		= kwargs.pop("key_edit", True)
		self.key_copy 		= kwargs.pop("key_copy", True)
		self.key_undo 		= kwargs.pop("key_undo", True)
		self.key_paste 		= kwargs.pop("key_paste", True)
		self.key_scroll 	= kwargs.pop("key_scroll", True)
		self.key_expand 	= kwargs.pop("key_expand", True)
		self.key_selectAll 	= kwargs.pop("key_selectAll", True)

		self.key_copyEntireRow 		= kwargs.pop("key_copyEntireRow", True)
		self.key_pasteEntireRow 	= kwargs.pop("key_pasteEntireRow", None)

		#Copy/Paste
		self.copiedList = []
		self.lastClicked = (None, None)
		self._paste_ignoreSort = False

		self.clipSimple 			= kwargs.pop("clipSimple", True)
		self.clipPrefix 			= kwargs.pop("clipPrefix", "\n")
		self.clipSuffix 			= kwargs.pop("clipSuffix", "\n")
		self.clipColumnSpacer 		= kwargs.pop("clipColumnSpacer", "\t")
		self.clipKeepAfterClose 	= kwargs.pop("clipKeepAfterClose", True)
		
		self.clipRowSpacer 	= kwargs.pop("clipRowSpacer", "\n")
		self.clipRowPrefix 	= kwargs.pop("clipRowPrefix", "")
		self.clipRowSuffix 	= kwargs.pop("clipRowSuffix", "")

		self.clipGroup 			= kwargs.pop("clipGroup", True)
		self.clipGroupSpacer 	= kwargs.pop("clipGroupSpacer", None)
		self.clipGroupPrefix 	= kwargs.pop("clipGroupPrefix", "\n")
		self.clipGroupSuffix 	= kwargs.pop("clipGroupSuffix", None)

		self.pasteWrap 			= kwargs.pop("pasteWrap", True)
		self.pasteToCell 		= kwargs.pop("pasteToCell", True)
		self.pasteInSelection 	= kwargs.pop("pasteInSelection", False)

		#Undo/Redo
		self.undoHistory = []
		self.redoHistory = []
		self._undo_listenForCheckBox = True

		self.undoCap 	= kwargs.pop("undoCap", 50)

		#Etc
		self.emptyListMsg 		= kwargs.pop("emptyListMsg", "This list is empty")
		self.emptyListFilterMsg = kwargs.pop("emptyListFilterMsg", None)
		self.emptyListFont 		= kwargs.pop("emptyListFont", wx.Font(24, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))

		#Setup Style
		style = kwargs.pop("style", None) #Do NOT pass in wx.LC_REPORT, or it will call virtual functions A LOT

		if (style is None):
			if (self.singleSelect):
				style = [wx.dataview.DV_SINGLE]
			else:
				style = [wx.dataview.DV_MULTIPLE]

			if (self.horizontalLines):
				style.append(wx.dataview.DV_HORIZ_RULES)

			if (self.verticalLines):
				style.append(wx.dataview.DV_VERT_RULES)

			if (self.noHeader):
				style.append(wx.dataview.DV_NO_HEADER)

			# if (self.useAlternateBackColors):
			# 	#Currently only supported by the native GTK and OS X implementations
			# 	style += "|wx.dataview.DV_ROW_LINES" #Cannot change colors?
			wx.dataview.DataViewCtrl.__init__(self, *args, style = functools.reduce(operator.ior, style or (0,)), **kwargs)
		else:
			wx.dataview.DataViewCtrl.__init__(self, *args, style = style, **kwargs)

		if (self.backgroundColor is not None):
			super().SetBackgroundColour(self.backgroundColor)
		if (self.foregroundColor is not None):
			super().SetForegroundColour(self.foregroundColor)

		if (self.groupFont is None):
			font = self.GetFont()
			self.groupFont = wx.FFont(font.GetPointSize(), font.GetFamily(), wx.FONTFLAG_BOLD, font.GetFaceName())
		if (isinstance(self.groupFont, wx.Font)):
			self.groupFont = (self.groupFont.GetWeight() == wx.BOLD, self.groupFont.GetStyle() == wx.ITALIC, wx.Colour(0, 0, 0))

		self.SetGroupIndent(groupIndent)
		self.SetModel(useWeakRefs = useWeakRefs)
		self.overlayEmptyListMsg = wx.Overlay()

		#Bind Functions
		self.Bind(wx.EVT_CHAR, self._HandleChar)
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

		self.Bind(wx.dataview.EVT_DATAVIEW_COLUMN_HEADER_CLICK, self._RelayColumnHeaderLeftClick)
		self.Bind(wx.dataview.EVT_DATAVIEW_COLUMN_HEADER_RIGHT_CLICK, self._RelayColumnHeaderRightClick)

		self.Bind(wx.dataview.EVT_DATAVIEW_COLUMN_SORTED, self._RelaySorted)
		self.Bind(wx.EVT_HEADER_BEGIN_REORDER, self._RelayReordering)
		self.Bind(wx.EVT_HEADER_END_REORDER, self._RelayReordered)
		self.Bind(wx.EVT_HEADER_DRAGGING_CANCELLED, self._RelayReorderCancel)

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
	# 	print("@on_expand.1", item.IsOk())
	# 	super().Expand(item)
	# 	print("@on_expand.2", self.IsExpanded(item), self.model.IsContainer(item))
	# 	event.Skip()

	# --------------------------------------------------------------#000000#FFFFFF
	# Setup


	#https://stackoverflow.com/questions/32711381/wxpython-wxdataviewlistctrl-get-all-selected-rows-items

	def SetModel(self, model = None, useWeakRefs = True):
		"""
		Associates the ListCtrl with the supplied model.
		If *model* is None, will use *NormalListModel*.
		"""

		# Create an instance of our model...
		if model is None:
			self.model = NormalListModel(self, useWeakRefs = useWeakRefs)
		else:
			self.model = model

		# Tel the DVC to use the model
		self.AssociateModel(self.model)
		self.model.DecRef() # avoid memory leak

	def SetColumns(self, columns, repopulate = True, clearRows = False):
		sortCol = self.GetSortColumn()
		self.ClearColumns()

		if (clearRows):
			self.ClearAll()

		self.columns = {}
		
		if (self.hideFirstIndent and (not self.showGroups)):
			x = self.AddColumnDefn(DataColumnDefn(title = "", width = 0))
			x.isInternal = True
			# self.SetExpanderColumn(x.column)

		for x in columns:
			if (x.isInternal):
				continue
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

	def SetGroupIndent(self, indent = None):
		"""
		Sets the indentation of items in groups.
		"""

		super().SetIndent(indent or 0)

	def AddColumnDefn(self, defn, index = None):
		"""
		Append the given ColumnDefn object to our list of active columns.

		If this method is called directly, you must also call RepopulateList()
		to populate the new column with data.
		"""
		self.columns[index or len(self.columns)] = defn

		#https://wxpython.org/Phoenix/docs/html/wx.dataview.DataViewColumn.html
		#https://wxpython.org/Phoenix/docs/html/wx.dataview.DataViewColumnFlags.enumeration.html
		#https://wxpython.org/Phoenix/docs/html/wx.dataview.DataViewCtrl.html#wx.dataview.DataViewCtrl.AppendColumn
		
		if (self.readOnly):
			defn.SetEditable(refreshColumn = False, changeVar = False, state = False)
		else:
			defn.SetEditable(refreshColumn = False, changeVar = False)

		defn.column = wx.dataview.DataViewColumn(defn.title, defn.renderer, index or len(self.columns) - 1, 
			width = defn.width, align = defn.GetAlignment())#, flags = wx.COL_WIDTH_AUTOSIZE)
		defn.SetHidden()
		defn.SetSortable()
		defn.SetResizeable()
		defn.SetReorderable()
		defn.SetSpaceFilling()

		if (index):
			return self.InsertColumn(index, defn)
		else:
			return self.AppendColumn(defn)

	def InsertColumn(self, index, column):
		super().InsertColumn(index, column.column)
		return column

	def AppendColumn(self, column):
		super().AppendColumn(column.column)
		return column

	def SetObjects(self, modelObjects, preserveSelection = False, preserveExpansion = True):
		"""
		Set the list of modelObjects to be displayed by the control.
		"""

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
		When there are no objects in the list, show this message in the control.
		"""
		self.emptyListMsg = msg

	def SetEmptyListFilterMsg(self, msg):
		"""
		When there are no objects in the list because of *filter*, show this message in the control.
		If None, will show the message in *emptyListMsg*.
		"""
		self.emptyListFilterMsg = msg

	def SetEmptyListMsgFont(self, font):
		"""
		In what font should the empty list message be rendered?
		"""
		self.emptyListFont = font

	def SetRowColour(self, modelObject, color = None):
		"""
		Changes the cell color for the entire row of the specified modelObject only.

		If *color* is None, the default color will be used. If *color* is a list, 
		the first element will be the color if the row if odd; 
		the second element will be the color if the row is even.
		"""

		if (color is not None):
			self.colorOverride_row[modelObject] = color
		elif (modelObject in self.colorOverride_row):
			del self.colorOverride_row[modelObject]

		# self.model.ItemChanged(modelObject)
		self.model.Cleared()

	def SetColumnColour(self, column, color = None):
		"""
		Changes the cell color for the entire given column only.

		If *color* is None, the default color will be used. If *color* is a list, 
		the first element will be the color if the row if odd; 
		the second element will be the color if the row is even.
		"""

		defn = self.GetColumn(column)
		if (defn is None):
			return

		index = defn.GetIndex()
		if (color is not None):
			self.colorOverride_column[index] = color
		elif (index in self.colorOverride_column):
			del self.colorOverride_column[index]

		self.model.Cleared()

	def SetCellColour(self, modelObject, column, color = None):
		"""
		Changes the cell color for the specified modelObject and given column.

		If *color* is None, the default color will be used. If *color* is a list, 
		the first element will be the color if the row if odd; 
		the second element will be the color if the row is even.
		"""

		defn = self.GetColumn(column)
		if (defn is None):
			return

		index = defn.GetIndex()
		if (color is not None):
			self.colorOverride_cell[(modelObject, index)] = color
		elif ((modelObject, index) in self.colorOverride_cell):
			del self.colorOverride_cell[(modelObject, index)]

		self.model.Cleared()

	def SetColorFunction(self, function = None):
		"""
		A function can be used to override row color instead of using
		SetRowColour, SetColumnColour, and SetCellColour.

		*function* must accept the following args: row, column
		*function* must return a valid wxColor or None

		If None, the functions mentioned above will be used.
		"""
		self.colorOverride_function = function

		self.model.Cleared()

	def SetColorGroupFunction(self, function = None):
		"""
		A function can be used to override goup color.

		*function* must accept the following args: row, column
		*function* must return a valid wxColor or None
		"""
		self.colorOverride_groupFunction = function

		self.model.Cleared()

	def SetFilter(self, myFilter, repopulate = True):
		"""
		Remember the filter that is currently operating on this control.
		Set this to None to clear the current filter.

		A filter is a callable that accepts one parameter: the original list
		of model objects. The filter chooses which of these model objects should
		be visible to the user, and returns a collection of only those objects.

		The Filter module has some useful standard filters.
		(https://filters.readthedocs.io/en/latest/)

		You must call RepopulateList() for changes to the filter to be visible.
		"""
		self.filter = myFilter

		if (repopulate):
			self.RepopulateList()

	#-------------------------------------------------------------------------
	# Accessing

	def GetItemCount(self):
		return len(self.modelObjects)

	def GetGroupIndent(self):
		return super().GetIndent()

	def GetObjects(self):
		"""
		Return the model objects that are available to the control.

		If no filter is in effect, this is the same as GetFilteredObjects().
		"""
		return self.modelObjects

	def GetFilteredObjects(self):
		if (not self.filter):
			return self.GetObjects()
		return self.filter(self.modelObjects)

	def GetFilter(self):
		"""
		Return the filter that is currently operating on this control.
		"""
		return self.filter

	def GetGroups(self):
		return self.groups

	def GetEmptyGroups(self):
		return [group for group in self.groups if (not group.modelObjects)]

	def GetColumns(self):
		"""
		Returns a list of all columns.
		"""
		return self.columns

	def GetColumn(self, column):
		"""
		Returns the requested column, or None if it does not exist.
		*column* can be the column number or what *valueGetter* is for the desired column.
		"""

		if (isinstance(column, DataColumnDefn)):
			return column

		if (isinstance(column, wx.dataview.DataViewColumn)):
			column = column.GetModelColumn()
		if (isinstance(column, int)):
			for item in self.columns.values():
				if (item.GetIndex() == column):
					return item
			return

		for defn in self.columns.values():
			if (defn.valueGetter == column):
				return defn

	def GetCurrentColumn(self):
		"""
		Returns the column that currently has focus.
		"""
		column = super().GetCurrentColumn()
		if (not column):
			return
		return self.columns[column.GetModelColumn()]

	def GetCurrentObject(self):
		"""
		Return the model object that currently has focus.
		"""

		item = self.GetCurrentItem()
		if (not item.IsOk()):
			return
		return self.model.ItemToObject(item)

	def GetFirst(self):
		"""
		Return the first model object.
		"""

		item = self.model.GetFirstItem()
		if (item.IsOk()):
			return self.model.ItemToObject(item)

	def GetLast(self):
		"""
		Return the last model object.
		"""

		item = self.model.GetLastItem()
		if (item.IsOk()):
			return self.model.ItemToObject(item)

	def GetNext(self, modelObject, wrap = True):
		"""
		Return the item below the given model object.
		"""

		item = self.model.GetNextItem(modelObject, wrap = wrap)
		if (item.IsOk()):
			return self.model.ItemToObject(item)

	def GetPrevious(self, modelObject, wrap = True):
		"""
		Return the item above the given model object.
		"""

		item = self.model.GetPreviousItem(modelObject, wrap = wrap)
		if (item.IsOk()):
			return self.model.ItemToObject(item)

	def GetColumnPosition(self, column = None):
		"""Return the position of the column or -1 if it is not in this table.

		Example Input: GetColumnPosition()
		"""

		if (column is None):
			catalogue = {}
			for _column in self.columns.values():
				if (_column.isInternal):
					continue
				catalogue.update(self.GetColumnPosition(_column))
			return catalogue

		column = self.GetColumn(column)
		return {super().GetColumnPosition(column.column): column}

	#Selection Functions
	def SetCurrentObject(self, modelObject):
		"""
		Set the model object that currently has focus.
		"""

		self.SetCurrentItem(self.model.ObjectToItem(modelObject))

	def YieldSelected(self):
		"""
		Progressively yield all selected items
		"""

		for item in self.GetSelections():
			yield self.model.ItemToObject(item)

	def GetSelectedObject(self):
		"""
		Return the selected modelObject or None if nothing is selected
		"""
		for model in self.YieldSelectedObjects():
			return model
		return None

	def GetSelectedObjects(self):
		"""
		Return a list of the selected modelObjects
		"""
		return list(self.YieldSelectedObjects())

	def YieldSelectedObjects(self):
		"""
		Progressively yield the selected modelObjects
		"""

		for item in self.YieldSelected():
			if (not isinstance(item, DataListGroup)):
				yield item

	def GetSelectedGroup(self):
		"""
		Return the selected groups or None if nothing is selected
		"""
		for model in self.YieldSelectedGroups():
			return model
		return None

	def GetSelectedGroups(self):
		"""
		Return a list of the selected groups
		"""
		return list(self.YieldSelectedGroups())

	def YieldSelectedGroups(self):
		"""
		Progressively yield the selected groups
		"""

		for item in self.YieldSelected():
			if (isinstance(item, DataListGroup)):
				yield item

	def IsAnySelected(self):
		"""
		Returns if there is any selection at all.
		"""

		try:
			next(iter(self.YieldSelected()))
			return True
		except StopIteration:
			return False

	def IsAnyObjectSelected(self):
		"""
		Returns if there is any object selection at all.
		"""

		try:
			next(iter(self.YieldSelectedObjects()))
			return True
		except StopIteration:
			return False

	def IsAnyGroupSelected(self):
		"""
		Returns if there is any group selection at all.
		"""

		try:
			next(iter(self.YieldSelectedGroups()))
			return True
		except StopIteration:
			return False

	def IsObjectSelected(self, modelObject):
		"""
		Is the given modelObject selected?
		"""
		for item in self.YieldSelectedObjects():
			if (item is modelObject):
				return True
		return False

	def IsGroupSelected(self, group):
		"""
		Is the given group selected?
		"""
		if (isinstance(group, str)):
			for item in self.YieldSelectedGroups():
				if (item.key == group):
					return True
		else:
			for item in self.YieldSelectedGroups():
				if (item is group):
					return True
		return False

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

	def SelectAll(self, override_singleSelect = True):
		"""
		Selected all model objects in the control.

		In a GroupListView, this does not select blank lines or groups
		"""

		if ((not override_singleSelect) and (self.singleSelect)):
			return self.SelectFirst()

		super().SelectAll()

	def UnselectAll(self):
		"""
		Unselect all model objects in the control.
		"""
		super().UnselectAll()

	DeselectAll = UnselectAll
	Deselect = Unselect

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

	def SelectFirst(self):
		"""
		Select the first item in the list.
		"""

		item = self.model.GetFirstItem()
		super().Select(item)

	def SelectLast(self):
		"""
		Select the last item in the list.
		"""

		item = self.model.GetLastItem()
		super().Select(item)

	def SelectNext(self, deselectOthers = True, wrap = True):
		"""
		Select the item(s) below the currently selected item(s).
		"""

		selection = []
		for item in self.GetSelections():
			selection.append(self.model.GetNextItem(item, wrap = wrap))
		if (not selection):
			if (wrap):
				selection = [self.model.GetLastItem()]
			else:
				selection = [self.model.GetFirstItem()]

		if (deselectOthers):
			self.UnselectAll()

		for item in selection:
			super().Select(item)

	def SelectPrevious(self, deselectOthers = True, wrap = True):
		"""
		Select the item(s) above the currently selected item(s).
		"""

		selection = []
		for item in self.GetSelections():
			selection.append(self.model.GetPreviousItem(item, wrap = wrap))
		if (not selection):
			if (wrap):
				selection = [self.model.GetFirstItem()]
			else:
				selection = [self.model.GetLastItem()]
		
		if (deselectOthers):
			self.UnselectAll()

		for item in selection:
			super().Select(item)

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
		self.InsertColumn(0, defn)

	def SetGroups(self, groups):
		"""
		Present the collection of DataListGroups in this control.

		Calling this automatically put the control into ShowGroup mode
		"""
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

		#Because this groups need the extra indention for the expanders, 
		#the extra indentation is needed if there are groups
		if (self.hideFirstIndent):
			self.SetColumns(list(self.columns.values()))

		self.model.Cleared()

	def GetShowEmptyGroups(self):
		"""
		Return whether or not this control is showing empty groups
		"""
		return self.showEmptyGroups

	def SetShowEmptyGroups(self, showEmptyGroups = True):
		"""
		Set whether or not this control is showing empty groups
		"""
		if (showEmptyGroups == self.showEmptyGroups):
			return

		self.showEmptyGroups = showEmptyGroups
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
			try:
				index = max([i for i in self.columns.keys() if (i is not None)])
			except ValueError:
				return None

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

	def SetAlwaysGroupByColumn(self, column, rebuild = True):
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
			except IndexError as error:
				print("@SetAlwaysGroupByColumn", error)
				self.alwaysGroupByColumnIndex = -1
		else:
			self.alwaysGroupByColumnIndex = column

		while (self.columns[self.alwaysGroupByColumnIndex].isInternal):
			self.alwaysGroupByColumnIndex += 1

		if (rebuild):
			self.RebuildGroups()

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
		# Cull groups that aren't going to change
		groups = [x for x in groups if x.IsExpanded() != isExpanding]
		if not groups:
			return

		# Expand/collapse the groups
		for x in groups:
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
		# If the list isn't in report view or there are no space filling
		# columns, just return
		if (not self.InReportView()):
			return

		visibleColumns = set(x for x in self.columns.values() if not x.GetHidden())
		fixedColumns = set(x for x in visibleColumns if not x.GetSpaceFilling())
		freeColumns = visibleColumns - fixedColumns

		# Don't do anything if there are no space filling columns
		if (not freeColumns):
			return

		# Calculate how much free space is available in the control
		totalFixedWidth = sum(x.column.GetWidth() for x in fixedColumns)
		if ('phoenix' in wx.PlatformInfo):
			freeSpace = max(0, self.GetClientSize()[0] - totalFixedWidth)
		else:
			freeSpace = max(0, self.GetClientSizeTuple()[0] - totalFixedWidth)

		# Calculate the total number of slices the free space will be divided into
		totalProportion = sum(x.freeSpaceProportion for x in freeColumns)

		# Space filling columns that would escape their boundary conditions are treated as fixed size columns
		columnsToResize = []
		for col in freeColumns:
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
			# self.UpdateUnsorted(preserveExpansion = preserveExpansion)
			self.RebuildGroups(preserveExpansion = preserveExpansion)
			self.model.ItemsAdded(modelObjects)
		finally:
			self.Thaw()

		if (self.showGroups):
			#Groups not updating children correctly, but rebuilding it all over again fixes it
			#TO DO: Fix self.model.ItemsAdded for groups
			self.model.Cleared()

	def RemoveObject(self, modelObject):
		"""
		Remove the given object from our collection of objects.
		"""
		self.RemoveObjects([modelObject])

	def RemoveObjects(self, modelObjects, preserveExpansion = True):
		"""
		Remove the given collections of objects from our collection of objects.
		"""

		try:
			self.Freeze()

			removedObjects = []
			for item in modelObjects:
				if (item in self.modelObjects):
					self.modelObjects.remove(item)
					removedObjects.append(item)

			self.RebuildGroups(preserveExpansion = preserveExpansion)
			self.model.ItemsDeleted(None, removedObjects)
		finally:
			self.Thaw()

		if (self.showGroups):
			#Groups not updating children correctly, but rebuilding it all over again fixes it
			#TO DO: Fix self.model.ItemsDeleted for groups
			self.model.Cleared()

	def EnsureVisible(self, modelObject, column = None):
		"""
		Make sure the user can see the given model object.
		"""

		item = self.model.ObjectToItem(modelObject)

		if (column is not None):
			column = self.columns[column].column

		super().EnsureVisible(item, column = column)

	def RepopulateList(self):
		"""
		Completely rebuild the contents of the list control
		"""

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
		if (not self.showGroups):
			return

		groups = self._BuildGroups(preserveExpansion = preserveExpansion)
		self._SetGroups(groups)

	def _BuildGroups(self, modelObjects = None, preserveExpansion = True):
		"""
		Partition the given list of objects into DataListGroups depending on the given groupBy column.

		Returns the created collection of DataListGroups
		"""
		if (modelObjects is None):
			modelObjects = self.modelObjects

		if (preserveExpansion):
			expanded = {}
			for group in self.groups:
				expanded[group.key] = group.IsExpanded()

		groupingColumn = self.GetGroupByColumn()
		assert (not groupingColumn.isInternal)

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

		groups = list(groupMap.values())

		if (self.GetShowItemCounts()):
			self._BuildGroupTitles(groups, groupingColumn)

		# Let the world know that we are creating the given groups
		event = DOLVEvent.GroupCreationEvent(self, groups)
		self.GetEventHandler().ProcessEvent(event)

		return event.groups

	def _SetGroups(self, groups):
		"""
		Present the collection of DataListGroups in this control.
		"""
		self.groups = groups
		self.RepopulateList()

	def _BuildGroupTitles(self, groups, groupingColumn):
		"""
		Rebuild the titles of the given groups
		"""
		for x in groups:
			x.title = groupingColumn.GetGroupTitle(x, self.GetShowItemCounts())

	# ---Sorting-------------------------------------------------------#000000#FFFFFF

	def EnableSorting(self, column = None, state = True):
		"""
		Enable automatic sorting when the user clicks on a column title
		If *column* is None, applies to all columns.
		"""
		if (column is not None):
			self.columns[column].SetSortable(state)
		else:
			for column in self.columns.values():
				column.SetSortable(state)

	def DisableSorting(self, column = None, state = True):
		"""
		Disable automatic sorting when the user clicks on a column title
		If *column* is None, applies to all columns.
		"""

		self.EnableSorting(column = column, state = not state)

	def SortBy(self, newColumnIndex, ascending = True):
		"""
		Sort the items by the given column
		"""
		self.SetSortColumn(newColumnIndex, ascending = ascending, resortNow = True)

	def GetSortColumn(self, returnIndex = False):
		"""
		Return the column by which the rows of this control should be sorted
		"""

		column = self.GetSortingColumn()
		if (column is not None):
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
			if (item is not None):
				item.UnsetAsSortKey() #`UnsetAsSortKey` is the reverse of SetSortOrder and is called to indicate that this column is not used for sorting any longer.
				if (unsortOnNone):
					self.model.Cleared()
		
		if (resortNow):
			self.model.Resort()

	# def UpdateUnsorted(self, preserveExpansion = True):
	# 	if (self.unsortedFunction):
	# 		self.modelObjects = self.unsortedFunction(self.modelObjects)

	def SetUnsortedFunction(self, function, repopulate = True):
		"""
		Allows the user to define an order for the unsorted list.
		If None, the order of the items given will be used.
		Setting this to None will not change the defined order of objects already added.
		"""
		self.unsortedFunction = function

		if (repopulate):
			self.RepopulateList()

	def SetCompareFunction(self, function, repopulate = True):
		"""
		Allows the user to use a different compare function for sorting items.
		You can set this to None to use the default compare function again.

		The comparison function must accept two model objects as two parameters, the column it is in as another, and if the order is ascending as one more.
		ie: myCompare(item1, item2, column, ascending)
		The comparison function should return negative, null or positive value depending on whether the first item is less than, equal to or greater than the second one.
		If it returns None, the default compare function will be used.
		"""
		self.compareFunction = function
		self.model.SelectCompare()

		if (repopulate):
			self.RepopulateList()

	def SetGroupCompareFunction(self, function, repopulate = True):
		"""
		Allows the user to use a different compare function for sorting groups.
		You can set this to None to use the default compare function again.

		The comparison function must accept two DataListGroup objects as two parameters, the column it is in as another, and if the order is ascending as one more.
		ie: myCompare(item1, item2, column, ascending)
		The comparison function should return negative, null or positive value depending on whether the first item is less than, equal to or greater than the second one.
		If it returns None, the default compare function will be used.
		"""
		self.groupCompareFunction = function
		self.model.SelectCompare()

		if (repopulate):
			self.RepopulateList()

	#Editing
	def SetReadOnly(self, state = True):
		"""
		Makes the entire table editable/uneditable
		"""

		self.readOnly = state
		_state = (None, False)[self.readOnly]

		for column in self.columns.values():
			column.SetEditable(refreshColumn = False, changeVar = False, state = _state)

	def GetReadOnly(self):
		return self.readOnly

	def StartCellEdit(self, objectModel, defn):
		"""
		Start an edit operation on the given cell.
		"""

		if (self.readOnly):
			return

		self.EditItem(self.model.ObjectToItem(objectModel), defn.column)

	def _PossibleStartCellEdit(self, objectModel, defn):
		"""
		Start an edit operation on the given cell after performing some sanity checks.
		"""

		if (self.readOnly):
			return

		if (objectModel is None):
			return

		if (defn.column is None):
			return

		if (not defn.IsEditable()):
			return

		self.StartCellEdit(objectModel, defn)

	#-------------------------------------------------------------------------
	# Calculating

	# def GetSubItemRect(self, rowIndex, subItemIndex, flag):
	# 	"""
	# 	Poor mans replacement for missing wxWindows method.

	# 	The rect returned takes scroll position into account, so negative x and y are
	# 	possible.
	# 	"""
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

	#-------------------------------------------------------------------------
	# Copy / Paste

	def CopyObjectsToClipboard(self, modelObjects = None, columns = None, **kwargs):
		"""
		Put a textual representation of the given objects onto the clipboard.

		*modelObjects* should be a list of model objects to copy.
		If *modelObjects* is None, all rows will be copied.

		*columns* should be a list of the columns to copy values from.
		If *columns* is None, all columns will be copied.

		The following parameters can be overridden by providing them as a kwarg:
			clipSimple
			clipKeepAfterClose

			clipSuffix
			clipPrefix
			clipColumnSpacer

			clipRowPrefix
			clipRowSuffix
			clipRowSpacer

			clipGroup
			clipGroupPrefix
			clipGroupSuffix
			clipGroupSpacer

		If the parameter *clipKeepAfterClose* == True, the copied data will be kept
		after the program is closed (this may not work on Mac and Linux).
		This parameter can be a function that returns a bool and accepts the
		following parameters: copiedText.

		What amount of control the user has over what the data looks like is based on
		the paramter *clipSimple*.

		If *clipSimple* == True:
			By default, rows will be on separate lines and columns will be separated by tabs.
			The parameters *clipRowSpacer* and *clipColumnSpacer* can change this.

			If a group is copied, an extra new line and the name of that group will be
			placed on the clipboard.

			By default, a new line is appended to the clipboard.
			The parameter *clipSuffix* can change what (if anything) is added.
			The parameter *clipPrefix* can change append text to the start.

		If *clipSimple* == False:
			By default, rows will be on separate lines and columns will be separated by tabs.
			The parameters *clipRowSpacer* and *clipColumnSpacer* can change this.
			Each row is sandwiched between *clipRowPrefix* and *clipRowSuffix*.

			By default, a new line is appended to the clipboard.
			The parameter *clipSuffix* can change what (if anything) is added.
			The parameter *clipPrefix* can change append text to the start.

			The parameter *clipGroup* controls what happens if a group is copied.
				- *clipGroup* is None: The group will be ignored
				- *clipGroup* == True: All items in the group will be copied
				- *clipGroup* == False: The name of the group will be copied as a row

			Copied group content will be separated by *clipGroupSpacer*, and sandwiched between
			*clipGroupPrefix* and *clipGroupSuffix*. If any of thsoe three are None, their row
			counterpart will be used.

			The following can be functions that take the paramters that follow them:
				*clipPrefix*: modelObjects
				*clipSuffix*: modelObjects

				*clipRowPrefix*: modelObject
				*clipRowSuffix*: modelObject
				*clipRowSpacer*: previousObject, modelObject
				*clipColumnSpacer*: modelObject, previousColumn, column

				*clipGroup*: group
				*clipGroupPrefix*: group
				*clipGroupSuffix*: group
				*clipGroupSpacer*: previousGroup, group

		Also, the following is stored in the variable *copiedList*:
			Each row will be copied into a dictionary, where each column is a key and their value
			corresponds to the value of the cell of the column in that row. The key None contains the
			row item itself. Each row is added to a list.
		"""

		columns = columns or self.columns.values()
		modelObjects = modelObjects or self.modelObjects

		#Tell the world that copying will happen
		event = self.TriggerEvent(DOLVEvent.CopyingEvent, rows = modelObjects, columns = columns, returnEvent = True)
		if (event.IsVetoed()):
			return
		if ((not event.rows) or (not event.columns)):
			return

		log = []
		clipSimple = kwargs.pop("clipSimple", self.clipSimple)
		clipKeepAfterClose = kwargs.pop("clipKeepAfterClose", self.clipKeepAfterClose)
		
		clipSuffix = kwargs.pop("clipSuffix", self.clipSuffix)
		clipPrefix = kwargs.pop("clipPrefix", self.clipPrefix)
		clipColumnSpacer = kwargs.pop("clipColumnSpacer", self.clipColumnSpacer)

		clipRowPrefix = kwargs.pop("clipRowPrefix", self.clipRowPrefix)
		clipRowSuffix = kwargs.pop("clipRowSuffix", self.clipRowSuffix)
		clipRowSpacer = kwargs.pop("clipRowSpacer", self.clipRowSpacer)

		clipGroup = kwargs.pop("clipGroup", self.clipGroup)
		clipGroupPrefix = kwargs.pop("clipGroupPrefix", self.clipGroupPrefix)
		clipGroupSuffix = kwargs.pop("clipGroupSuffix", self.clipGroupSuffix)
		clipGroupSpacer = kwargs.pop("clipGroupSpacer", self.clipGroupSpacer)

		def logRow(row):
			nonlocal self, event, log

			newEvent = self.TriggerEvent(DOLVEvent.CopyEvent, row = row, columns = (*event.columns,), returnEvent = True)
			if (newEvent.IsVetoed() or (not newEvent.columns) or (newEvent.row is None)):
				return None, []

			contents = {None: newEvent.row}
			for column in newEvent.columns:
				contents[column.GetIndex()] = column.GetValue(row)
			log.append(contents)

			return newEvent.row, newEvent.columns, newEvent.text

		def logGroup(group, _clipGroup = None):
			nonlocal self, log

			pass

			# if (_clipGroup is not None):
			# 	log.append({None: group})

		def getSimpleText():
			nonlocal self, event

			lines = []
			for row in event.rows:
				if (isinstance(row, DataListGroup)):
					logGroup(row, clipGroup = clipGroup)
					lines.append(f"\n{row.title}")
				else:
					_row, columns, _text = logRow(row)
					if (_row is not None):
						if (_text is not None):
							lines.append(_text)
						else:
							lines.append(f"{clipColumnSpacer or ''}".join((column.GetStringValue(_row) for column in columns)))

			text = f"{clipPrefix or ''}"
			text += f"{clipRowSpacer or ''}".join(lines)
			text += f"{clipSuffix or ''}"
			return text

		def getRowText(row):
			nonlocal self

			_row, columns, _text = logRow(row)
			if (_row is None):
				return ""
			if (_text is not None):
				return _text

			text = f"{_Munge(clipRowPrefix, source = row, returnMunger_onFail = True)}"

			previousItem = None
			for column in columns:
				if (previousItem is not None):
					text += f"{_Munge(clipColumnSpacer, source = _row, extraArgs = [previousItem, column], returnMunger_onFail = True)}"
				text += column.GetStringValue(_row)
				previousItem = column

			text += f"{_Munge(clipRowSuffix, source = _row, returnMunger_onFail = True)}"
			return text

		def getGroupText(group, _clipGroup):
			nonlocal self

			logGroup(group, clipGroup = _clipGroup)
			text = f"{_Munge(clipGroupPrefix, source = group, returnMunger_onFail = True)}"

			if (not _clipGroup):
				text += f"{group.title}"
			else:
				lines = []
				for row in group.modelObjects:
					lines.append((row, getRowText(row)))
				text += joinLines(lines)

			text += f"{_Munge(clipGroupSuffix, source = group, returnMunger_onFail = True)}"
			return text

		def joinLines(lines):
			nonlocal self

			text = ""

			previousItem = None
			for item, line in lines:
				if (previousItem is not None):
					if (isinstance(item, DataListGroup) and (clipGroupSpacer is not None)):
						spacer = clipGroupSpacer
					else:
						spacer = clipRowSpacer or ''
					text += f"{_Munge(spacer, source = previousItem, extraArgs = [item], returnMunger_onFail = True)}"
				text += line
				previousItem = item

			return text

		##########################################################

		clipSimple = True #TO DO: Finish non-simple version

		#Make a text version of the values
		lines = []
		if (event.text is not None):
			text = event.text
		elif (clipSimple):
			text = getSimpleText()
		else:
			text = f"{_Munge(clipPrefix, source = event.rows, returnMunger_onFail = True)}"

			for row in event.rows:
				if (not isinstance(row, DataListGroup)):
					lines.append((row, getRowText(row)))
				else:
					clipGroup = _Munge(clipGroup, source = row, returnMunger_onFail = True)
					if (clipGroup is not None):
						lines.append((row, getGroupText(row, clipGroup)))
			text += joinLines(lines)
			text += f"{_Munge(clipSuffix, source = event.rows, returnMunger_onFail = True)}"

		#Tell the world that copying is done
		event = self.TriggerEvent(DOLVEvent.CopiedEvent, log = log, text = text, rows = event.rows, columns = event.columns, returnEvent = True)
		self.copiedList = event.log or []
		_text = event.text or ""

		#Place text on clipboard
		clipboard = wx.TextDataObject()
		clipboard.SetText(_text)

		if (wx.TheClipboard.Open()):
			if (wx.TheClipboard.SetData(clipboard) and _Munge(clipKeepAfterClose, source = _text, returnMunger_onFail = True)):
				wx.TheClipboard.Flush()
			wx.TheClipboard.Close()
		else:
			wx.MessageBox("Can't open the clipboard", "Error")

	def CopySelectionToClipboard(self, entireRow = True):
		"""
		Copy the selected objects to the clipboard.
		"""

		if (entireRow):
			columns = self.columns.values()
		else:
			columns = [self.lastClicked[1]]

		self.CopyObjectsToClipboard(list(self.YieldSelected()), columns)

	def PasteClipboardToSelection(self, entireRow = True):
		"""
		Copy the selected objects to the clipboard.
		"""

		self.PasteObjectsFromClipboard(list(self.YieldSelected()), entireRow = entireRow)

	def PasteObjectsFromClipboard(self, modelObjects, entireRow = True, track = True, resortNow = True):
		"""
		Paste what was copied into the selected row(s).

		*entireRow* determines which column data is pasted to.
			- If *entireRow* == True: All valid columns will be pasted to
			- If *entireRow* == False: Only the column of the last cell clicked will be pasted to

		The parameter *pasteWrap* determines what happens if there are more rows than content to paste.
			- If *pasteWrap* == True: Use the first item in the copiedList and keep going from there 
			- If *pasteWrap* == False: Skip the rest of the rows

		The paramter *pasteInSelection* determines what happens if there are less rows than content to paste.
			- If *pasteInSelection* == True: Only pastes what will fit 
			- If *pasteInSelection* == False: Keeps going down the list until it reaches the bottom or there is no content left

		The paramter *pasteToCell* determines what happens if *copiedList* == [] and the copied text
		is not formatted for the columns.
			- If *pasteToCell* == True: Paste the value to the cell last clicked
			- If *pasteToCell* == False: Paste the value to the primary column
		"""

		event = self.TriggerEvent(DOLVEvent.PastingEvent, rows = modelObjects, column = self.lastClicked[1], log = [*self.copiedList], returnEvent = True)
		if (event.IsVetoed()):
			return
		if (not event.rows):
			return

		appliedLog = {}
		log = event.log or []
		columnClicked = self.GetColumn(event.column)

		def getClipboardText():
			clipboard = wx.TextDataObject()
			if (wx.TheClipboard.Open()):
				wx.TheClipboard.GetData(clipboard)
				wx.TheClipboard.Close()
			else:
				wx.MessageBox("Can't open the clipboard", "Error")
				return
			return clipboard.GetText()

		def formatLines(lines):
			nonlocal self, event

			if (not self.pasteWrap):
				return

			def yieldIndex():
				nonlocal lines

				while True:
					for index in range(len(lines)):
						yield index

			count = len(event.rows)
			indexGenerator = yieldIndex()
			while (len(lines) < count):
				index = next(indexGenerator)
				lines.append(lines[index])

		def yieldRows():
			nonlocal self, event

			for row in event.rows:
				yield row

			if (self.pasteInSelection):
				return

			while True:
				row = self.GetNext(row, wrap = False)
				if (row is None):
					break
				yield row

		def pasteSimple(text):
			nonlocal self

			_text = text.lstrip(f"{self.clipPrefix or ''}").rstrip(f"{self.clipSuffix or ''}")
			if (not self.clipRowSpacer):
				lines = [_text]
			else:
				lines = _text.split(f"{self.clipRowSpacer}")
			formatLines(lines)

			rows = yieldRows()
			for i, line in enumerate(lines):
				try:
					row = next(rows)
				except StopIteration:
					break

				if (not self.clipColumnSpacer):
					columns = [line]
				else:
					columns = line.split(f"{self.clipColumnSpacer}")

				if (len(columns) == 1):
					if (self.pasteToCell):
						pasteCell(row, columns[0])
					else:
						tryValue(row, self.GetPrimaryColumn(), columns[0])
					continue

				if ((not entireRow) and (columnClicked is not None)):
					index = columnClicked.GetIndex()
					if (index in columns):
						tryValue(row, self.GetColumn(index), columns[index])
					continue

				for index, value in enumerate(columns):
					column = self.GetColumn(index)
					if (column.isInternal):
						continue
					if (not isinstance(column.GetValue(row), type(value))):
						try:
							value = ast.literal_eval(value)
						except Exception as error:
							print("@pasteSimple", f"Malformed paste string for column {column.title} as {value} to replace {column.GetValue(row)}")
							continue
					column.SetValue(row, value)

		def pasteCell(row, value):
			nonlocal self, columnClicked

			if (columnClicked is None):
				return
			
			tryValue(row, columnClicked, value)

		def tryValue(row, column, value):
			self._paste_ignoreSort = True
			self._undo_listenForCheckBox = False
			try:
				oldValue = column.GetValue(row)
				event = self.TriggerEvent(DOLVEvent.PasteEvent, row = row, column = column, value = value, editCanceled = False, returnEvent = True)
				if (event.IsVetoed()):
					return
				if ((event.row is None) or (event.column is None)):
					return

				_row = self.model.ObjectToItem(event.row)
				_column = event.column.GetIndex()
				if (event.wasHandled):
					self.model.ValueChanged(_row, _column)
					logApplication(event.row, event.column, oldValue, event.value)
					return

				if (event.column.renderer.type in ["bmp", "multi_bmp", "button"]):
					return
				if (event.column.isInternal):
					return

				try:
					self.model.ChangeValue(event.value, _row, _column)
					self.model.GetValue(_row, _column)
				except Exception as error:
					print("@tryValue", error)
					self.model.ChangeValue(oldValue, _row, _column)
				else:
					logApplication(event.row, event.column, oldValue, event.value)
			finally:
				self._paste_ignoreSort = False
				self._undo_listenForCheckBox = True

		def logApplication(row, column, oldValue, value):
			if (row not in appliedLog):
				appliedLog[row] = []
			appliedLog[row].append([column, oldValue, value])

		def pasteList(copiedList):
			nonlocal self, entireRow, columnClicked

			rows = yieldRows()
			formatLines(copiedList)
			for i, line in enumerate(copiedList):
				try:
					row = next(rows)
				except StopIteration:
					break

				if ((not entireRow) and (columnClicked is not None)):
					index = columnClicked.GetIndex()
					if (index in line):
						tryValue(row, columnClicked, line[index])
					elif (columnClicked.valueGetter in line):
						tryValue(row, columnClicked, line[columnClicked.valueGetter])
					continue

				for index, value in line.items():
					if (index is None):
						continue
					tryValue(row, self.GetColumn(index), value)

		#########################################################

		try:
			if (log):
				return pasteList(log)

			text = getClipboardText()
			if (text and self.clipSimple):
				return pasteSimple(text)
		finally:
			if (resortNow and appliedLog):
				self.model.Resort()
			if (track):
				self._TrackPaste(appliedLog)

	#-------------------------------------------------------------------------
	# Undo / Redo

	def _TrackAction(self, action):
		"""
		Remembers what was done, and what can be done to undo it.
		"""

		event = self.TriggerEvent(DOLVEvent.UndoTrackEvent, action = action, type = action.GetType(), returnEvent = True)
		if (event.IsVetoed() or (event.action is None)):
			return

		if (self.redoHistory):
			self.redoHistory = []
			self.TriggerEvent(DOLVEvent.RedoEmptyEvent)
		
		if (not self.undoHistory):
			self.TriggerEvent(DOLVEvent.UndoFirstEvent)
		elif (len(self.undoHistory) >= self.undoCap):
			del self.undoHistory[0]

		self.undoHistory.append(event.action)

	def _TrackEdit(self, row, column, oldValue, newValue):
		action = UndoEdit(self, row, column, oldValue, newValue)
		self._TrackAction(action)

	def _TrackPaste(self, log):
		action = UndoPaste(self, log)
		self._TrackAction(action)

	def SetUndoHistory(self, undoHistory = []):
		"""
		Changes the undo history, while making sure to trigger the appropriate events.
		"""

		if (not undoHistory):
			if (self.undoHistory):
				self.TriggerEvent(DOLVEvent.UndoEmptyEvent)
		else:
			if (not self.undoHistory):
				self.TriggerEvent(DOLVEvent.UndoFirstEvent)

		self.undoHistory = undoHistory or []

	def SetRedoHistory(self, redoHistory = []):
		"""
		Changes the redo history, while making sure to trigger the appropriate events.
		"""

		if (not redoHistory):
			if (self.redoHistory):
				self.TriggerEvent(DOLVEvent.RedoEmptyEvent)
		else:
			if (not self.redoHistory):
				self.TriggerEvent(DOLVEvent.RedoFirstEvent)

		self.redoHistory = redoHistory or []

	def Undo(self):
		"""
		Undoes the last action in the undo history.
		"""

		self._undo_listenForCheckBox = False
		try:
			if (not self.undoHistory):
				return

			action = self.undoHistory.pop()
			if (not action.undo()):
				self.undoHistory.append(action)
				return

			if (not self.undoHistory):
				self.TriggerEvent(DOLVEvent.UndoEmptyEvent, type = action.GetType())
			if (not self.redoHistory):
				self.TriggerEvent(DOLVEvent.RedoFirstEvent, type = action.GetType())

			self.redoHistory.append(action)
		finally:
			self._undo_listenForCheckBox = True

	def Redo(self):
		"""
		Redoes the last action in the redo history.
		"""

		self._undo_listenForCheckBox = False
		try:
			if (not self.redoHistory):
				return

			action = self.redoHistory.pop()
			if (not action.redo()):
				self.redoHistory.append(action)
				return

			if (not self.redoHistory):
				self.TriggerEvent(DOLVEvent.RedoEmptyEvent, type = action.GetType())
			if (not self.undoHistory):
				self.TriggerEvent(DOLVEvent.UndoFirstEvent, type = action.GetType())

			self.undoHistory.append(action)
		finally:
			self._undo_listenForCheckBox = True

	#-------------------------------------------------------------------------
	# Event handling

	def _HandleChar(self, event):

		key = event.GetUnicodeKey()
		if (key == wx.WXK_NONE):
			key = event.GetKeyCode()
		
		if (self.key_scroll):
			if (key == wx.WXK_UP):
				self.SelectPrevious()
				return
			if (key == wx.WXK_DOWN):
				self.SelectNext()
				return
		if (self.key_expand):
			if (key == wx.WXK_LEFT):
				self.CollapseAll(self.GetSelectedGroups())
				return
			if (key == wx.WXK_RIGHT):
				self.ExpandAll(self.GetSelectedGroups())
				return
		
		if (self.key_copy):
			if ((key == wx.WXK_CONTROL_C)):
				if (self.key_copyEntireRow is not None):
					self.CopySelectionToClipboard(entireRow = self.key_copyEntireRow)
				else:
					self.CopySelectionToClipboard(entireRow = event.ShiftDown())
				return
		if (self.key_paste):
			if ((key == wx.WXK_CONTROL_V)):
				if (self.key_pasteEntireRow is not None):
					self.PasteClipboardToSelection(entireRow = self.key_pasteEntireRow)
				else:
					self.PasteClipboardToSelection(entireRow = event.ShiftDown())
				return
		if (self.key_selectAll):
			if (key == wx.WXK_CONTROL_A):
				self.SelectAll(override_singleSelect = False)
				return
			if (key == wx.WXK_ESCAPE):
				self.UnselectAll()
				return
		if (self.key_undo):
			if (key == wx.WXK_CONTROL_Z):
				if (event.ShiftDown()):
					self.Redo()
				else:
					self.Undo()
				return
			if (key == wx.WXK_CONTROL_Y):
				self.Redo()
				return
		
		if (self.key_edit):
			if (key in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]):
				self._PossibleStartCellEdit(self.GetCurrentObject(), self.GetPrimaryColumn())
				return

		event.Skip()

	# def _HandleTypingEvent(self, event):
	# 	"""
	# 	"""
	# 	if self.GetItemCount() == 0 or self.GetColumnCount() == 0:
	# 		return False

	# 	if event.GetModifiers() != 0 and event.GetModifiers() != wx.MOD_SHIFT:
	# 		return False

	# 	if event.GetKeyCode() > wx.WXK_START:
	# 		return False

	# 	if event.GetKeyCode() in (wx.WXK_BACK, wx.WXK_DELETE):
	# 		self.searchPrefix = u""
	# 		return True

	# 	# On which column are we going to compare values? If we should search on the
	# 	# sorted column, and there is a sorted column and it is searchable, we use that
	# 	# one, otherwise we fallback to the primary column
	# 	if self.typingSearchesSortColumn and self.GetSortColumn(
	# 	) and self.GetSortColumn().isSearchable:
	# 		searchColumn = self.GetSortColumn()
	# 	else:
	# 		searchColumn = self.GetPrimaryColumn()

	# 	# On Linux, GetUnicodeKey() always returns 0 -- on my 2.8.7.1
	# 	# (gtk2-unicode)
	# 	uniKey = event.UnicodeKey
	# 	if uniKey == 0:
	# 		uniChar = six.unichr(event.KeyCode)
	# 	else:
	# 		# on some versions of wxPython UnicodeKey returns the character
	# 		# on others it is an integer
	# 		if isinstance(uniKey, int):
	# 			uniChar = six.unichr(uniKey)
	# 		else:
	# 			uniChar = uniKey
	# 	if not self._IsPrintable(uniChar):
	# 		return False

	# 	# On Linux, event.GetTimestamp() isn't reliable so use time.time()
	# 	# instead
	# 	timeNow = time.time()
	# 	if (timeNow - self.whenLastTypingEvent) > self.SEARCH_KEYSTROKE_DELAY:
	# 		self.searchPrefix = uniChar
	# 	else:
	# 		self.searchPrefix += uniChar
	# 	self.whenLastTypingEvent = timeNow

	# 	#self.__rows = 0
	# 	self._FindByTyping(searchColumn, self.searchPrefix)
	# 	# log "Considered %d rows in %2f secs" % (self.__rows, time.time() -
	# 	# timeNow)

	# 	return True

	def _HandleColumnClick(self, event):
		"""
		The user has clicked on a column title.
		Sorts by ascending, descending, then unsorted.
		"""

		column = event.GetDataViewColumn()

		if ((not self.GetSortingColumn()) or (column.IsSortOrderAscending())):
			event.Skip()
		else:
			index = column.GetModelColumn()
			columnHandle = self.columns.get(column.GetModelColumn(), None)

			event = DOLVEvent.SortingEvent(self, columnHandle, index, None)
			self.GetEventHandler().ProcessEvent(event)
			if (event.wasHandled or event.IsVetoed()):
				return

			self.model.sortCounter = None
			column.UnsetAsSortKey() #`UnsetAsSortKey` is the reverse of SetSortOrder and is called to indicate that this column is not used for sorting any longer.
			self.model.Cleared()

			self.TriggerEvent(DOLVEvent.SortedEvent, column = columnHandle, index = index, ascending = None)

	def _HandleSize(self, event):
		"""
		The ListView is being resized
		"""
		# self._PossibleFinishCellEdit()
		event.Skip()
		self._ResizeSpaceFillingColumns()

	def _HandleOverlays(self, event):
		"""
		Draws all overlays on top of the DataList.
		"""

		def drawEmptyList(item, message):
			"""
			Draws the empty list message.
			"""

			self.overlayEmptyListMsg.Reset()
			
			dc = wx.ClientDC(item)
			dc.Clear()
			odc = wx.DCOverlay(self.overlayEmptyListMsg, dc)
			odc.Clear()

			if ('wxMac' not in wx.PlatformInfo):
				dc = wx.GCDC(dc) #Mac's DC is already the same as a GCDC

			size = item.GetClientSize()
			_drawText(dc, text = message, align = wx.Rect(0, 0, size[0], size[1]), x_align = "center", color = wx.LIGHT_GREY, font = self.emptyListFont, wrap = True)

			del odc  # Make sure the odc is destroyed before the dc is.

		####################################################

		if (not self.modelObjects):
			wx.CallAfter(drawEmptyList, event.GetEventObject(), self.emptyListMsg)
		elif (not self.model.rootLength):
			wx.CallAfter(drawEmptyList, event.GetEventObject(), self.emptyListFilterMsg or self.emptyListMsg)
		event.Skip()

	#Event Relays
	def _getRelayInfo(self, relayEvent):
		kwargs = {}
		if (isinstance(relayEvent, wx.dataview.DataViewEvent)):
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
			kwargs["editCanceled"] = relayEvent.IsEditCancelled()

			kwargs["value"] = relayEvent.GetValue()
			if (isinstance(kwargs["value"], wx.dataview.DataViewIconText)):
				kwargs["value"] = kwargs["value"].GetText()
		else:
			kwargs["index"] = relayEvent.GetColumn()
		return kwargs

	def TriggerEvent(self, eventFunction, returnEvent = False, **kwargs):
		"""
		Allows the user to easily trigger an event remotely.

		Example Use: myOLV.TriggerEvent(ObjectListView.SelectionChangedEvent, row = newItem)
		"""

		newEvent = eventFunction(self, **kwargs)
		self.GetEventHandler().ProcessEvent(newEvent)

		if (returnEvent):
			return newEvent
		if (isinstance(newEvent, DOLVEvent.VetoableEvent)):
			if (newEvent.IsVetoed()):
				return False
			# return
		return True

	def _RelayEvent(self, eventFrom, eventTo, info = None):
		if (not info):
			info = self._getRelayInfo(eventFrom)
		answer = self.TriggerEvent(eventTo, **info)

		if (answer):
			eventFrom.Skip()
		elif (answer is not None):
			eventFrom.Veto()
		return answer, info

	def _RelaySelectionChanged(self, relayEvent):
		model = relayEvent.GetModel()

		#Record location
		_row, _column = self.HitTest(self.ScreenToClient(wx.GetMousePosition()))
		if (_row.IsOk()):
			self.lastClicked = (model.ItemToObject(_row), self.GetColumn(_column))
		else:
			self.lastClicked = (None, self.GetColumn(_column))

		#Do not fire this event if that row is already selecetd
		try:
			row = model.ItemToObject(relayEvent.GetItem())
		except TypeError:
			#Deselection with no new selection
			relayEvent.Skip()
			return

		if (row != self.lastSelected):
			self.lastSelected = row
			if (isinstance(row, DataListGroup)):
				self._RelayEvent(relayEvent, DOLVEvent.GroupSelectedEvent)
			else:
				self._RelayEvent(relayEvent, DOLVEvent.CellLeftClickEvent)
				self._RelayEvent(relayEvent, DOLVEvent.SelectionChangedEvent)
		else:
			if (not isinstance(row, DataListGroup)):
				self._RelayEvent(relayEvent, DOLVEvent.CellLeftClickEvent)

			relayEvent.Skip()

	def _RelayCellContextMenu(self, relayEvent):
		if (self.showContextMenu):
			rowInfo = self._getRelayInfo(relayEvent)

			#Check if the user clicked on empty space instead of on an item
			if (rowInfo["column"] is not None):
				self.contextMenu.SetRow(rowInfo["row"])
				self.contextMenu.SetColumn(rowInfo["column"])
				if (self.contextMenu.Show()):
					relayEvent.Skip()
					return
		self._RelayEvent(relayEvent, DOLVEvent.CellRightClickEvent)

	def _RelayCellActivated(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.CellActivatedEvent)

	def _RelayColumnHeaderLeftClick(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.ColumnHeaderLeftClickEvent)

	def _RelayColumnHeaderRightClick(self, relayEvent):
		if (self.showColumnContextMenu):
			rowInfo = self._getRelayInfo(relayEvent)

			#Check if the user clicked on empty space instead of on an item
			if (rowInfo["column"] is not None):
				self.columnContextMenu.SetColumn(rowInfo["column"])
				if (self.columnContextMenu.Show()):
					relayEvent.Skip()
					return

		self._RelayEvent(relayEvent, DOLVEvent.ColumnHeaderRightClickEvent)

	def _RelaySorted(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.SortedEvent)

	def _RelayReordering(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.ReorderingEvent)

	def _RelayReordered(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.ReorderedEvent)

	def _RelayReorderCancel(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.ReorderCancelEvent)

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
		if (self.readOnly or (not self.columns[relayEvent.GetDataViewColumn().GetModelColumn()].isEditable)):
			relayEvent.Veto()
		else:
			self._RelayEvent(relayEvent, DOLVEvent.EditCellStartingEvent)

	def _RelayEditCellStarted(self, relayEvent):
		self._RelayEvent(relayEvent, DOLVEvent.EditCellStartedEvent)

	def _RelayEditCellFinishing(self, relayEvent):
		info = self._getRelayInfo(relayEvent)
		column = info["column"]
		if (column is not None):
			row = info["row"]
			oldValue = column.GetValue(row)

		self._RelayEvent(relayEvent, DOLVEvent.EditCellFinishingEvent, info = info)
		
		if ((column is not None) and (relayEvent.IsAllowed())):
			self._TrackEdit(row, column, oldValue, info["value"])

	def _RelayEditCellFinished(self, relayEvent):
		info = self._getRelayInfo(relayEvent)
		column = info["column"]
		if (column is not None):
			row = info["row"]
			oldValue = column.GetValue(row)

		self._RelayEvent(relayEvent, DOLVEvent.EditCellFinishedEvent, info = info)

		if (self._undo_listenForCheckBox and (column is not None) and (relayEvent.IsAllowed()) and 
			(isinstance(column.renderer, (wx.dataview.DataViewToggleRenderer, Renderer_CheckBox)))):

			value = column.GetValue(row)
			self._TrackEdit(row, column, oldValue, value)

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

	def __init__(self, title = "title", align = "left", width = -1, valueGetter = None, sortGetter = None, 
		imageGetter = None, stringConverter = None, valueSetter = None, isSortable = True, isEditable = True, 
		isReorderable = True, isResizeable = True, isHidden = False, isSpaceFilling = False, isSearchable = True, 
		fixedWidth = None, minimumWidth = -1, maximumWidth = -1, 
		checkStateGetter = None, 
		checkStateSetter = None, useBinarySearch = None, headerImage = -1, groupKeyGetter = None, 
		groupKeyConverter = None, groupSortGetter = None, useInitialLetterForGroupKey = False, 
		groupTitleSingleItem = None, groupTitlePluralItems = None, renderer = None, rendererArgs = [], rendererKwargs = {}):
		"""
		Create a new ColumnDefn using the given attributes.
		"""
		self.title = title
		self.align = align
		self.column = None
		self.valueGetter = valueGetter
		self.sortGetter = sortGetter
		self.imageGetter = imageGetter
		self.stringConverter = stringConverter
		self.valueSetter = valueSetter
		self.isSpaceFilling = isSpaceFilling
		self._isSpaceFilling = False #Allows _Munge to be used for isSpaceFilling
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
			olv.InsertColumn(index, self)

	def GetWidth(self):
		"""
		Return the width of the column.
		"""
		return self.column.GetWidth()

	def SetWidth(self, width = None):
		"""
		Change the width of the column.
		If 'width' is None, it will auto-size.
		"""
		if (width is None):
			width = wx.LIST_AUTOSIZE

		return self.column.SetWidth(_Munge(width, source = self, returnMunger_onFail = True))

	def GetAlignment(self):
		"""
		Return the alignment that this column uses
		"""
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

	def GetIndex(self):
		return self.column.GetModelColumn()

	def SetSortable(self, state = None):
		if (state is not None):
			self.isSortable = state

		self.column.SetSortable(_Munge(self.isSortable, source = self, returnMunger_onFail = True))

	def GetSortable(self):
		return self.column.IsSortable()

	def SetEditable(self, state = None, refreshColumn = True, changeVar = True):
		if (changeVar and (state is not None)):
			self.isEditable = state

		if (_Munge(self.isEditable, source = self, returnMunger_onFail = True)):
			key = "edit"
		else:
			key = "nonEdit"

		self.SetRenderer(self.renderer.Clone(mode = rendererCatalogue[self.renderer.type][key]), refreshColumn = refreshColumn)

	def GetEditable(self):
		return self.renderer.Mode == rendererCatalogue[self.renderer.type]["edit"]

	def SetReorderable(self, state = None):
		if (state is not None):
			self.isReorderable = state

		self.column.SetReorderable(_Munge(self.isReorderable, source = self, returnMunger_onFail = True))

	def GetReorderable(self):
		return self.column.IsReorderable()

	def SetResizeable(self, state = None):
		if (state is not None):
			self.isResizeable = state

		self.column.SetResizeable(_Munge(self.isResizeable, source = self, returnMunger_onFail = True))

	def GetResizeable(self):
		return self.column.IsResizeable()

	def SetHidden(self, state = None):
		if (state is not None):
			self.isHidden = state

		self.column.SetHidden(_Munge(self.isHidden, source = self, returnMunger_onFail = True))

	def GetHidden(self):
		return self.column.IsHidden()

	def SetSpaceFilling(self, state = None):
		if (state is not None):
			self.isSpaceFilling = state

		self._isSpaceFilling = _Munge(self.isSpaceFilling, source = self, returnMunger_onFail = True)

	def GetSpaceFilling(self):
		return self._isSpaceFilling

	#-------------------------------------------------------------------------
	# Value accessing

	def GetValue(self, modelObject):
		"""
		Return the value for this column from the given modelObject
		"""
		return _Munge(self.valueGetter, source = modelObject)

	def GetStringValue(self, modelObject):
		"""
		Return a string representation of the value for this column from the given modelObject
		"""
		value = self.GetValue(modelObject)

		return _StringToValue(value, self.stringConverter, extraArgs = [self])

	def GetGroupKey(self, modelObject):
		"""
		Return the group key for this column from the given modelObject
		"""
		if (self.groupKeyGetter is None):
			key = self.GetValue(modelObject)
		else:
			key = _Munge(self.groupKeyGetter, source = modelObject)
		if (self.useInitialLetterForGroupKey):
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
		# there isn't a special key converter, use the normal aspect to string converter.
		if (self.groupKeyGetter is None and self.groupKeyConverter is None):
			return _StringToValue(groupKey, self.stringConverter, extraArgs = [self])
		else:
			return _StringToValue(groupKey, self.groupKeyConverter, extraArgs = [self])

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
		if (self.valueSetter is None):
			return _SetValueUsingMunger(modelObject, value, self.valueGetter)
		else:
			return _SetValueUsingMunger(modelObject, value, self.valueSetter)

	#-------------------------------------------------------------------------
	# Width management

	def CalcBoundedWidth(self, width):
		"""
		Calculate the given width bounded by the (optional) minimum and maximum column widths
		"""
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
		return self.renderer

	def SetRenderer(self, renderer, *args, refreshColumn = True, **kwargs):
		"""
		Applies the provided renderer
		"""
		global rendererCatalogue

		renderer = _Munge(renderer, source = self, returnMunger_onFail = True)
		try:
			self.renderer = rendererCatalogue[renderer]["class"](*args, **kwargs)
		except (AttributeError, KeyError):
			#https://github.com/wxWidgets/Phoenix/blob/master/samples/dataview/CustomRenderer.py
			self.renderer = renderer

		if (refreshColumn):
			self.RefreshColumn()

class ContextMenu(object):
	"""
	A wrapper for the context menu that appears when the user right-clicks on an item.
	"""

	def __init__(self, olv):
		"""
		Create a context menu with the given attributes.
		"""

		super().__init__()

		self.olv = olv
		self.row = None
		self.column = None
		self.contents = []    #[id]
		self.idCatalogue = {} #{id: text}
		self.exclusive_x = {} #{id: [row]}
		self.exclusive_y = {} #{id: [column]}
		self.conditions = {}  #{id: function}
		self.functions = {}   #{id: function}
		self.checks = {}      #{id: state}
		self.radios = {}      #{id: state}

	def SetRow(self, row):
		"""
		Determines what row the context menu applies to.
		"""

		self.row = row

	def SetColumn(self, column):
		"""
		Determines what column the context menu applies to.
		"""

		if (not isinstance(column, DataColumnDefn)):
			column = self.olv.columns[column]
		self.column = column

	def AddItem(self, text = None, function = None, row = None, column = None, condition = None, check = None, radio = None):
		"""
		Add an item to the context menu.

		If *text* is not given, the menu item will be a separator.
		If *check* is given, the menu item will have a check box with the state of *check*
		If *check* is given, the menu item will have a radio button with the state of *check*

		If *function* is given, that function will run when the item is clicked.
		The function must accept the following args: row, column, item

		If *condition* is given, it must be a function that will decide if the item should appear or not.
		The function must accept the following args: row, column, text
		If the function returns True, the item will be added

		If *row* is given, this item will only show for that row; a list of rows can be given.
		If *column* is given, this item will only show for that column; a list of columns can be given.
		"""

		item_id = wx.NewId()
		self.contents.append(item_id)
		self.idCatalogue[item_id] = text

		#Setup Type
		if (check is not None):
			self.checks[item_id] = check

		if (radio is not None):
			self.radios[item_id] = radio

		#Setup Conditional
		if (row is not None):
			self.exclusive_x[item_id] = set()
			for _row in row if (isinstance(row, (list, tuple, set, types.GeneratorType))) else [row]:
				self.exclusive_x[item_id].add(_row)

		if (column is not None):
			self.exclusive_y[item_id] = set()
			for _column in column if (isinstance(column, (list, tuple, set, types.GeneratorType))) else [column]:
				if (not isinstance(_column, DataColumnDefn)):
					_column = self.olv.columns[_column]
				self.exclusive_y[item_id].add(_column)
		
		if (condition is not None):
			self.conditions[item_id] = condition

		#Bind Functions
		self.olv.Bind(wx.EVT_MENU, self._handleItemClicked, id = item_id)

		if (function is not None):
			self.functions[item_id] = function

	def _handleItemClicked(self, event):
		"""
		Handles a clicked item.
		"""

		item_id = event.GetId()
		menu = event.GetEventObject()
		item = menu.FindItemById(item_id)

		answer = self.olv.TriggerEvent(DOLVEvent.MenuItemSelectedEvent, row = self.row, item = item,
			column = self.column, index = self.column.column.GetModelColumn(), menu = menu)

		if ((answer != False) and (item_id in self.functions)):
			self.functions[item_id](self.row, self.column, item)

		event.Skip()

	def Show(self):
		"""
		Show the menu.
		"""

		#Cannot show an empty list
		if (not self.contents):
			return

		#Create the menu
		menu = wx.Menu()
		for item_id in self.contents:
			text = _Munge(self.idCatalogue[item_id], source = self.row, extraArgs = [self.column], returnMunger_onFail = True)

			if ((item_id in self.conditions) and (not self.conditions[item_id](self.row, self.column, text))):
				continue
			if (not self.exclusive_x.get(item_id, {None}).intersection({None, self.row})):
				continue
			if (not self.exclusive_y.get(item_id, {None}).intersection({None, self.column})):
				continue
 
			if (not text):
				menu.Append(item_id, "", kind = wx.ITEM_SEPARATOR)

			elif (item_id in self.checks):
				menu.AppendCheckItem(item_id, text)
				menu.Check(item_id, _Munge(self.checks[item_id], source = self.row, extraArgs = [self.column], returnMunger_onFail = True))

			elif (item_id in self.radios):
				menu.AppendRadioItem(item_id, text)
				menu.Check(item_id, _Munge(self.radios[item_id], source = self.row, extraArgs = [self.column], returnMunger_onFail = True))
			
			else:
				menu.Append(item_id, text)

		#Allow the user to veto the menu and/or make changes to it
		answer = self.olv.TriggerEvent(DOLVEvent.MenuCreationEvent, row = self.row, 
			column = self.column, index = self.column.column.GetModelColumn(), menu = menu)
		if (answer == False):
			return False

		#Show the menu
		self.olv.PopupMenu(menu)
		menu.Destroy()
		return True

class UndoEdit():
	"""
	This class tracks an edit action that was done.
	It provides undo and redo methods.
	
	Modified code from: https://wiki.wxpython.org/UndoRedoFramework
	"""

	def __init__(self, olv, modelObject, column, oldValue, newValue):
		self.olv = olv
		self.column = column
		self.oldValue = oldValue
		self.newValue = newValue
		self.modelObject = modelObject

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		if (traceback is not None):
			return False

	def GetType(self):
		return self.__class__.__name__

	def undo(self, undo = True):
		if (undo):
			event = self.olv.TriggerEvent(DOLVEvent.UndoEvent, row = self.modelObject, column = self.olv.GetColumn(self.column), 
				value = self.oldValue, type = self.GetType(), returnEvent = True)
		else:
			event = self.olv.TriggerEvent(DOLVEvent.RedoEvent, row = self.modelObject, column = self.olv.GetColumn(self.column), 
				value = self.newValue, type = self.GetType(), returnEvent = True)
		if (event.IsVetoed()):
			return

		_row = self.olv.model.ObjectToItem(event.row)
		if (not _row.IsOk()):
			print("@UndoEdit.undo", f"Row {event.row.__repr__()} is not on the table anymore.")
			return False
		if (event.column is None):
			print("@UndoEdit.undo", f"Column {self.column.__repr__()} is not on the table anymore.")
			return False

		if (event.wasHandled):
			return self.olv.model.ValueChanged(_row, event.column.GetIndex())
		return self.olv.model.ChangeValue(event.value, _row, event.column.GetIndex())

	def redo(self, redo = True):
		return self.undo(undo = not redo)

class UndoPaste():
	"""
	This class tracks a paste action that was done.
	It provides undo and redo methods.
	
	Modified code from: https://wiki.wxpython.org/UndoRedoFramework
	"""

	def __init__(self, olv, log):
		self.olv = olv
		self.log = log

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		if (traceback is not None):
			return False

	def GetType(self):
		return self.__class__.__name__

	def undo(self, undo = True):
		self.olv._paste_ignoreSort = True
		try:
			success = True
			for row, changes in self.log.items():
				for column, oldValue, newValue in changes:
					if (undo):
						event = self.olv.TriggerEvent(DOLVEvent.UndoEvent, row = row, column = self.olv.GetColumn(column), 
							value = oldValue, type = self.GetType(), returnEvent = True)
					else:
						event = self.olv.TriggerEvent(DOLVEvent.RedoEvent, row = row, column = self.olv.GetColumn(column), 
							value = newValue, type = self.GetType(), returnEvent = True)
					if (event.IsVetoed()):
						continue

					_row = self.olv.model.ObjectToItem(event.row)
					if (not _row.IsOk()):
						print("@UndoPaste.undo", f"Row {row.__repr__()} is not on the table anymore.")
						success = False
						continue
					if (event.column is None):
						print("@UndoPaste.undo", f"Column {column.__repr__()} is not on the table anymore.")
						success = False
						continue

					if (event.wasHandled):
						if (not self.olv.model.ValueChanged(_row, event.column.GetIndex())):
							success = False
					else:
						if (not self.olv.model.ChangeValue(event.value, _row, event.column.GetIndex())):
							success = False
			return success
		finally:
			self.olv._paste_ignoreSort = False
			self.olv.model.Resort()

	def redo(self, redo = True):
		return self.undo(undo = not redo)

#Utility Functions
_StringToValue = MyUtilities.common._StringToValue
_SetValueUsingMunger = MyUtilities.common._SetValueUsingMunger
_Munge = MyUtilities.common._Munge

_drawText = MyUtilities.wxPython._drawText
_drawBackground = MyUtilities.wxPython._drawBackground
_drawButton = MyUtilities.wxPython._drawButton

#Models
#https://github.com/wxWidgets/Phoenix/blob/master/samples/dataview/DataViewModel.py
dummy = type("Dummy", (object,), {})
class NormalListModel(wx.dataview.PyDataViewModel):
	"""Displays like an ObjectListView or GroupListView."""
	#https://wxpython.org/Phoenix/docs/html/wx.dataview.DataViewItemObjectMapper.html

	def __init__(self, olv, useWeakRefs = True):
		wx.dataview.PyDataViewModel.__init__(self)
		self.olv = olv
		self.colorCatalogue = {}

		self.rootLength = 0 #How many children are shown on the top level of the model
		self.sortCounter = None
		self.useWeakRefs = useWeakRefs
		self.sort_colorCatalogue = {}

		self.SelectCompare()

		# The PyDataViewModel derives from both DataViewModel and from
		# DataViewItemObjectMapper, which has methods that help associate
		# data view items with Python objects. Normally a dictionary is used
		# so any Python object can be used as data nodes. If the data nodes
		# are weak-referencable then the objmapper can use a
		# WeakValueDictionary instead.
		self.UseWeakRefs(useWeakRefs)
		# self.UseWeakRefs(True)

	def GetAttr(self, item, column, attribute):
		#Override this to indicate that the item has special font attributes.
		#The base class version always simply returns False.

		node = self.ItemToObject(item)
		def applyColor(color, odd = None):
			nonlocal node
			try:
				attribute.SetBackgroundColour(color)
			except TypeError:
				if (odd is None):
					odd = (node not in self.colorCatalogue) or (self.colorCatalogue[node] is self.olv.oddRowsBackColor)
				if (odd):
					attribute.SetBackgroundColour(color[0])
				else:
					attribute.SetBackgroundColour(color[1])

			return True

		try:
			if (isinstance(node, DataListGroup)):
				attribute.SetBold(self.olv.groupFont[0])
				attribute.SetItalic(self.olv.groupFont[1])

				if (self.olv.colorOverride_groupFunction):
					try:
						color = self.olv.colorOverride_groupFunction(node, self.olv.columns[column])
					except Exception as error:
						print("@applyColor.1", error)
						color = None

					if (color is not None):
						return applyColor(color)

				attribute.SetColour(self.olv.groupFont[2])
				return True

			if (self.olv.colorOverride_function):
				try:
					color = self.olv.colorOverride_function(node, self.olv.columns[column])
				except Exception as error:
					print("@applyColor.2", error)
					color = None

				if (color is not None):
					return applyColor(color)

			if ((node, column) in self.olv.colorOverride_cell):
				return applyColor(self.olv.colorOverride_cell[(node, column)])

			if (column in self.olv.colorOverride_column):
				return applyColor(self.olv.colorOverride_column[column])

			if (node in self.olv.colorOverride_row):
				return applyColor(self.olv.colorOverride_row[node])
			
			if (self.sortCounter is not None):
				if (node not in self.sort_colorCatalogue):
					if (self.sortCounter % 2):
						self.sort_colorCatalogue[node] = self.olv.evenRowsBackColor
					else:
						self.sort_colorCatalogue[node] = self.olv.oddRowsBackColor
					self.sortCounter += 1
				return applyColor(self.sort_colorCatalogue[node])
			
			if (node in self.colorCatalogue):
				return applyColor(self.colorCatalogue[node])

		finally:
			if (self.olv.rowFormatter is not None):
				self.olv.rowFormatter(node, column, attribute)

	def GetChildrenList(self, parent):
		children = wx.dataview.DataViewItemArray()
		self.GetChildren(parent, children)
		return list(children)

	def GetChildren(self, parent, children):
		#Override this so the control can query the child items of an item.
		#Returns the number of items.

		def applyRowColor(rows):
			if (self.olv.useAlternateBackColors and self.olv.InReportView()):
				for index, row in enumerate(rows):
					if (index % 2):
						self.colorCatalogue[row] = self.olv.evenRowsBackColor
					else:
						self.colorCatalogue[row] = self.olv.oddRowsBackColor

		def applyGroupColor(group, rows):
			if (self.olv.useAlternateBackColors and self.olv.InReportView()):
				if (self.olv.groupBackColor is not None):
					self.colorCatalogue[group] = self.olv.groupBackColor
				applyRowColor(rows)

		def applyRowFilter(rows):
			if (self.olv.filter):
				return list(self.olv.filter(rows))
			return rows

		# The view calls this method to find the children of any node in the
		# control. There is an implicit hidden root node, and the top level
		# item(s) should be reported as children of this node. A List view
		# simply provides all items as children of this hidden root. A Tree
		# view adds additional items as children of the other items, as needed,
		# to provide the tree hierachy.

		# If the parent item is invalid then it represents the hidden root
		# item, so we'll use the genre objects as its children and they will
		# end up being the collection of visible roots in our tree.
		if (not parent):
			if (self.olv.showGroups):
				self.rootLength = 0
				for group in self.olv.groups:
					rowList = applyRowFilter(group.modelObjects)
					if ((not rowList) and ((not _Munge(self.olv.showEmptyGroups, source = group, returnMunger_onFail = True)) or (group.key not in self.olv.emptyGroups))):
						continue

					self.rootLength += 1
					applyGroupColor(group, rowList)
					children.append(self.ObjectToItem(group))
			else:
				rowList = applyRowFilter(self.olv.modelObjects)
				self.rootLength = len(rowList)
				applyRowColor(rowList)
				for row in rowList:
					children.append(self.ObjectToItem(row))

			return self.rootLength

		# Otherwise we'll fetch the python object associated with the parent
		# item and make DV items for each of it's child objects.
		node = self.ItemToObject(parent)
		if (isinstance(node, DataListGroup)):
			rowList = applyRowFilter(node.modelObjects)
			applyGroupColor(node, rowList)
			for row in rowList:
				children.append(self.ObjectToItem(row))
			return len(rowList)
		return 0

	def GetParent(self, item):
		#Override this to indicate which wx.dataview.DataViewItem representing the parent of item 
		#or an invalid wx.dataview.DataViewItem if the root item is the parent item.

		if (not self.olv.showGroups):
			return wx.dataview.NullDataViewItem

		if (isinstance(item, wx.dataview.DataViewItem)):
			if (not item):
				return wx.dataview.NullDataViewItem
			node = self.ItemToObject(item)
		else:
			node = item

		if (isinstance(node, DataListGroup)):
			return wx.dataview.NullDataViewItem
		else:
			for group in self.olv.groups:
				if (node in group.modelObjects):
					return self.ObjectToItem(group)
			return wx.dataview.NullDataViewItem

	def GetFirstItem(self):
		children = self.GetChildrenList(wx.dataview.NullDataViewItem)
		if (children):
			return children[0]
		return wx.dataview.NullDataViewItem

	def GetLastItem(self):
		children = self.GetChildrenList(wx.dataview.NullDataViewItem)
		if (children):
			return children[-1]
		return wx.dataview.NullDataViewItem

	def GetPreviousItem(self, item, wrap = False):
		#Modified code from: http://docs.kicad-pcb.org/doxygen/wxdataviewctrl__helpers_8cpp_source.html
		if (not isinstance(item, wx.dataview.DataViewItem)):
			item = self.ObjectToItem(item)

		previousItem = self.GetPreviousSibling(item)
		if (not previousItem.IsOk()):
			previousItem = self.GetParent(item)

		elif (self.olv.IsExpanded(previousItem)):
			children = self.GetChildrenList(previousItem)
			previousItem = children[-1]

		if (wrap and (not previousItem.IsOk())):
			return self.GetLastItem()
		return previousItem

	def GetNextItem(self, item, wrap = False):
		#Modified code from: http://docs.kicad-pcb.org/doxygen/wxdataviewctrl__helpers_8cpp_source.html
		if (not isinstance(item, wx.dataview.DataViewItem)):
			item = self.ObjectToItem(item)

		if ((not item.IsOk()) or (self.olv.IsExpanded(item))):
			children = self.GetChildrenList(item)
			nextItem = children[0]
		else:
			#Walk up levels until we find one that has a next sibling
			walk = item
			while (walk.IsOk()):
				nextItem = self.GetNextSibling(walk)
				if (nextItem.IsOk()):
					break
				walk = self.GetParent(walk)
			else:
				nextItem = wx.dataview.NullDataViewItem

		if (wrap and (not nextItem.IsOk())):
			return self.GetFirstItem()
		return nextItem

	def GetPreviousSibling(self, item):
		#Modified code from: http://docs.kicad-pcb.org/doxygen/wxdataviewctrl__helpers_8cpp_source.html
		if (not isinstance(item, wx.dataview.DataViewItem)):
			item = self.ObjectToItem(item)

		previousItem = wx.dataview.NullDataViewItem
		for sibling in self.GetChildrenList(self.GetParent(item)):
			if (sibling == item):
				break
			previousItem = sibling
		return previousItem

	def GetNextSibling(self, item):
		#Modified code from: http://docs.kicad-pcb.org/doxygen/wxdataviewctrl__helpers_8cpp_source.html
		if (not isinstance(item, wx.dataview.DataViewItem)):
			item = self.ObjectToItem(item)

		returnNext = False
		for sibling in self.GetChildrenList(self.GetParent(item)):
			if (returnNext):
				return sibling
			if (sibling == item):
				returnNext = True
		return wx.dataview.NullDataViewItem

	def GetValue(self, item, column, alternateGetter = None, raw = False):
		#Override this to indicate the value of item.
		#A Variant is used to store the data.

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
			if (isinstance(defn.renderer, (Renderer_Text, Renderer_Choice))):
				return (node.title, node.title, None)
			return node.title

		if (alternateGetter):
			value = _Munge(alternateGetter, source = node, extraArgs = [defn])
		else:
			value = _Munge(defn.valueGetter, source = node, extraArgs = [defn])

		if (raw):
			return value

		if (isinstance(defn.renderer, Renderer_Text)):
			#Account for formatter and icon
			icon = _Munge(defn.renderer.icon, source = node, extraArgs = [defn], returnMunger_onFail = True)
			return (value, _StringToValue(value, defn.stringConverter, extraArgs = [defn]), icon)

		if (isinstance(defn.renderer, Renderer_Choice)):
			#Account for formatter
			return (value, _StringToValue(value, defn.stringConverter, extraArgs = [defn]))
		
		if (isinstance(defn.renderer, (wx.dataview.DataViewTextRenderer, wx.dataview.DataViewChoiceRenderer))):
			return _StringToValue(value, defn.stringConverter, extraArgs = [defn])

		elif (isinstance(defn.renderer, (Renderer_Spin, wx.dataview.DataViewSpinRenderer,
			wx.dataview.DataViewProgressRenderer, Renderer_Progress))):
			try:
				return float(value)
			except TypeError:
				return 0
		
		elif (isinstance(defn.renderer, (wx.dataview.DataViewIconTextRenderer, Renderer_Icon))):
			icon = _Munge(defn.renderer.icon, source = node, extraArgs = [defn], returnMunger_onFail = True)
			if (icon is None):
				icon = wx.Icon(wx.NullBitmap)
			if (value is None):
				value = ""

			print("@GetValue", defn.valueGetter, defn.renderer)

			#Account for formatter
			if (isinstance(defn.renderer, Renderer_Icon)):
				return (value, _StringToValue(value, defn.stringConverter, extraArgs = [defn]), icon)
			return wx.dataview.DataViewIconText(text = str(value), icon = icon)

		elif (isinstance(defn.renderer, Renderer_MultiImage)):
			image = _Munge(defn.renderer.image, source = node, extraArgs = [defn], returnMunger_onFail = True)
			if (isinstance(image, (list, tuple, set, types.GeneratorType))):
				return image
			else:
				return [image] * int(value)

		elif (isinstance(defn.renderer, Renderer_Button)):
			return [node, defn, value]

		if (value is None):
			value = ""
		return value

	def SetValue(self, value, item, column):
		# This gets called in order to set a value in the data model.
		# The most common scenario is that the wx.dataview.DataViewCtrl calls this method after the user changed some data in the view.
		# This is the function you need to override in your derived class but if you want to call it, 
		# ChangeValue is usually more convenient as otherwise you need to manually call ValueChanged to update the control itself.

		node = self.ItemToObject(item)
		if (isinstance(node, DataListGroup)):
			return True

		try:
			defn = self.olv.columns[column]
		except AttributeError:
			raise AttributeError(f"There is no column {column}")

		if (isinstance(defn.renderer, (wx.dataview.DataViewIconTextRenderer, Renderer_Icon)) and (isinstance(value, wx.dataview.DataViewIconText))):
			value = value.GetText()

		if (defn.valueSetter is None):
			_SetValueUsingMunger(node, value, defn.valueGetter, extraArgs = [defn])
		else:
			_SetValueUsingMunger(node, value, defn.valueSetter, extraArgs = [defn])
			
		return True

	#Checking ------------------------------------------------------------------------------------------------------
	def HasContainerColumns(self, item):
		#Override this method to indicate if a container item merely acts as a headline (or for categorisation) 
		#or if it also acts a normal item with entries for further columns.
		#By default returns False.
		return super().HasContainerColumns(item)

	def HasDefaultCompare(self):
		# Override this to indicate that the model provides a default compare function that the control should use if no wx.dataview.DataViewColumn has been chosen for sorting.
		# Usually, the user clicks on a column header for sorting, the data will be sorted alphanumerically.
		# If any other order (e.g. by index or order of appearance) is required, then this should be used. See wx.dataview.DataViewIndexListModel for a model which makes use of this.
		return super().HasDefaultCompare()

	def HasValue(self, item, column):
		# Return True if there is a value in the given column of this item.

		# All normal items have values in all columns but the container items only show their label in the first column (column == 0) by default (but see HasContainerColumns ). 
		#So this function always returns True for the first column while for the other ones it returns True only if the item is not a container or HasContainerColumns was overridden to return True for it.
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
		if (isinstance(node, DataListGroup)):
			return True


		# but everything else (the song objects) are not
		return False

	def IsEnabled(self, item, column):
		# Override this to indicate that the item should be disabled.
		# Disabled items are displayed differently (e.g. grayed out) and cannot be interacted with.
		# The base class version always returns True, thus making all items enabled by default.

		return super().IsEnabled(item, column)

	# Report how many columns this model provides data for.
	def GetColumnCount(self):
		#Override this to indicate the number of columns in the model.
		return len(self.olv.columns)

	# Map the data column numbers to the data type
	def GetColumnType(self, column):
		#Override this to indicate what type of data is stored in the column specified by column.
		#This should return a string indicating the type of data as reported by Variant .
		raise NotImplementedError()

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
		return super().Cleared()

	def ChangeValue(self, value, item, column):
		#Change the value of the given item and update the control to reflect it.
		#This function simply calls SetValue and, if it succeeded, ValueChanged.

		#super().ChangeValue does not accept a value of None, so the logic is redone here
		if (self.SetValue(value, item, column)):
			return self.ValueChanged(item, column)

		# return super().ChangeValue(value, item, column)

	def ValueChanged(self, item, column):
		# Call this to inform this model that a value in the model has been changed.
		# This is also called from wx.dataview.DataViewCtrl‘s internal editing code, e.g. when editing a text field in the control.
		# This will eventually emit a wxEVT_DATAVIEW_ITEM_VALUE_CHANGED event to the user.
		return super().ValueChanged(item, column)

	def ItemAdded(self, parent, item):
		#Call this to inform the model that an item has been added to the data.

		try:
			super().ItemAdded(parent, item)
		except wx._core.wxAssertionError:
			#The filter has removed the item from the list
			return True
		except TypeError:
			#The item was not converted
			return super().ItemAdded(parent, self.ObjectToItem(item))

	def ItemChanged(self, item):
		#Call this to inform the model that an item has changed.
		# This will eventually emit a wxEVT_DATAVIEW_ITEM_VALUE_CHANGED event (in which the column fields will not be set) to the user.
		if (not isinstance(item, wx.dataview.DataViewItem)):
			item = self.ObjectToItem(item)
		return super().ItemChanged(item)

	def ItemDeleted(self, parent, item):
		#Call this to inform the model that an item has been deleted from the data.
		if (parent is None):
			parent = self.GetParent(item)
		if (not isinstance(item, wx.dataview.DataViewItem)):
			item = self.ObjectToItem(item)
		return super().ItemDeleted(parent, item)

	def ItemsAdded(self, items):
		"""Call this to inform the model that several items have been added to the data."""

		#If a large list has all items filtered out, it will make super().ItemAdded take over 8000 times longer
		if (self.olv.filter):
			try:
				next(iter(self.olv.filter(items)))
			except StopIteration:
				return True

		parent = self.ObjectToItem(dummy) #This speeds up the super() function WAY more than NullDataViewItem does. And, it doesn't seem to matter
		for item in items:
			self.ItemAdded(parent, self.ObjectToItem(item))
		return True

	def ItemsChanged(self, items):
		# Call this to inform the model that several items have changed.
		# This will eventually emit wxEVT_DATAVIEW_ITEM_VALUE_CHANGED events (in which the column fields will not be set) to the user.

		for item in items:
			answer = self.ItemChanged(item)
		return True

	def ItemsDeleted(self, parent, items):
		# Call this to inform the model that several items have been deleted.

		if (parent is not None):
			return super().ItemsDeleted(parent, items)
		
		for item in items:
			answer = self.ItemDeleted(parent, item)
		return True

	#Sorting-------------------------------------------------------
	def Resort(self):
		# Call this to initiate a resort after the sort function has been changed.

		if (self.olv._paste_ignoreSort):
			return

		#Fire a SortEvent that can be catched by an OLV-using developer using Bind() for this event
		column = self.olv.GetSortingColumn()
		try:
			event = DOLVEvent.SortingEvent(self.olv, self.olv.columns.get(column.GetModelColumn(), None), column.GetModelColumn(), column.IsSortOrderAscending())
		except AttributeError as error:
			event = DOLVEvent.SortingEvent(self.olv, None, -1, None)
		self.olv.GetEventHandler().ProcessEvent(event)
		if (event.wasHandled or event.IsVetoed()):
			return

		#Fix row colors
		self.sortCounter = 0
		self.sort_colorCatalogue = {}

		answer = super().Resort()
		return answer

	def GetSortValue(self, item, column):
		"""Returns the value to be used for sorting."""

		try:
			defn = self.olv.columns[column]
		except AttributeError:
			raise AttributeError(f"There is no column {column}")

		if (isinstance(defn.renderer, (wx.dataview.DataViewBitmapRenderer, Renderer_Bmp, Renderer_MultiImage))):
			#Do not compare images
			return (False, 0)
		
		if (isinstance(defn.renderer, (wx.dataview.DataViewIconTextRenderer, Renderer_Icon))):
			#Only compare the text
			value = self.GetValue(item, column, alternateGetter = defn.groupSortGetter)
			value = value.GetText()
		else:
			value = self.GetValue(item, column, alternateGetter = defn.sortGetter)
		
		# When sorting large groups, this is called a lot. Make it efficent.
		# It is more efficient (by about 30%) to try to call lower() and catch the
		# exception than it is to test for the class
		if (not self.olv.caseSensitive):
			try:
				value = value.lower()
			except AttributeError:
				pass
		
		#Account for None being a value
		return (value is None, value)

	def SelectCompare(self):
		"""Different case functions have been created to speed up calls to the function Compare()."""

		if (self.olv.compareFunction is None):
			if (self.olv.groupCompareFunction is None):
				self.Compare = self.Compare_None
			else:
				self.Compare = self.Compare_Group
		else:
			if (self.olv.groupCompareFunction is None):
				self.Compare = self.Compare_Row
			else:
				self.Compare = self.Compare_GroupRow

	def Compare_None(self, item1, item2, column, ascending):
		"""This compare function will run if the user does not plan on intercepting it themselves."""

		#The compare function to be used by control.
		#The default compare function sorts by container and other items separately and in ascending order. Override this for a different sorting behaviour.
		#The comparison function should return negative, null or positive value depending on whether the first item is less than, equal to or greater than the second one. 
		#The items should be compared using their values for the given column.

		value1 = self.GetSortValue(item1, column)
		value2 = self.GetSortValue(item2, column)

		#The builtin function cmp is depricated now
		if (value1 < value2):
			return (1, -1)[ascending]
		elif (value1 > value2):
			return (-1, 1)[ascending]
		else:
			return 0

	Compare = Compare_None #Compare_None is the default function to use for Compare

	def Compare_Row(self, item1, item2, column, ascending):
		"""This compare function will run if the user plans on intercepting only rows themselves."""

		node = self.ItemToObject(item1)
		if (not isinstance(node, DataListGroup)):
			answer = self.olv.compareFunction(node, self.ItemToObject(item2), self.olv.columns[column], ascending)
			if (answer is not None):
				return answer
		return self.Compare_None(item1, item2, column, ascending)

	def Compare_Group(self, item1, item2, column, ascending):
		"""This compare function will run if the user plans on intercepting only groups themselves."""

		node = self.ItemToObject(item1)
		if (isinstance(node, DataListGroup)):
			answer = self.olv.groupCompareFunction(node, self.ItemToObject(item2), self.olv.columns[column], ascending)
			if (answer is not None):
				return answer
		return self.Compare_None(item1, item2, column, ascending)

	def Compare_GroupRow(self, item1, item2, column, ascending):
		"""This compare function will run if the user plans on intercepting both groups and rows themselves."""

		node = self.ItemToObject(item1)
		if (isinstance(node, DataListGroup)):
			answer = self.olv.groupCompareFunction(node, self.ItemToObject(item2), self.olv.columns[column], ascending)
		else:
			answer = self.olv.compareFunction(node, self.ItemToObject(item2), self.olv.columns[column], ascending)
		if (answer is not None):
			return answer
		return self.Compare_None(item1, item2, column, ascending)

	#Unused -----------------------------------------------------------------------------
	def AddNotifier(self, notifier):
		#Adds a wx.dataview.DataViewModelNotifier to the model.
		return super().AddNotifier(notifier)

	def RemoveNotifier(self, notifier):
		# Remove the notifier from the list of notifiers.
		return super().RemoveNotifier(notifier)

	def IsListModel(self):
		return super().IsListModel()

	def IsVirtualListModel(self):
		return super().IsVirtualListModel()

#Renderers
_ellipsizeCatalogue = {
	None: wx.ELLIPSIZE_NONE, 
	False: wx.ELLIPSIZE_NONE, 
	True: wx.ELLIPSIZE_MIDDLE,
	"start": wx.ELLIPSIZE_START, 
	"middle": wx.ELLIPSIZE_MIDDLE, 
	"end": wx.ELLIPSIZE_END,
}
class Renderer_MultiImage(wx.dataview.DataViewCustomRenderer):
	"""
	Places multiple images next to each other.

	If *image* is a list of bitmaps, each will be placed in the cell in the order they are in the list.
	Otherwise, *image* will be repeated n times, where n the value returned by *valueGetter* for the assigned *ColumnDefn*.
	"""

	def __init__(self, image = None, **kwargs):
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
		self.value = value
		return True

	def GetValue(self):
		return self.value

	def GetSize(self):
		# Return the size needed to display the value.  The renderer
		# has a helper function we can use for measuring text that is
		# aware of any custom attributes that may have been set for
		# this item.
		return (-1, -1)

	def Render(self, rect, dc, state):

		x, y, width, height = rect
		totalWidth = 0
		for image in self.value:
			try:
				dc.DrawBitmap(image, x + totalWidth, y)
			except TypeError:
				dc.DrawIcon(image, x + totalWidth, y)
			totalWidth += image.GetWidth()
		return True

class Renderer_Button(wx.dataview.DataViewCustomRenderer):
	"""
	Depending on what *text* and *function* initially are will determine how 
	the value returned by by *valueGetter* for the assigned *ColumnDefn* is used.
		- *text* is None and *function* is None: The value should be a list, where the first element is 
			the text to display and the second element is the function to run.
		- *text* is not None and *function* is None: The value should be a function that returns a function.
			If it is only a function, _Munge will run it.
			For simplicity, you can use `lambda: yourFunction`.
		- *text* is None and *function* is not None: The value returned should be the text to display.
		- *text* is not None and *function* is not None: The value returned will be passed to *function* as
			a third parameter.

	In all cases, the function should accept the following parameters: objectModel, columnIndex

	- *enabled* is not None: Determines if the button is enabled or not. 
		If *enabled* is None, if the column is editable or not will be used for this.

	The Button can be drawn with the wxNativeRenderer if *useNativeRenderer* is True.
	If it is None, Only text will be drawn.
	"""

	def __init__(self, text = None, function = None, enabled = None, useNativeRenderer = False, ellipsize = True, mode = wx.dataview.DATAVIEW_CELL_ACTIVATABLE, **kwargs):
		wx.dataview.DataViewCustomRenderer.__init__(self, mode = mode, **kwargs)
		self.type = "button"
		self.buildingKwargs = {**kwargs, "text": text, "function": function, "enabled": enabled, "useNativeRenderer": useNativeRenderer, "mode": mode}
		
		if (text is None):
			if (function is None):
				self.SetValue = self.SetValue_both
			else:
				self.SetValue = self.SetValue_text
		else:
			if (function is None):
				self.SetValue = self.SetValue_function
			else:
				self.LeftClick = self.LeftClick_extraArg

		self.text = text
		self.enabled = enabled
		self.function = function
		self.useNativeRenderer = useNativeRenderer

		self.SetEllipsize(ellipsize)

	def Clone(self, **kwargs):
		#Any keywords in kwargs will override keywords in buildingKwargs
		instructions = {**self.buildingKwargs, **kwargs}
		return super().__self_class__(**instructions)

	def SetEllipsize(self, ellipsize = None):
		global _ellipsizeCatalogue

		self.ellipsize = ellipsize
		self.buildingKwargs["ellipsize"] = ellipsize

		self.EnableEllipsize(_ellipsizeCatalogue.get(ellipsize, wx.ELLIPSIZE_MIDDLE))

	def SetValue_both(self, value):
		self._node = value[0]
		self._column = value[1]
		self._text = value[2][0]
		self._applyFunction(value[2][1])

		if (self.enabled is not None):
			self._enabled = _Munge(self.enabled, source = self._node, returnMunger_onFail = True)
		else:
			self._enabled = self.GetMode() == rendererCatalogue[self.type]["edit"]
		return True

	def SetValue_function(self, value):
		self._node = value[0]
		self._column = value[1]
		self._applyFunction(value[2])
		self._text = _Munge(self.text, source = self._node, returnMunger_onFail = True)

		if (self.enabled is not None):
			self._enabled = _Munge(self.enabled, source = self._node, returnMunger_onFail = True)
		else:
			self._enabled = self.GetMode() == rendererCatalogue[self.type]["edit"]
		return True

	def SetValue_text(self, value):
		self._node = value[0]
		self._column = value[1]
		self._applyFunction(_Munge(self.function, source = self._node, returnMunger_onFail = True))
		self._text = value[2]

		if (self.enabled is not None):
			self._enabled = _Munge(self.enabled, source = self._node, returnMunger_onFail = True)
		else:
			self._enabled = self.GetMode() == rendererCatalogue[self.type]["edit"]
		return True

	def SetValue(self, value):
		self._node = value[0]
		self._column = value[1]
		self._applyFunction(_Munge(self.function, source = self._node, returnMunger_onFail = True))
		self._text = _Munge(self.text, source = self._node, returnMunger_onFail = True)
		self.extraArg = value[2]

		if (self.enabled is not None):
			self._enabled = _Munge(self.enabled, source = self._node, returnMunger_onFail = True)
		else:
			self._enabled = self.GetMode() == rendererCatalogue[self.type]["edit"]
		return True

	def _applyFunction(self, function):
		if (callable(function)):
			self._function = function
		else:
			self._function = None

	def GetValue(self):
		return self.function

	def GetSize(self):
		return (-1, -1)

	def Render(self, rectangle, dc, state):

		isSelected = state == wx.dataview.DATAVIEW_CELL_SELECTED
		useNativeRenderer = _Munge(self.useNativeRenderer, source = self._node, returnMunger_onFail = True)
		if (useNativeRenderer):
			#Use: https://github.com/wxWidgets/wxPython/blob/master/demo/RendererNative.py

			style = []
			if (isSelected):
				style.append("wx.CONTROL_SELECTED")
			if (not self._enabled):
				style.append("wx.CONTROL_DISABLED")
			# if (self._isPressed):
			# 	style.append("wx.CONTROL_PRESSED")
			style = "|".join(style)

			wx.RendererNative.Get().DrawPushButton(self.GetOwner().GetOwner(), dc, rectangle, eval(style, {'__builtins__': None, "wx": wx}, {}))
		elif (useNativeRenderer is not None):
			rectangle.Deflate(2, 2)
			_drawButton(dc, rectangle, isSelected)
			rectangle.Deflate(2, 0)

		if (self._text):
			_drawText(dc, text = self._text, align = rectangle, isSelected = False, isEnabled = self._enabled, x_align = "left") #x_align = "center" if (useNativeRenderer is not None) else "left")
		return True

	def LeftClick(self, clickPos, cellRect, model, item, columnIndex):
		if (self._enabled and self._function):
			self._function(model.ItemToObject(item), model.olv.columns[columnIndex])
		return True

	def LeftClick_extraArg(self, clickPos, cellRect, model, item, columnIndex):
		if (self._enabled and self._function):
			self._function(model.ItemToObject(item), model.olv.columns[columnIndex], self.extraArg)
		return True

class Renderer_File(wx.dataview.DataViewCustomRenderer):
	"""
	Uses a file picker or directory picker as the editor.
	The value returned by *valueGetter* is a filepath.
	"""

	def __init__(self, *args, message = "", directoryOnly = False, openFile = True,
		wildcard = "All files (*.*)|*.*", changeDir = False, single = False, preview = False,
		mustExist = False, confirm = True, ellipsize = True, **kwargs):

		wx.dataview.DataViewCustomRenderer.__init__(self, **kwargs)
		self.type = "file"

		self.buildingKwargs = {**kwargs, "message": message, "changeDir": changeDir, 
			"mustExist": mustExist, "wildcard": wildcard, "confirm": confirm, "single": single, "preview": preview}
		
		self.message = message
		self.changeDir = changeDir

		if (directoryOnly):
			self.single = True
			self.mustExist = mustExist
			self.CreateEditorCtrl = self.CreateEditorCtrl_dirOnly
		else:
			self.preview = preview
			self.wildcard = wildcard
			if (openFile):
				self.single = single
				self.mustExist = mustExist
			else:
				self.single = True
				self.confirm = confirm
				self.CreateEditorCtrl = self.CreateEditorCtrl_save

		self.value = None
		self.SetEllipsize(ellipsize)

	def Clone(self, **kwargs):
		#Any keywords in kwargs will override keywords in buildingKwargs
		instructions = {**self.buildingKwargs, **kwargs}
		return super().__self_class__(**instructions)

	def SetEllipsize(self, ellipsize = None):
		global _ellipsizeCatalogue

		self.ellipsize = ellipsize
		self.buildingKwargs["ellipsize"] = ellipsize

		self.EnableEllipsize(_ellipsizeCatalogue.get(ellipsize, wx.ELLIPSIZE_MIDDLE))

	def SetValue(self, value):
		if ((not self.single) and (not isinstance(value, (list, tuple)))):
			value = [value]
		self.value = value
		return True

	def GetValue(self):
		return self.value

	def GetSize(self):
		return (-1, -1)

	def Render(self, rectangle, dc, state):
		isSelected = state == wx.dataview.DATAVIEW_CELL_SELECTED

		if (not self.single):
			value = ", ".join(self.value)
		else:
			value = self.value

		_drawText(dc, text = value, align = rectangle, isSelected = isSelected, x_align = "left")
		return True

	def HasEditorCtrl(self):
		return False

	def GetValueFromEditorCtrl(self, editor):
		value = editor.GetValue()
		if (not self.single):
			value = ast.literal_eval(f"['{value.lstrip('[').rstrip(']')}']")
		return value

	def CreateEditorCtrl(self, parent, labelRect, value):
		#Show Dialog
		style = ["wx.FD_OPEN"]
		if (self.changeDir):
			style.append("wx.FD_CHANGE_DIR")
		if (self.mustExist):
			style.append("wx.FD_FILE_MUST_EXIST")
		if (not self.single):
			style.append("wx.FD_MULTIPLE")
		if (self.preview):
			style.append("wx.FD_PREVIEW")
		style = "|".join(style)

		if (self.single):
			checkValue = value
		else:
			try:
				checkValue = value[0]
			except IndexError:
				checkValue = ""

		if (os.path.exists(os.path.dirname(checkValue))):
			defaultDir = os.path.dirname(checkValue)
		else:
			defaultDir = ""

		if (os.path.exists(os.path.basename(checkValue))):
			defaultFile = os.path.basename(checkValue)
		else:
			defaultFile = ""

		with wx.FileDialog(parent, self.message, defaultDir = defaultDir, defaultFile = defaultFile,
			wildcard = self.wildcard, style = eval(style, {'__builtins__': None, "wx": wx}, {})) as fileDialog:

			if (fileDialog.ShowModal() == wx.ID_CANCEL):
				value = value
			elif (self.single):
				value = fileDialog.GetPath()
			else:
				value = ", ".join(fileDialog.GetPaths())

		#Create ctrl
		ctrl = wx.TextCtrl(parent, value = value, pos = labelRect.Position, size = labelRect.Size)
		ctrl.SetInsertionPointEnd()
		ctrl.SelectAll()

		return ctrl

	def CreateEditorCtrl_save(self, parent, labelRect, value):
		#Show Dialog
		style = ["wx.FD_SAVE"]
		if (self.changeDir):
			style.append("wx.FD_CHANGE_DIR")
		if (self.confirm):
			style.append("wx.FD_OVERWRITE_PROMPT")
		if (self.preview):
			style.append("wx.FD_PREVIEW")
		style = "|".join(style)

		if (self.single):
			checkValue = value
		else:
			try:
				checkValue = value[0]
			except IndexError:
				checkValue = ""

		if (os.path.exists(os.path.dirname(checkValue))):
			defaultDir = os.path.dirname(checkValue)
		else:
			defaultDir = ""

		if (os.path.exists(os.path.basename(checkValue))):
			defaultFile = os.path.basename(checkValue)
		else:
			defaultFile = ""

		with wx.FileDialog(parent, self.message, defaultDir = defaultDir, defaultFile = defaultFile,
			wildcard = self.wildcard, style = eval(style, {'__builtins__': None, "wx": wx}, {})) as fileDialog:

			if (fileDialog.ShowModal() == wx.ID_CANCEL):
				value = value
			elif (self.single):
				value = fileDialog.GetPath()
			else:
				value = ", ".join(fileDialog.GetPaths())

		#Create ctrl
		ctrl = wx.TextCtrl(parent, value = value, pos = labelRect.Position, size = labelRect.Size)
		ctrl.SetInsertionPointEnd()
		ctrl.SelectAll()

		return ctrl

	def CreateEditorCtrl_dirOnly(self, parent, labelRect, value):
		#Show Dialog
		style = ["wx.DD_DEFAULT_STYLE "]
		if (self.changeDir):
			style.append("wx.DD_CHANGE_DIR")
		if (self.mustExist):
			style.append("wx.DD_DIR_MUST_EXIST")
		style = "|".join(style)

		if (os.path.exists(value)):
			defaultDir = value
		else:
			defaultDir = ""

		with wx.DirDialog(parent, self.message, defaultPath = defaultDir, defaultFile = defaultFile,
			wildcard = self.wildcard, style = eval(style, {'__builtins__': None, "wx": wx}, {})) as fileDialog:

			if (fileDialog.ShowModal() == wx.ID_CANCEL):
				value = value
			else:
				value = fileDialog.GetPath()

		#Create ctrl
		ctrl = wx.TextCtrl(parent, value = value, pos = labelRect.Position, size = labelRect.Size)
		ctrl.SetInsertionPointEnd()
		ctrl.SelectAll()

		return ctrl

class Renderer_CheckBox(wx.dataview.DataViewToggleRenderer):
	"""
	Changed the default behavior from Inert to Active.
	"""

	def __init__(self, mode = wx.dataview.DATAVIEW_CELL_ACTIVATABLE, **kwargs):

		wx.dataview.DataViewToggleRenderer.__init__(self, mode = mode, **kwargs)
		self.type = "check"
		self.buildingKwargs = {**kwargs, "mode": mode}

	def SetValue(self, value):
		return super().SetValue(bool(value))

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
	They must accept Renderer_Progress as a read-only parameter.

	'editor' determines what type of editor is used to change the value of the progress bar.
	Possible editors are: "text" for a wxTextCtrl, "spin" for a wxSpinCtrl, and "slider" for a wxSlider.
	Alternatively, instead of text, a wxWindow can be given. That wxWindow will be used instead of a pre-defined one.
	"""

	def __init__(self, minimum = 0, maximum = 100, editor = "slider",
		color = wx.BLUE, pen = None, brush = None, 
		mode = wx.dataview.DATAVIEW_CELL_EDITABLE, **kwargs):

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
		self.pen = pen
		self.buildingKwargs["pen"] = pen

	def SetBrush(self, brush = None):
		self.brush = brush
		self.buildingKwargs["brush"] = brush

	def SetValue(self, value):
		try:
			self.value = int(value)
		except TypeError:
			self.value = 0
		return True

	def GetValue(self):
		return self.value

	def GetSize(self):
		return (-1, -1)

	def Render(self, rectangle, dc, state):
		pen = _Munge(self.pen, source = self, returnMunger_onFail = True)
		if (pen is None):
			pen = wx.Pen(wx.BLACK, 1)

		brush = _Munge(self.brush, source = self, returnMunger_onFail = True)
		if (brush is None):
			color = _Munge(self.color, source = self, returnMunger_onFail = True)
			if (color is None):
				color = wx.BLUE
			brush = wx.Brush(color)

		minimum = _Munge(self.minimum, source = self, returnMunger_onFail = True)
		if (minimum is None):
			minimum = 0

		maximum = _Munge(self.maximum, source = self, returnMunger_onFail = True)
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
		return True

	def CreateEditorCtrl(self, parent, labelRect, value):
		editor = _Munge(self.editor, source = self, returnMunger_onFail = True)
		try:
			if (editor.lower() == "text"):
				ctrl = wx.TextCtrl(parent, value = str(value), pos = labelRect.Position, size = labelRect.Size)
				ctrl.SetInsertionPointEnd()
				ctrl.SelectAll()

			else:
				minimum = _Munge(self.minimum, source = self, returnMunger_onFail = True)
				if (minimum is None):
					minimum = 0

				maximum = _Munge(self.maximum, source = self, returnMunger_onFail = True)
				if (maximum is None):
					maximum = 100

				try:
					_value = int(value)
				except TypeError:
					_value = 0

				if (editor.lower() == "slider"):
					ctrl = wx.Slider(parent, value = _value, minValue = int(minimum), maxValue = int(maximum), pos = labelRect.Position, size = labelRect.Size)
				else:
					ctrl = wx.SpinCtrl(parent, pos = labelRect.Position, size = labelRect.Size, min = int(minimum), max = int(maximum), initial = _value)
		except:
			ctrl = editor

		return ctrl

	def GetValueFromEditorCtrl(self, editor):
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

	*default* is what selection the editor defaults to. Can be an integer or string that is in *choices*.
	If *default* is None: Will try using what was in the cell (may not work with formatted text)
	To ensure it is able to use what is currently in the cell, make use 'lambda value: value' for *default*
	
	*default* and *choices* can also be callable functions 
	that accept the following args: unformatted_value, formatted_value
	"""

	def __init__(self, choices = [], ellipsize = True, default = None, **kwargs):

		self.choices = choices
		if (callable(choices)):
			wx.dataview.DataViewChoiceRenderer.__init__(self, [], **kwargs)
		else:
			wx.dataview.DataViewChoiceRenderer.__init__(self, choices, **kwargs)
		self.type = "choice"
		self.buildingKwargs = {**kwargs, "choices": choices}
		
		self.SetDefault(default)
		self.SetEllipsize(ellipsize)

	def Clone(self, **kwargs):
		#Any keywords in kwargs will override keywords in buildingKwargs
		instructions = {**self.buildingKwargs, **kwargs}
		return super().__self_class__(**instructions)

	def SetValue(self, value):
		if (value[1] is None):
			return super().SetValue("")
		return super().SetValue(value[1])

	def SetDefault(self, default = None):
		self.default = default
		self.buildingKwargs["default"] = default

	def SetEllipsize(self, ellipsize = None):
		global _ellipsizeCatalogue
		
		self.ellipsize = ellipsize
		self.buildingKwargs["ellipsize"] = ellipsize

		self.EnableEllipsize(_ellipsizeCatalogue.get(ellipsize, wx.ELLIPSIZE_MIDDLE))

	def CreateEditorCtrl(self, parent, labelRect, value):
		if (callable(self.choices)):
			choices = _Munge(self.choices, source = value[0], extraArgs = [value[1]], returnMunger_onFail = True)
		else:
			choices = self.choices

		default = _Munge(self.default, source = value[0], extraArgs = [value[1]], returnMunger_onFail = True)
		if (default is None):
			default = value[1]

		window = wx.Choice(parent, id = wx.ID_ANY, pos = labelRect.GetTopLeft(), size = labelRect.GetSize(), choices = choices)
		try:
			window.SetSelection(choices.index(default))
		except:
			try:
				window.SetSelection(default)
			except:
				pass

		return window

class Renderer_Icon(wx.dataview.DataViewIconTextRenderer):
	"""
	Depending on what *icon* is initially will determine how 
	the value returned by by *valueGetter* for the assigned *ColumnDefn* is used.
	*icon* should be a wxBitmap or function that returns a wxBitmap; if it is None,
	then no icon will be drawn.
	"""

	def __init__(self, icon = None, editor = None, editRaw = True, ellipsize = True, **kwargs):

		wx.dataview.DataViewIconTextRenderer.__init__(self, **kwargs)
		self.type = "icon"
		self.buildingKwargs = {**kwargs}

		self.SetIcon(icon)
		self.SetEditor(editor)
		self.SetEditRaw(editRaw)
		self.SetEllipsize(ellipsize)

	def SetIcon(self, icon = None):
		self.icon = icon
		self.buildingKwargs["icon"] = icon

	def Clone(self, **kwargs):
		#Any keywords in kwargs will override keywords in buildingKwargs
		instructions = {**self.buildingKwargs, **kwargs}
		return super().__self_class__(**instructions)

	def SetEllipsize(self, ellipsize = None):
		global _ellipsizeCatalogue
		
		self.ellipsize = ellipsize
		self.buildingKwargs["ellipsize"] = ellipsize

		self.EnableEllipsize(_ellipsizeCatalogue.get(ellipsize, wx.ELLIPSIZE_MIDDLE))

class Renderer_Text(wx.dataview.DataViewCustomRenderer, MyUtilities.common.EnsureFunctions):
	"""
	If *editRaw* == True: Edit the un-formatted value
	If *editRaw* == False: Edit the formatted value

	If *autoComplete* is a list: Will use the given list to auto-complete things the user types

	Depending on what *icon* is initially will determine how 
	the value returned by by *valueGetter* for the assigned *ColumnDefn* is used.
	*icon* should be a wxIcon or function that returns a wxIcon; if it is None,
	then no icon will be drawn.
	"""

	def __init__(self, icon = None, iconSize = None, password = False, ellipsize = True, editRaw = True, 
		autoComplete = None, caseSensitive = False, alwaysShow = False, editor = None, **kwargs):

		wx.dataview.DataViewCustomRenderer.__init__(self, **kwargs)
		self.type = "text"
		self.buildingKwargs = {**kwargs}

		self.value = None
		self.patch_edit = False

		self.SetIcon(icon)
		self.SetIconSize(iconSize)
		self.SetEditor(editor)
		self.SetEditRaw(editRaw)
		self.SetPassword(password)
		# self.SetEllipsize(ellipsize)
		self.SetAlwaysShow(alwaysShow)
		self.SetAutoComplete(autoComplete)
		self.SetCaseSensitive(caseSensitive)

	def Clone(self, **kwargs):
		#Any keywords in kwargs will override keywords in buildingKwargs
		instructions = {**self.buildingKwargs, **kwargs}
		return super().__self_class__(**instructions)

	# def SetEllipsize(self, ellipsize = None):
	# 	global _ellipsizeCatalogue
		
	# 	self.ellipsize = ellipsize
	# 	self.buildingKwargs["ellipsize"] = ellipsize

	# 	self.EnableEllipsize(_ellipsizeCatalogue.get(ellipsize, wx.ELLIPSIZE_MIDDLE))

	def SetIcon(self, icon = None):
		self.icon = icon
		self.buildingKwargs["icon"] = icon

	def SetEditor(self, editor = None):
		self.editor = editor
		self.buildingKwargs["editor"] = editor

	def SetEditRaw(self, editRaw = None):
		self.editRaw = editRaw
		self.buildingKwargs["editRaw"] = editRaw

	def SetIconSize(self, iconSize = None):
		self.iconSize = iconSize or (16, 16)
		self.buildingKwargs["iconSize"] = iconSize

	def SetPassword(self, password = None):
		self.password = password
		self.buildingKwargs["password"] = password

	def SetAlwaysShow(self, alwaysShow = None):
		self.alwaysShow = alwaysShow
		self.buildingKwargs["alwaysShow"] = alwaysShow

	def SetAutoComplete(self, autoComplete = None):
		self.autoComplete = autoComplete
		self.buildingKwargs["autoComplete"] = autoComplete

	def SetCaseSensitive(self, caseSensitive = None):
		self.caseSensitive = caseSensitive
		self.buildingKwargs["caseSensitive"] = caseSensitive

	def GetValue(self):
		return self.value

	def SetValue(self, value):
		self.value = value
		return True

	def FinishEditing(self, ctrl = None, fromEvent = False):
		ctrl = ctrl or self.GetEditorCtrl()

		if (not isinstance(ctrl, AutocompleteTextCtrl)):
			if (fromEvent):
				return
			return super().FinishEditing()

		#Skip the next call after the popup menu is shown
		if (ctrl.popup.IsActive()):
			self.patch_edit = True
			return False

		if (self.patch_edit):
			self.patch_edit = False
			return False

		return self.pre_FinishEditing(ctrl)

	def pre_FinishEditing(self, ctrl):
		if (not ctrl.popup.IsActive()):
			ctrl.popup.Hide()
		
		return super().FinishEditing()

	def OnKillFocus(self, event):
		self.FinishEditing(fromEvent = True)
		event.Skip()

	def OnSelectOther(self, event):
		ctrl = self.GetEditorCtrl()

		self.FinishEditing(ctrl = ctrl, fromEvent = True)
		event.Skip()

	def HasEditorCtrl(self):
		return True

	def CreateEditorCtrl(self, parent, rectangle, value):
		self.patch_edit = False
		editor = _Munge(self.editor, source = self, returnMunger_onFail = True)
		if (editor):
			return editor

		editRaw = _Munge(self.editRaw, source = self, returnMunger_onFail = True)
		_value = self.ensure_string(value[not editRaw])

		x, y, width, height = rectangle
		icon = value[2]
		if (icon is not None):
			for image in self.ensure_container(icon):
				width -= image.GetWidth() 

		style = (0, wx.TE_PASSWORD)[self.password]
		autoComplete = _Munge(self.autoComplete, source = self, returnMunger_onFail = True)
		if (autoComplete):
			alwaysShow = _Munge(self.alwaysShow, source = self, returnMunger_onFail = True)
			caseSensitive = _Munge(self.caseSensitive, source = self, returnMunger_onFail = True)
			ctrl = AutocompleteTextCtrl(parent, completer = autoComplete, caseSensitive = caseSensitive, alwaysShow = alwaysShow, 
				value = _value, pos = (x, y), size = (width, height), style = style)

			ctrl.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
			ctrl.Bind(wx.dataview.EVT_DATAVIEW_SELECTION_CHANGED, self.OnSelectOther)
		else:
			ctrl = wx.TextCtrl(parent, value = _value, pos = (x, y), size = (width, height), style = style)
		ctrl.SetInsertionPointEnd()
		ctrl.SelectAll()

		self._editorCtrl = ctrl

		return ctrl

	def GetValueFromEditorCtrl(self, editor):
		return editor.GetValue()

	def GetSize(self):
		return (-1, -1)

	def Render(self, rectangle, dc, state):
		x, y, width, height = rectangle
		totalWidth = 0

		for image in self.ensure_container(self.value[2]):
			try:
				dc.DrawIcon(image, x + totalWidth, y)
			except TypeError:
				dc.DrawBitmap(image, x + totalWidth, y)
			totalWidth += image.GetWidth()
		if (totalWidth >= width):
			return True

		_drawText(dc, text = self.value[1], isSelected = state == wx.dataview.DATAVIEW_CELL_SELECTED, align = wx.Rect(x + totalWidth, y, width - totalWidth, height), x_align = "left")

		return True

class Renderer_Spin(wx.dataview.DataViewSpinRenderer):
	"""
	"""

	def __init__(self, minimum = None, maximum = None, base = 10, editor = None, ellipsize = True, **kwargs):

		wx.dataview.DataViewSpinRenderer.__init__(self, 0, 1, **kwargs)
		self.type = "spin"
		self.buildingKwargs = {**kwargs}

		self.SetEllipsize(ellipsize)
		self.SetEditor(editor)
		self.SetMax(minimum)
		self.SetMin(maximum)
		self.SetBase(base)

	def Clone(self, **kwargs):
		#Any keywords in kwargs will override keywords in buildingKwargs
		instructions = {**self.buildingKwargs, **kwargs}
		return super().__self_class__(**instructions)

	def SetEllipsize(self, ellipsize = None):
		global _ellipsizeCatalogue
		
		self.ellipsize = ellipsize
		self.buildingKwargs["ellipsize"] = ellipsize

		self.EnableEllipsize(_ellipsizeCatalogue.get(ellipsize, wx.ELLIPSIZE_MIDDLE))

	def SetEditor(self, editor = None):
		self.editor = editor
		self.buildingKwargs["editor"] = editor

	def SetMax(self, maximum = None):
		self.maximum = maximum
		self.buildingKwargs["maximum"] = maximum

	def SetMin(self, minimum = None):
		self.minimum = minimum
		self.buildingKwargs["minimum"] = minimum

	def SetBase(self, base = None):
		self.base = base or 0
		self.buildingKwargs["base"] = base

	def HasEditorCtrl(self):
		return True

	def CreateEditorCtrl(self, parent, labelRect, value):

		editor = _Munge(self.editor, source = self, returnMunger_onFail = True)
		if (editor):
			return editor

		minimum = _Munge(self.minimum, source = self, returnMunger_onFail = True)
		if (minimum is None):
			minimum = -999_999_999

		maximum = _Munge(self.maximum, source = self, returnMunger_onFail = True)
		if (maximum is None):
			maximum = 999_999_999

		ctrl = wx.SpinCtrl(parent, pos = labelRect.Position, size = labelRect.Size, min = minimum, max = maximum, initial = value)

		base = _Munge(self.base, source = self, returnMunger_onFail = True)
		if ((base is not None) and (base != 10)):
			ctrl.SetBase(base)
		return ctrl

class Renderer_Bmp(wx.dataview.DataViewBitmapRenderer):
	"""
	"""

	def __init__(self, **kwargs):

		wx.dataview.DataViewBitmapRenderer.__init__(self, **kwargs)
		self.type = "bmp"
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
	"file":      {"edit": wx.dataview.DATAVIEW_CELL_EDITABLE, 		"nonEdit": wx.dataview.DATAVIEW_CELL_ACTIVATABLE, 	"class": Renderer_File},
}

