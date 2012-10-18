#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import re
import itertools
import gtk
import tegakigtk.recognizer
import cjklib.dictionary
import cjklib.reading
import sorder

CJKLIB_OPTS = {'databaseUrl': 'sqlite:///data/cjklib.db'}

class DictionaryWidget:
    """Handle main GUI window of Tajpan"""

    def __init__(self):
        # Init cjklib
        self.dict = cjklib.dictionary.CEDICT(**CJKLIB_OPTS)
        self.compl_dict = cjklib.dictionary.CEDICT(
                headwordSearchStrategy=cjklib.dictionary.search.Wildcard(),
                **CJKLIB_OPTS)
        self.reading = cjklib.reading.ReadingFactory(**CJKLIB_OPTS)

        # Fire up GtkBuilder
        self.gladefile = "tajpan.glade"
        self.builder = gtk.Builder() 
        self.builder.add_from_file(self.gladefile)

        # Get the Main Window, and connect events
        self.window = self.builder.get_object("MainWindow")
        self.window.connect("destroy", gtk.main_quit)

        # Get search box/button and connect events
        self.entry = self.builder.get_object("ent_search")
        self.entry.connect("key_press_event", self._search_keypress)
        self.entry.connect("changed", self._changed)
        self.search = self.builder.get_object("btn_search")
        self.search.connect("clicked", self._search)
        
        compl = self.builder.get_object("com_search")
        self.entry.set_completion(compl)
        self.compl_model = gtk.ListStore(str, str)
        #for i in self.dict.getAll():
        #    ds.append([i.HeadwordSimplified])
        compl.set_model(self.compl_model)
        compl.set_text_column(0)
        compl.set_match_func(self._match_func)
        compl.connect("match_selected", self._compl_match_selected)

        # Get option checkboxes
        self.chk_reading = self.builder.get_object("chk_reading")
        self.chk_translation = self.builder.get_object("chk_translation")
        
        # Get result text buffer
        self.view = self.builder.get_object("txt_result")
        self.rbuf = self.view.get_buffer()
        self.view.connect("button_press_event", self._view_context_menu)

        # Get expander and add recognizer to it
        self.recognizer = tegakigtk.recognizer.SimpleRecognizerWidget()
        self.recognizer.connect("commit-string", self._addchar)
        self.exp_recognizer = self.builder.get_object("exp_recognize")
        self.exp_recognizer.add(self.recognizer)

    def _view_context_menu(self, widget, event):
        if event.button == 3:
            x,y = self.view.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT,
                                                    int(event.x), int(event.y))
            start = widget.get_iter_at_position(x, y)
            s, e = start[0], start[0].copy()
            e.forward_char()
            char = s.get_text(e)
            if not self.is_cjk(char):
                return False
            menu = gtk.Menu()
            menu_sorder = gtk.MenuItem( "Show stroke order")
            menu_sorder.connect("activate", self.show_stroke_order, char)
            menu_sorder.show()
            menu.append(menu_sorder)
            menu.popup(None, None, None, event.button, event.time)
            return True
        return False

    def is_cjk(self, character):
        if character == '':
            return False

        char = ord(character)
        #main blocks
        if char >= 0x4E00 and char <= 0x9FFF:
            return True
        #extended block A
        if char >= 0x3400 and char <= 0x4DBF:
            return True
        #extended block B
        if char >= 0x20000 and char <= 0x2A6DF:
            return True
        #extended block C
        if char >= 0x2A700 and char <= 0x2B73F:
            return True
        return False

    def show_stroke_order(self, widget, char):
        anim = sorder.StrokeOrderAnimation(char)
        anim.start()

    def _addchar(self, widget, char):
        self.entry.set_text(self.entry.get_text() + char)
        self.recognizer.clear_all()

    def _compl_match_selected(self, completion, model, iter):
        self.entry.set_text(model[iter][1])
        self._search()
        return True

    def _match_func(self, completion, key_string, item):
        return True

    def _changed(self, widget):
        # wildcard search for empty string is evil
        if len(self.entry.get_text()) == 0:
            return False

        res = self.dict.getForHeadword(unicode(self.entry.get_text())+'%')
        self.compl_model.clear()
        for r in res:
            s = r.HeadwordSimplified 
            if r.HeadwordSimplified != r.HeadwordTraditional:
                s += " (" + r.HeadwordTraditional + ")"
            s += "  [" + r.Reading + "]"
            self.compl_model.append([s, r.HeadwordSimplified])
        return False

    def _search_keypress(self, widget, event):
        if(event.keyval == gtk.keysyms.Return):
            self._search()
        return False

    def _search(self, widget=None):
        # tags
        tag_hword = self.rbuf.create_tag(scale=2.)
        tag_tone1 = self.rbuf.create_tag(foreground='#ff0000')
        tag_tone2 = self.rbuf.create_tag(foreground='#ddbb00')
        tag_tone3 = self.rbuf.create_tag(foreground='#00aa00')
        tag_tone4 = self.rbuf.create_tag(foreground='#3333ff')
        tag_tonenull = self.rbuf.create_tag(foreground='#888888')
        tag_basictrans = self.rbuf.create_tag(scale=1.3)

        # don't bother to search for empty string
        if self.entry.get_text() == '':
            return

        # search in characters (HeadWord)
        res = self.dict.getForHeadword(unicode(self.entry.get_text()))

        # search in reading (Pinyin)
        if self.chk_reading.get_active():
            res2 = self.dict.getForReading(unicode(self.entry.get_text()),
                                           reading='Pinyin',
                                           toneMarkType='numbers')
            res = itertools.chain(res, res2)

        # search in translation
        if self.chk_translation.get_active():
            res2 = self.dict.getForTranslation(unicode(self.entry.get_text()))
            res = itertools.chain(res, res2)

        self.rbuf.set_text('\n')
        num_results = 0
        for r in res:
            num_results += 1
            # Chinese
            self.rbuf.insert_with_tags(self.rbuf.get_end_iter(),
                                       r.HeadwordSimplified, tag_hword)
            if r.HeadwordSimplified != r.HeadwordTraditional:
                s = " (" + r.HeadwordTraditional + ")"
                self.rbuf.insert_with_tags(self.rbuf.get_end_iter(), 
                                           s, tag_hword)

            # Reading
            self.rbuf.insert(self.rbuf.get_end_iter(), "\n[ ")
            decomp = self.reading.decompose(r.Reading, 'Pinyin')
            for ent in decomp:
                if self.reading.isReadingEntity(ent, 'Pinyin'):
                    foo,tone = self.reading.splitEntityTone(ent, 'Pinyin')
                    if tone == 1:
                        self.rbuf.insert_with_tags(self.rbuf.get_end_iter(), 
                                                   ent, tag_tone1)
                    elif tone == 2:
                        self.rbuf.insert_with_tags(self.rbuf.get_end_iter(), 
                                                   ent, tag_tone2)
                    elif tone == 3:
                        self.rbuf.insert_with_tags(self.rbuf.get_end_iter(), 
                                                   ent, tag_tone3)
                    elif tone == 4:
                        self.rbuf.insert_with_tags(self.rbuf.get_end_iter(), 
                                                   ent, tag_tone4)
                    else:
                        self.rbuf.insert_with_tags(self.rbuf.get_end_iter(), 
                                                   ent, tag_tonenull)
                else:
                    self.rbuf.insert(self.rbuf.get_end_iter(), ent)
            self.rbuf.insert(self.rbuf.get_end_iter(), " ]\n\n")
            
            # Translation
            st = r.Translation
            for match in re.finditer('\[(.*)\]', st):
                s = match.start(1)
                e = match.end(1)
                rd = self.reading.convert(match.group(1), self.dict.READING,
                            self.dict.READING, 
                            sourceOptions=self.dict.READING_OPTIONS)
                st = st[:s] + rd + st[e:]

            s = st[1:-1].split('/')
            self.rbuf.insert_with_tags(self.rbuf.get_end_iter(), s[0] + "\n",
                                       tag_basictrans)
            for i in range(1, min(len(s), 11)):
                m = "  " + unichr(12928+i-1) + " " + s[i] + "\n"
                self.rbuf.insert(self.rbuf.get_end_iter(), m)

            for i in range(11, len(s)):
                m = "  (" + str(i) + ") " + s[i] + "\n"
                self.rbuf.insert(self.rbuf.get_end_iter(), m)
                                           
            self.rbuf.insert(self.rbuf.get_end_iter(), "\n\n")

        if num_results == 0:
            self.rbuf.set_text("\nExpression '" 
                               + unicode(self.entry.get_text())
                               + "' was not found in the dictionary!")
        
    def start(self):
        self.window.show_all()
        
        gtk.gdk.threads_init()
        gtk.gdk.threads_enter() 
        gtk.main()
        gtk.gdk.threads_leave()


# If directly called, start the GUI
if __name__ == "__main__":
    gui = DictionaryWidget()
    gui.start()

