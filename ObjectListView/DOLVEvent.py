# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Name:         OLVEvent.py
# Author:       Phillip Piper
# Created:      3 April 2008
# Copyright:    (c) 2008 by Phillip Piper, 2008
# License:      wxWindows license
#----------------------------------------------------------------------------
# Change log:
# 2008/08/18  JPP   Added CELL_EDIT_STARTED and CELL_EDIT_FINISHED events
# 2008/07/16  JPP   Added group-related events
# 2008/06/19  JPP   Added EVT_SORT
# 2008/05/26  JPP   Fixed pyLint annoyances
# 2008/04/04  JPP   Initial version complete
#----------------------------------------------------------------------------
# To do:

"""
The OLVEvent module holds all the events used by the ObjectListView module.
"""

__author__ = "Phillip Piper"
__date__ = "3 August 2008"

import wx

#======================================================================
# Event ids and types


def _EventMaker():
	evt = wx.NewEventType()
	return (evt, wx.PyEventBinder(evt))

(olv_EVT_DATA_CELL_EDIT_STARTING, EVT_DATA_CELL_EDIT_STARTING) = _EventMaker()
(olv_EVT_DATA_CELL_EDIT_STARTED, EVT_DATA_CELL_EDIT_STARTED) = _EventMaker()
(olv_EVT_DATA_CELL_EDIT_FINISHING, EVT_DATA_CELL_EDIT_FINISHING) = _EventMaker()
(olv_EVT_DATA_CELL_EDIT_FINISHED, EVT_DATA_CELL_EDIT_FINISHED) = _EventMaker()

(olv_EVT_DATA_SORTING, EVT_DATA_SORTING) = _EventMaker()
(olv_EVT_DATA_SORTED, EVT_DATA_SORTED) = _EventMaker()
(olv_EVT_DATA_REORDER, EVT_DATA_REORDER) = _EventMaker()

(olv_EVT_DATA_GROUP_CREATING, EVT_DATA_GROUP_CREATING) = _EventMaker()
(olv_EVT_DATA_MENU_CREATING, EVT_DATA_MENU_CREATING) = _EventMaker()
(olv_EVT_DATA_MENU_ITEM_SELECTED, EVT_DATA_MENU_ITEM_SELECTED) = _EventMaker()

(olv_EVT_DATA_EXPANDING, EVT_DATA_EXPANDING) = _EventMaker()
(olv_EVT_DATA_EXPANDED, EVT_DATA_EXPANDED) = _EventMaker()
(olv_EVT_DATA_COLLAPSING, EVT_DATA_COLLAPSING) = _EventMaker()
(olv_EVT_DATA_COLLAPSED, EVT_DATA_COLLAPSED) = _EventMaker()

(olv_EVT_DATA_CELL_LEFT_CLICK, EVT_DATA_CELL_LEFT_CLICK) = _EventMaker()
(olv_EVT_DATA_CELL_RIGHT_CLICK, EVT_DATA_CELL_RIGHT_CLICK) = _EventMaker()
(olv_EVT_DATA_CELL_ACTIVATED, EVT_DATA_CELL_ACTIVATED) = _EventMaker()

(olv_EVT_DATA_SELECTION_CHANGED, EVT_DATA_SELECTION_CHANGED) = _EventMaker()
(olv_EVT_DATA_GROUP_SELECTED, EVT_DATA_GROUP_SELECTED) = _EventMaker()

(olv_EVT_DATA_COLUMN_HEADER_LEFT_CLICK, EVT_DATA_COLUMN_HEADER_LEFT_CLICK) = _EventMaker()
(olv_EVT_DATA_COLUMN_HEADER_RIGHT_CLICK, EVT_DATA_COLUMN_HEADER_RIGHT_CLICK) = _EventMaker()

(olv_EVT_DATA_COPYING, EVT_DATA_COPYING) = _EventMaker()
(olv_EVT_DATA_COPY, EVT_DATA_COPY) = _EventMaker()
(olv_EVT_DATA_COPIED, EVT_DATA_COPIED) = _EventMaker()
(olv_EVT_DATA_PASTING, EVT_DATA_PASTING) = _EventMaker()
(olv_EVT_DATA_PASTE, EVT_DATA_PASTE) = _EventMaker()

