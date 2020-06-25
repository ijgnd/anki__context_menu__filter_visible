"""
Add-on for Anki
Copyright (c): 2020 ijgnd
               Ankitects Pty Ltd and contributors


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.


This add-on uses the file filter_functions.py which has this copyright and permission notice:

    Copyright (c): 2018  Rene Schallner
                   2019- ijgnd

    This file (filter_functions.py) is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This file is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this file.  If not, see <http://www.gnu.org/licenses/>.

"""


from anki.lang import _
from aqt import mw
from aqt.gui_hooks import (
    browser_menus_did_init,
    browser_will_show_context_menu,
    editor_did_init_shortcuts,
    editor_will_show_context_menu,
    reviewer_will_show_context_menu,
)
from aqt.qt import (
    QAction,
    QContextMenuEvent,
    QCursor,
    QKeySequence,
    QLineEdit,
    QMenu,
    QShortcut,
    QWidget,
    QWidgetAction,
    qconnect,
)
from aqt.utils import (
    qtMenuShortcutWorkaround,
)
from aqt.browser import Browser
from aqt.editor import EditorWebView
from aqt.reviewer import Reviewer

from .filter_functions import (
    does_it_match,
    split_search_terms_withStart,
)


def gc(arg, fail=False):
    conf = mw.addonManager.getConfig(__name__)
    if conf:
        return conf.get(arg, fail)
    else:
        return fail


stylesheet = """
QMenu::item {
    padding-top: 5px;
    padding-bottom: 5px;
    padding-right: 75px;
    padding-left: 20px;
    font-size: 13px;
}
QMenu::item:selected {
    background-color: #fd4332;
}
"""


# NOTE: I have three approaches for modifying the context menu. Mabe I should consolidate
#       them at some point.


class MyFilterMenu(QMenu):
    def __init__(self, *args, **kwargs):
        super(QMenu, self).__init__(*args, **kwargs)
        self.setStyleSheet(stylesheet)
        self.le = QLineEdit()
        self.le.textChanged.connect(self.text_changed)
        self.le_container = QWidgetAction(self)  # self.editor.widget
        self.le_container.setDefaultWidget(self.le)
        self.addAction(self.le_container)
        self.le.setFocus()

    def text_changed(self):
        search_string = self.le.text()
        if not search_string:
            search_string = ""
        search_string = search_string.lower()
        search_terms = split_search_terms_withStart(search_string)
        for element in self.children():
            if isinstance(element, QMenu):
                if not does_it_match(search_terms, element.title()):
                    element.menuAction().setVisible(False)
                else:
                    element.menuAction().setVisible(True)
            elif isinstance(element, QAction):
                if hasattr(element, "defaultWidget"):
                    continue
                if not does_it_match(search_terms, element.text()):
                    if element.isVisible():
                        element.setVisible(False)
                else:
                    if not element.isVisible():
                        element.setVisible(True)
        self.le.setFocus()


def editor_context_helper(self):
    # self is EditorWebView
    m = MyFilterMenu(self)

    m.addSection("built-in")
    a = m.addAction(_("Cut"))
    qconnect(a.triggered, self.onCut)
    a = m.addAction(_("Copy"))
    qconnect(a.triggered, self.onCopy)
    a = m.addAction(_("Paste"))
    qconnect(a.triggered, self.onPaste)
    m.addSeparator()
    editor_will_show_context_menu(self, m)
    m.popup(QCursor.pos())


def editor_contextMenuEvent(self, evt: QContextMenuEvent) -> None:
    # self is EditorWebView
    editor_context_helper(self)
if gc("editor: enable this add-on"):
    EditorWebView.contextMenuEvent = editor_contextMenuEvent



def onSetupEditorShortcuts(cuts, editor):
    sc = gc("editor: additional shortcut for context menu")
    if sc:
        pair = (sc, lambda ewv=editor.web: editor_contextMenuEvent(ewv))
        cuts.append(pair)
if gc("editor: enable this add-on"):
    editor_did_init_shortcuts.append(onSetupEditorShortcuts)




