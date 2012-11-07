#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import gtk
import sqlalchemy
import dictionary
import sorder
import vocabulary
import texteditor

VOCABULARY_DB = "sqlite:///data/vocabulary.db"
GLADE_FILE = "taipan.glade"

class Taipan:
    def __init__(self):
        # Fire up GtkBuilder
        builder = gtk.Builder() 
        builder.add_from_file(GLADE_FILE)
        
        # Get main window and connect events
        self.window = builder.get_object("MainWindow")
        self.window.connect("destroy", gtk.main_quit)

        # Setup toolbar
        toolbar = builder.get_object("MainToolbar")
        icon = gtk.Image()
        icon.set_from_stock(gtk.STOCK_DIRECTORY, 4)
        toolbar.append_item(" Open", "Tooltip text", "", icon, self._foo)

        # Init dictionary
        self.dictionary = dictionary.DictionaryWidget()

        # Get dictionary frame and add dictionary to it
        frm = builder.get_object("frm_dict")
        frm.add(self.dictionary)

        # Demo treeview
        self.ntb = builder.get_object("ntb")
        vocab = vocabulary.VocabularyWidget()
        label = gtk.Label("Vocabulary")
        self.ntb.append_page(vocab, label)

        # Get notebook and insert demopage
        label = gtk.Label("TextView")
        editor = texteditor.TexteditorWidget()
        self.ntb.append_page(editor, label)

    def start(self):
        self.window.show_all()
        gtk.gdk.threads_init()
        gtk.gdk.threads_enter() 
        gtk.main()
        gtk.gdk.threads_leave()

    def _foo(self):
        pass

# If directly called, start the GUI
if __name__ == "__main__":
    tp = Taipan()
    tp.start()