(olv_EVT_DATA_UNDO, EVT_DATA_UNDO) = _EventMaker()
(olv_EVT_DATA_UNDO_TRACK, EVT_DATA_UNDO_TRACK) = _EventMaker()
(olv_EVT_DATA_UNDO_FIRST, EVT_DATA_UNDO_FIRST) = _EventMaker()
(olv_EVT_DATA_UNDO_EMPTY, EVT_DATA_UNDO_EMPTY) = _EventMaker()
(olv_EVT_DATA_REDO, EVT_DATA_REDO) = _EventMaker()
(olv_EVT_DATA_REDO_FIRST, EVT_DATA_REDO_FIRST) = _EventMaker()
(olv_EVT_DATA_REDO_EMPTY, EVT_DATA_REDO_EMPTY) = _EventMaker()


#======================================================================
# Event parameter blocks


class VetoableEvent(wx.PyCommandEvent):

	"""
	Base class for all cancellable actions
	"""

	def __init__(self, evtType):
		wx.PyCommandEvent.__init__(self, evtType, -1)
		self.veto = False

	def Veto(self, isVetoed=True):
		"""
		Veto (or un-veto) this event
		"""
		self.veto = isVetoed

	def IsVetoed(self):
		"""
		Has this event been vetod?
		"""
		return self.veto

#----------------------------------------------------------------------------
#Rows

class SelectionChangedEvent(wx.PyCommandEvent):
	"""
	The selection of the DataViewCtrl has changed.
	"""

	def __init__(self, objectListView, **kwargs):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_SELECTION_CHANGED, -1)
		
		self.SetEventObject(objectListView)
		self.objectListView = objectListView
		self.row = kwargs.pop("row", None)

class CellLeftClickEvent(wx.PyCommandEvent):
	"""
	A cell has been left-clicked.
	"""

	def __init__(self, objectListView, **kwargs):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_CELL_LEFT_CLICK, -1)
		
		self.SetEventObject(objectListView)
		self.objectListView = objectListView
		self.row = kwargs.pop("row", None)

class CellRightClickEvent(wx.PyCommandEvent):
	"""
	A cell has been right-clicked.
	Will not fire if *showContextMenu* is True.
	"""

	def __init__(self, objectListView, **kwargs):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_CELL_RIGHT_CLICK, -1)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView
		self.row = kwargs.pop("row", None)

class CellActivatedEvent(wx.PyCommandEvent):
	"""
	A cell has been activated (double clicked).
	"""

	def __init__(self, objectListView, **kwargs):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_CELL_ACTIVATED, -1)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView
		self.row = kwargs.pop("row", None)

#----------------------------------------------------------------------------
#Columns

class ColumnHeaderLeftClickEvent(wx.PyCommandEvent):
	"""
	A column header has been clicked.
	"""

	def __init__(self, objectListView, **kwargs):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_COLUMN_HEADER_LEFT_CLICK, -1)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView
		self.column = kwargs.pop("column", None)
		self.ascending = kwargs.pop("ascending", None)
		self.index = kwargs.pop("index", None)

class ColumnHeaderRightClickEvent(wx.PyCommandEvent):
	"""
	A column header has been right-clicked.
	Note: Currently this event is not generated in the native OS X versions of wx.dataview.DataViewCtrl
	Will not fire if *showLabelContextMenu* is True.
	"""

	def __init__(self, objectListView, **kwargs):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_COLUMN_HEADER_RIGHT_CLICK, -1)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView
		self.column = kwargs.pop("column", None)
		self.ascending = kwargs.pop("ascending", None)
		self.index = kwargs.pop("index", None)

#----------------------------------------------------------------------------
#Groups

class GroupCreationEvent(wx.PyCommandEvent):
	"""
	The user is about to create one or more groups.

	The handler can mess with the list of groups before they are created: change their
	names, give them icons, remove them from the list to stop them being created
	(that last behaviour could be very confusing for the users).
	"""

	def __init__(self, objectListView, groups = []):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_GROUP_CREATING, -1)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView
		self.groups = groups

class CollapsingEvent(VetoableEvent):
	"""
	A group will collapse.
	If the handler calls Veto() for the event, the action will be cancelled.
	"""

	def __init__(self, objectListView, **kwargs):
		VetoableEvent.__init__(self, olv_EVT_DATA_COLLAPSING)
		
		self.SetEventObject(objectListView)
		self.objectListView = objectListView
		self.group = kwargs.pop("row", None)

