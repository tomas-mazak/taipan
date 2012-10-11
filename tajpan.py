#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import re
import gtk
import tegakigtk.recognizer
import cjklib.dictionary
import cjklib.reading

CJKLIB_OPTS = {'databaseUrl': 'sqlite:///data/cjklib.db'}

class TajpanGUI:
    """Handle main GUI window of Tajpan"""

    def __init__(self):
        # Init cjklib
        self.dict = cjklib.dictionary.CEDICT(**CJKLIB_OPTS)
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
        self.search = self.builder.get_object("btn_search")
        self.search.connect("clicked", self._search)
        
        #compl = self.builder.get_object("com_search")
        #self.entry.set_completion(compl)
        #ds = gtk.ListStore(str)
        #for i in self.dict.getAll():
        #    ds.append([i.HeadwordSimplified])
        #compl.set_model(ds)
        #compl.set_text_column(0)
        
        # Get result text buffer
        self.rbuf = self.builder.get_object("txt_result").get_buffer()

        # Get expander and add recognizer to it
        self.recognizer = tegakigtk.recognizer.SimpleRecognizerWidget()
        self.recognizer.connect("commit-string", self._addchar)
        self.exp_recognizer = self.builder.get_object("exp_recognize")
        self.exp_recognizer.add(self.recognizer)

    def _addchar(self, widget, char):
        self.entry.set_text(self.entry.get_text() + char)
        self.recognizer.clear_all()

    def _search_keypress(self, widget, event):
        if(event.keyval == gtk.keysyms.Return):
            self._search(widget)
        else:
            return False

    def _search(self, widget):
        # tags
        tag_hword = self.rbuf.create_tag(scale=2.)
        tag_tone1 = self.rbuf.create_tag(foreground='#ff0000')
        tag_tone2 = self.rbuf.create_tag(foreground='#ddbb00')
        tag_tone3 = self.rbuf.create_tag(foreground='#00aa00')
        tag_tone4 = self.rbuf.create_tag(foreground='#3333ff')
        tag_tonenull = self.rbuf.create_tag(foreground='#888888')
        tag_basictrans = self.rbuf.create_tag(scale=1.3)

        self.rbuf.set_text('\n')

        res = self.dict.getForHeadword(unicode(self.entry.get_text()))
        for r in res:
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
        
    def start(self):
        self.window.show_all()
        gtk.main()


# If directly called, start the GUI
if __name__ == "__main__":
    gui = TajpanGUI()
    gui.start()

