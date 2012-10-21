#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import gtk
import sqlalchemy

VOCABULARY_DB = "sqlite:///data/vocabulary.db"

class EntryDialog(gtk.MessageDialog):
    def __init__(self, *args, **kwargs):
        '''
        Creates a new EntryDialog. Takes all the arguments of the usual
        MessageDialog constructor plus one optional named argument 
        "default_value" to specify the initial contents of the entry.
        '''
        if 'default_value' in kwargs:
            default_value = kwargs['default_value']
            del kwargs['default_value']
        else:
            default_value = ''
        super(EntryDialog, self).__init__(*args, **kwargs)
        entry = gtk.Entry()        
        entry.set_text(str(default_value))
        entry.connect("activate", 
                      lambda ent, dlg, resp: dlg.response(resp), 
                      self, gtk.RESPONSE_OK)
        self.vbox.pack_end(entry, True, True, 0)
        self.vbox.show_all()
        self.entry = entry

    def set_value(self, text):
        self.entry.set_text(text)

    def run(self):
        result = super(EntryDialog, self).run()
        if result == gtk.RESPONSE_OK:
            text = self.entry.get_text()
        else:
            text = None
        return text


class VocabularyWidget(gtk.VBox):
    def __init__(self):
        gtk.VBox.__init__(self)

        # Setup DB
        self.db = sqlalchemy.create_engine(VOCABULARY_DB)
        self.tb_les = sqlalchemy.Table('lessons', 
                                       sqlalchemy.MetaData(self.db),
                                       autoload=True)
        
        # create toolbar
        toolbar = gtk.Toolbar()
        self.lessons = gtk.ListStore(int, str)
        self.cmb_lessons = gtk.ComboBox(self.lessons)
        cell = gtk.CellRendererText()
        self.cmb_lessons.pack_start(cell, True)
        self.cmb_lessons.add_attribute(cell, 'text', 1)
        self.cmb_lessons.connect("changed", self._on_lesson_changed)
        toolbar.append_element(gtk.TOOLBAR_CHILD_WIDGET, self.cmb_lessons, 
                               "Lesson", None, None, None, lambda : None, None)
        icon = gtk.Image()
        icon.set_from_stock(gtk.STOCK_ADD, 4)
        toolbar.append_element(gtk.TOOLBAR_CHILD_BUTTON, None, "New", 
                               "Add a new lesson", None, icon, 
                               self._on_new_clicked, None)

        self.pack_start(toolbar, expand=False, fill=False)

        # create vocabulary table
        self.table = VocabularyTable(self.db)
        self.pack_start(self.table)

        # load data from database
        self._load_lessons()

    def _load_lessons(self):
        res = self.tb_les.select().execute()
        self.lessons.clear()
        i = 1
        for r in res:
            self.lessons.append([r[0], str(i) + " - " + r[1]])
            i += 1
        self.cmb_lessons.set_active(i-2)

    def _on_new_clicked(self, widget):
        dialog = EntryDialog(None, gtk.DIALOG_MODAL,
                gtk.MESSAGE_INFO, gtk.BUTTONS_OK_CANCEL,
                "Enter the name of the new lesson")
        response = dialog.run()
        dialog.destroy()
        if response != None and response != '':
            self.db.execute(self.tb_les.insert().values(name=response))
            self._load_lessons()

    def _on_lesson_changed(self, widget):
        lesson_id = widget.get_model()[widget.get_active()][0]
        self.table.load(lesson_id)


class VocabularyTable(gtk.TreeView):
    def __init__(self, db):
        gtk.TreeView.__init__(self)

        # Setup DB
        self.db = db
        self.tb_vocab = sqlalchemy.Table('vocabulary', 
                                         sqlalchemy.MetaData(self.db), 
                                         autoload=True)

        self.model = gtk.ListStore(int, str, str, str, str, int)
        self.set_model(self.model)

        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.connect("key_press_event", self._on_key_press)

        self.col_chars = gtk.TreeViewColumn('Characters')
        self.col_reading = gtk.TreeViewColumn('Pinyin')
        self.col_trans = gtk.TreeViewColumn('Translation')

        self.append_column(self.col_chars)
        self.append_column(self.col_reading)
        self.append_column(self.col_trans)

        self.cel_chars = gtk.CellRendererText()
        self.cel_chars.set_property('editable', True)
        self.cel_chars.connect("edited", self._on_cell_edited, 1)
        self.cel_reading = gtk.CellRendererText()
        self.cel_reading.set_property('editable', True)
        self.cel_reading.connect("edited", self._on_cell_edited, 3)
        self.cel_trans = gtk.CellRendererText()
        self.cel_trans.set_property('editable', True)
        self.cel_trans.connect("edited", self._on_cell_edited, 4)

        self.col_chars.pack_start(self.cel_chars, False)
        self.col_reading.pack_start(self.cel_reading, False)
        self.col_trans.pack_start(self.cel_trans, False)

        self.col_chars.set_attributes(self.cel_chars, text=1)
        self.col_reading.set_attributes(self.cel_reading, text=3)
        self.col_trans.set_attributes(self.cel_trans, text=4)

        self.col_chars.set_sort_column_id(1)
        self.col_reading.set_sort_column_id(3)
        self.col_trans.set_sort_column_id(4)

    def load(self, lesson):
        self.lesson = lesson
        res = self.tb_vocab.select(self.tb_vocab.c.lesson == lesson).execute()
        self.model.clear()
        for r in res:
            self.model.append(r)
        self.model.append([-1, '', '', '', '', lesson])

    def _on_key_press(self, widget, event):
        if event.keyval == gtk.keysyms.Delete:
            dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL,
                    gtk.MESSAGE_INFO, gtk.BUTTONS_YES_NO,
                    "Are you sure you want to delete selected words?")
            response = dialog.run()
            dialog.destroy()

            if response == gtk.RESPONSE_YES:
                sel = self.get_selection()
                model, pathlist = sel.get_selected_rows()
                for path in pathlist:
                    self._delete_row(model.get_iter(path))
                self._delete_commit()
            
    def _on_cell_edited(self, cell, path, new_text, col_id):
        it = self.model.get_iter(path)
        self.model[it][col_id] = new_text
        self._update_row(it)

    def _update_row(self, it):
        row = self.model[it]
        if row[0] == -1:
            # insert to db
            ins = self.tb_vocab.insert()
            new = ins.values(simplified=unicode(row[1]),
                             traditional=unicode(row[2]), 
                             reading=unicode(row[3]), 
                             translation=unicode(row[4]), 
                             lesson=self.lesson)
            res = self.db.execute(new)
            newid = res.last_inserted_ids()[0]
            self.model[it][0] = newid
            # add a new empty row
            self.model.append([-1, '', '', '', '', self.lesson])
        else:
            # update db record
            update = self.tb_vocab.update().where(
                    self.tb_vocab.c.id==row[0])
            update_v = update.values(simplified=unicode(row[1]), 
                                     traditional=unicode(row[2]),
                                     reading=unicode(row[3]), 
                                     translation=unicode(row[4]),
                                     lesson=self.lesson)
            self.db.execute(update_v)
    
    def _delete_row(self, it):
        if self.model[it][0] == -1:
            return
        i = self.model[it][0]
        self.db.execute(self.tb_vocab.delete().where(self.tb_vocab.c.id == i))
        self.model[it][0] = -2

    def _delete_commit(self):
        for it in self.model:
            if it[0] == -2:
                self.model.remove(it.iter)