class ExpandingEvent(VetoableEvent):
	"""
	A group will expand.
	If the handler calls Veto() for the event, the action will be cancelled.
	"""

	def __init__(self, objectListView, **kwargs):
		VetoableEvent.__init__(self, olv_EVT_DATA_EXPANDING)
		
		self.SetEventObject(objectListView)
		self.objectListView = objectListView
		self.group = kwargs.pop("row", None)

class CollapsedEvent(wx.PyCommandEvent):
	"""
	A group has collapsed.
	"""

	def __init__(self, objectListView, **kwargs):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_COLLAPSED, -1)
		
		self.SetEventObject(objectListView)
		self.objectListView = objectListView
		self.group = kwargs.pop("row", None)

class ExpandedEvent(wx.PyCommandEvent):
	"""
	A group has expanded.
	"""

	def __init__(self, objectListView, **kwargs):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_EXPANDED, -1)
		
		self.SetEventObject(objectListView)
		self.objectListView = objectListView
		self.group = kwargs.pop("row", None)

class GroupSelectedEvent(wx.PyCommandEvent):
	"""
	A group was selected.
	"""

	def __init__(self, objectListView, **kwargs):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_GROUP_SELECTED, -1)
		
		self.SetEventObject(objectListView)
		self.objectListView = objectListView
		self.group = kwargs.pop("row", None)

#----------------------------------------------------------------------------
#Sorting

class SortingEvent(VetoableEvent):
	"""
	The user wants to sort the ObjectListView.

	If the handler calls Veto(), no further default processing will be done.
	If the handler calls Handled(), default processing concerned with UI will be done. This
	includes updating sort indicators.
	If the handler calls neither of these, all default processing will be done.
	"""

	def __init__(self, objectListView, column = None, index = None, ascending = None):
		VetoableEvent.__init__(self, olv_EVT_DATA_SORTING)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView
		
		self.index = index
		self.column = column
		self.ascending = ascending
		self.wasHandled = False

	def Handled(self, wasHandled=True):
		"""
		Indicate that the event handler has sorted the ObjectListView.
		The OLV will handle other tasks like updating sort indicators
		"""
		self.wasHandled = wasHandled

class SortedEvent(wx.PyCommandEvent):
	"""
	Sorting has finished.
	"""

	def __init__(self, objectListView, **kwargs):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_SORTED, -1)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.index = kwargs.pop("index", None)
		self.column = kwargs.pop("column", None)
		self.ascending = kwargs.pop("ascending", None)

class ReorderEvent(wx.PyCommandEvent):
	"""
	Data was reordered.
	"""

	def __init__(self, objectListView, **kwargs):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_REORDER, -1)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.index = kwargs.pop("index", None)
		self.column = kwargs.pop("column", None)
		self.ascending = kwargs.pop("ascending", None)

#----------------------------------------------------------------------------
#Editing

class EditCellStartingEvent(VetoableEvent):
	"""
	A cell has started to be edited.

	Veto() will not allow the edit to happen.

	All attributes are public and should be considered read-only.
	"""

	def __init__(self, objectListView, **kwargs):
		VetoableEvent.__init__(self, olv_EVT_DATA_CELL_EDIT_STARTING)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.index = kwargs.pop("index", None)
		self.column = kwargs.pop("column", None)
		self.ascending = kwargs.pop("ascending", None)
		self.row = kwargs.pop("row", None)

class EditCellStartedEvent(wx.PyCommandEvent):
	"""
	A cell has started to be edited.

	All attributes are public and should be considered read-only.
	"""

	def __init__(self, objectListView, **kwargs):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_CELL_EDIT_STARTED, -1)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.index = kwargs.pop("index", None)
		self.column = kwargs.pop("column", None)
		self.ascending = kwargs.pop("ascending", None)
		self.row = kwargs.pop("row", None)

class EditCellFinishingEvent(VetoableEvent):
	"""
	The user has finished editing a cell.

	All attributes are public and should be considered read-only.
	"""

	def __init__(self, objectListView, **kwargs):
		VetoableEvent.__init__(self, olv_EVT_DATA_CELL_EDIT_FINISHING)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.index = kwargs.pop("index", None)
		self.column = kwargs.pop("column", None)
		self.ascending = kwargs.pop("ascending", None)
		self.row = kwargs.pop("row", None)
		self.value = kwargs.pop("value", None)
		self.editCanceled = kwargs.pop("editCanceled", None)