class MyBrowserFilterMenu(QMenu):
    def __init__(self, *args, **kwargs):
        super(QMenu, self).__init__(*args, **kwargs)
        self.setStyleSheet(stylesheet)
        self.le = QLineEdit()
        self.le.textChanged.connect(self.text_changed)
        self.le_container = QWidgetAction(self)  # self.editor.widget
        self.le_container.setDefaultWidget(self.le)
        self.addAction(self.le_container)
        self.le.setFocus()
        self.aboutToHide.connect(self.make_sure_all_are_visible)

    def make_sure_all_are_visible(self):
        for element in self.actions():
            if not element.isVisible():
                element.setVisible(True)

    def text_changed(self):
        search_string = self.le.text()
        if not search_string:
            search_string = ""
        search_string = search_string.lower()
        search_terms = split_search_terms_withStart(search_string)
        # doesn't work here: Maybe because these actions are defined in QtDesigner/the menu ?
        # for element in self.children():
        for element in self.actions():
            # print(element, type(element), element.text())
            if hasattr(element, "defaultWidget"):
                continue
            if not does_it_match(search_terms, element.text()):
                if element.isVisible():
                    element.setVisible(False)
            else:
                if not element.isVisible():
                    element.setVisible(True)
        self.le.setFocus()


def browser_context_helper(self):
    m = MyBrowserFilterMenu(self)  #  m = QMenu()
    for act in self.form.menu_Cards.actions():
        m.addAction(act)
    m.addSeparator()
    for act in self.form.menu_Notes.actions():
        m.addAction(act)
    browser_will_show_context_menu(self, m)
    qtMenuShortcutWorkaround(m)
    m.exec_(QCursor.pos())  # m.exec_(QCursor.pos())  exec_ is necessary unless I do MyBrowserFilterMenu(self)


def browser_onContextMenu(self, _point) -> None:
    browser_context_helper(self)
if gc("browser (table): enable this add-on"):
    Browser.onContextMenu = browser_onContextMenu


def setupBrowserShortcuts(self):
    # self is browser
    cut = gc("browser (table): additional shortcut for context menu")
    if cut:
        cm = QShortcut(QKeySequence(cut), self)
        qconnect(cm.activated, lambda b=self: browser_context_helper(b))
if gc("browser (table): enable this add-on"):
    browser_menus_did_init.append(setupBrowserShortcuts)



'''
def reviewerShowContextMenu(self) -> None:
    opts = self._contextMenu()
    m = MyFilterMenu(self.mw)
    self._addMenuItems(m, opts)

    reviewer_will_show_context_menu(self, m)
    qtMenuShortcutWorkaround(m)
    m.exec_(QCursor.pos())
Reviewer.showContextMenu = reviewerShowContextMenu

# doesn't help
# mw.setupReviewer()

# https://stackoverflow.com/questions/50599045/python-replacing-a-function-within-a-class-of-a-module
# doesn't work:
# mw.reviewer.showContextMenu = reviewerShowContextMenu.__get__(mw.reviewer, Reviewer)

# doesn't work:
#import types
#mw.reviewer.showContextMenu = types.MethodType(reviewerShowContextMenu, mw.reviewer)
'''



# since custom context menus won't load I modify the reviewer
# https://doc.qt.io/qt-5/qwidget.html#insertAction : I need a "QAction *before"
# https://stackoverflow.com/questions/54120195/slotting-in-new-items-at-specified-positions-in-qmenu


def text_changed(self):
    search_string = self.le.text()
    if not search_string:
        search_string = ""
    search_string = search_string.lower()
    search_terms = split_search_terms_withStart(search_string)
    for element in self.children():
        if isinstance(element, QMenu):
            if not does_it_match(search_terms, element.title()):
                element.menuAction().setVisible(False)
            else:
                element.menuAction().setVisible(True)
        elif isinstance(element, QAction):
            if hasattr(element, "defaultWidget"):
                continue
            if not does_it_match(search_terms, element.text()):
                if element.isVisible():
                    element.setVisible(False)
            else:
                if not element.isVisible():
                    element.setVisible(True)
    self.le.setFocus()


from anki.lang import _
from anki.hooks import addHook
def ReviewerContextMenu(view, menu):
    if mw.state != "review":
        return
    self = menu
    self.setStyleSheet(stylesheet)
    self.le = QLineEdit()
    self.le.textChanged.connect(lambda: text_changed(self))
    self.le_container = QWidgetAction(self)  # self.editor.widget
    self.le_container.setDefaultWidget(self.le)

    for element in self.children():
        if isinstance(element, QAction):
            if element.text() == _("Copy"):
                self.insertAction(element, self.le_container)
                self.le.setFocus()
if gc("reviewer: enable this add-on"):
    addHook("AnkiWebView.contextMenuEvent", ReviewerContextMenu)


def reviewer_shortcuts_21(shortcuts):
    scut = gc("reviewer: additional shortcut for context menu")
    if scut:
        additions = (
            (scut, lambda: mw.reviewer.showContextMenu()),
        )
        shortcuts += additions
if gc("reviewer: enable this add-on"):
    addHook("reviewStateShortcuts", reviewer_shortcuts_21)