class EditCellFinishedEvent(wx.PyCommandEvent):
	"""
	The edited value has been applied.
	"""

	def __init__(self, objectListView, **kwargs):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_CELL_EDIT_FINISHED, -1)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.index = kwargs.pop("index", None)
		self.column = kwargs.pop("column", None)
		self.ascending = kwargs.pop("ascending", None)
		self.row = kwargs.pop("row", None)
		self.value = kwargs.pop("value", None)
		self.editCanceled = kwargs.pop("editCanceled", None)

#----------------------------------------------------------------------------
#Context Menu

class MenuCreationEvent(VetoableEvent):
	"""
	The context menu will begin building.

	Veto() will not allow the menu to be built or shown.
	If this happens, EVT_DATA_CELL_RIGHT_CLICK will fire.

	The handler can mess with the menu before it is shown.
	"""

	def __init__(self, objectListView, **kwargs):
		VetoableEvent.__init__(self, olv_EVT_DATA_MENU_CREATING)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.index = kwargs.pop("index", None)
		self.column = kwargs.pop("column", None)
		self.row = kwargs.pop("row", None)
		self.menu = kwargs.pop("menu", None)

class MenuItemSelectedEvent(VetoableEvent):
	"""
	A menu item has been selected.

	Veto() will not allow any functions that 
	the menu item should run to be ran.
	"""

	def __init__(self, objectListView, **kwargs):
		VetoableEvent.__init__(self, olv_EVT_DATA_MENU_ITEM_SELECTED)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.index = kwargs.pop("index", None)
		self.column = kwargs.pop("column", None)
		self.row = kwargs.pop("row", None)
		self.item = kwargs.pop("item", None)

#----------------------------------------------------------------------------
#Copy/Paste

class CopyingEvent(VetoableEvent):
	"""
	Values from items in the list will be copied.

	Veto() will not allow the items to be copied.

	The handler can mess with what rows and columns are copied from.
	"""

	def __init__(self, objectListView, **kwargs):
		VetoableEvent.__init__(self, olv_EVT_DATA_COPYING)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.text = None
		self.rows = kwargs.pop("rows", [])
		self.columns = kwargs.pop("columns", [])

	def SetText(self, text = None):
		"""
		Set the text to be put on the clipboard yourself.
		If *text* is None, the program will determine what the clipboard should look like.
		"""
		self.text = text

class CopiedEvent(wx.PyCommandEvent):
	"""
	Allows the user to modify *log* (the 'what was copied list of dictionaries') 
	before it is saved.	*text* can also be modified before it goes on the clipboard.
	"""

	def __init__(self, objectListView, **kwargs):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_COPIED, -1)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.log = kwargs.pop("log", [])
		self.text = kwargs.pop("text", "")
		self.rows = kwargs.pop("rows", [])
		self.columns = kwargs.pop("columns", [])

class CopyEvent(VetoableEvent):
	"""
	A row is going to be copied.

	Veto() will not allow the item to be copied.
	"""

	def __init__(self, objectListView, **kwargs):
		VetoableEvent.__init__(self, olv_EVT_DATA_COPY)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.row = kwargs.pop("row", [])
		self.columns = kwargs.pop("columns", [])
		self.text = None

	def SetText(self, text = None):
		"""
		Set the text to be put on the clipboard yourself.
		If *text* is None, the program will determine what the clipboard should look like.
		"""
		self.text = text

class PastingEvent(VetoableEvent):
	"""
	Values from copied items will be pasted.

	Veto() will not allow the items to be pasted.

	The handler can mess with what values are pasted to what columns.
	"""

	def __init__(self, objectListView, **kwargs):
		VetoableEvent.__init__(self, olv_EVT_DATA_PASTING)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.log = kwargs.pop("log", [])
		self.rows = kwargs.pop("rows", [])
		self.column = kwargs.pop("column", -1)

class PasteEvent(VetoableEvent):
	"""
	A row is going to be pasted.

	Veto() will not allow the item to be pasted.

	Handled() will cause the program to skip changing the value, but still update the cell.
	If you handle it on your own, your change will not be placed in the undo history
	unless you add it to the history yourself.
	"""

	def __init__(self, objectListView, **kwargs):
		VetoableEvent.__init__(self, olv_EVT_DATA_PASTE)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.row = kwargs.pop("row", [])
		self.value = kwargs.pop("value", None)
		self.column = kwargs.pop("column", [])
		self.editCanceled = kwargs.pop("editCanceled", None)
		self.wasHandled = False

	def Handled(self, wasHandled = True):
		"""
		Indicate that the event handler has changed the value.
		The OLV will handle other tasks like updating the cell.
		"""
		self.wasHandled = wasHandled

#----------------------------------------------------------------------------
#Undo/Redo

class UndoEmptyEvent(wx.PyCommandEvent):
	"""
	Notifies the user that the undo history is empty.
	This is a good time to disable whatever widget calls the undo action
	"""

	def __init__(self, objectListView, **kwargs):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_UNDO_EMPTY, -1)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.type = kwargs.pop("type", None)

class RedoEmptyEvent(wx.PyCommandEvent):
	"""
	Notifies the user that the redo history is empty.
	This is a good time to disable whatever widget calls the redo action
	"""

	def __init__(self, objectListView, **kwargs):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_REDO_EMPTY, -1)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.type = kwargs.pop("type", None)

class UndoFirstEvent(wx.PyCommandEvent):
	"""
	Notifies the user that the undo history has recieved it's first action.
	This is a good time to enable whatever widget calls the undo action
	"""

	def __init__(self, objectListView, **kwargs):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_UNDO_FIRST, -1)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.type = kwargs.pop("type", None)

class RedoFirstEvent(wx.PyCommandEvent):
	"""
	Notifies the user that the redo history has recieved it's first action.
	This is a good time to enable whatever widget calls the redo action
	"""

	def __init__(self, objectListView, **kwargs):
		wx.PyCommandEvent.__init__(self, olv_EVT_DATA_REDO_FIRST, -1)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.type = kwargs.pop("type", None)

class UndoEvent(VetoableEvent):
	"""
	An action is going to be undone.

	Veto() will not allow the item to be undone.

	Handled() will cause the program to consider the action undone, and will
	remove the action from the undo history and placed in the redo history.
	"""

	def __init__(self, objectListView, **kwargs):
		VetoableEvent.__init__(self, olv_EVT_DATA_UNDO)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.row = kwargs.pop("row", [])
		self.type = kwargs.pop("type", None)
		self.value = kwargs.pop("value", None)
		self.column = kwargs.pop("column", [])
		self.editCanceled = kwargs.pop("editCanceled", None)
		self.wasHandled = False

	def Handled(self, wasHandled = True):
		"""
		Indicate that the event handler has changed the value.
		The OLV will handle other tasks like removing the action from the undo history
		and placing it in the redo history.
		"""
		self.wasHandled = wasHandled

class RedoEvent(VetoableEvent):
	"""
	An action is going to be redone.

	Veto() will not allow the item to be redone.

	Handled() will cause the program to consider the action redone, and will
	remove the action from the redo history and placed in the undo history.
	"""

	def __init__(self, objectListView, **kwargs):
		VetoableEvent.__init__(self, olv_EVT_DATA_REDO)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.row = kwargs.pop("row", [])
		self.type = kwargs.pop("type", None)
		self.value = kwargs.pop("value", None)
		self.column = kwargs.pop("column", [])
		self.editCanceled = kwargs.pop("editCanceled", None)
		self.wasHandled = False

	def Handled(self, wasHandled = True):
		"""
		Indicate that the event handler has changed the value.
		The OLV will handle other tasks like removing the action from the redo history
		and placing it in the undo history.
		"""
		self.wasHandled = wasHandled

class UndoTrackEvent(VetoableEvent):
	"""
	An action is going to be tracked in the undo history

	Veto() will not allow the item to be tracked.

	The user can modify the tracked event here if they need to.
	"""

	def __init__(self, objectListView, **kwargs):
		VetoableEvent.__init__(self, olv_EVT_DATA_UNDO_TRACK)
		self.SetEventObject(objectListView)
		self.objectListView = objectListView

		self.type = kwargs.pop("type", None)
		self.action = kwargs.pop("action", None)
