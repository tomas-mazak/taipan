#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import re
import itertools
import gtk
import tegakigtk.recognizer
import cjklib.dictionary
import cjklib.reading
import cjklib.characterlookup
import sorder

CJKLIB_OPTS = {'databaseUrl': 'sqlite:///data/cjklib.db'}
GLADE_FILE = "taipan.glade"

class Tag:
    """Container of formatting tags"""
    pass

class DictionaryWidget(gtk.Frame):
    """Custom widget encapsulating dictionary functions including handwriting
       recognition"""

    def __init__(self):
        """Init the widget components and required modules from cjklib"""
        gtk.Frame.__init__(self)

        # Init cjklib
        cjklib.dictionary.search.setDefaultWildcards(singleCharacter='?',
                                                     multipleCharacters='*')
        self.cjk = cjklib.characterlookup.CharacterLookup('T', **CJKLIB_OPTS)
        self.dict = cjklib.dictionary.CEDICT(**CJKLIB_OPTS)
        self.reading = cjklib.reading.ReadingFactory(**CJKLIB_OPTS)

        # Fire up GtkBuilder
        builder = gtk.Builder() 
        builder.add_from_file(GLADE_FILE)

        # Get dictionary layout from GtkBuilder and add it to this widget
        gladewin = builder.get_object("DictionaryWidget")
        layout = builder.get_object("DictionaryWidgetLayout")
        gladewin.remove(layout)
        self.add(layout)

        # Get search box and connect events
        self.entry = builder.get_object("ent_search")
        self.entry.connect("key_press_event", self._on_entry_keypress)
        self.entry.connect("changed", self._on_entry_changed)

        # Setup popup completition for search box
        compl = gtk.EntryCompletion()
        compl.set_popup_set_width(False)
        self.entry.set_completion(compl)
        # ListStore will contain nice string for displaying in popup and
        # simplified characters to put into searchbox
        self.compl_model = gtk.ListStore(str, str)
        compl.set_model(self.compl_model)
        compl.set_text_column(0)
        # Match function just accepts all items from the list, as we are doing
        # filtering stuff elsewhere
        compl.set_match_func(lambda c,k,r: True)
        compl.connect("match_selected", self._on_compl_match_selected)

        # Get search button and connect events
        search = builder.get_object("btn_search")
        search.connect("clicked", self._on_search_clicked)

        # Get option checkboxes
        self.chk_reading = builder.get_object("chk_reading")
        self.chk_translation = builder.get_object("chk_translation")
        
        # Get result text buffer
        result = builder.get_object("txt_result")
        self.rbuf = result.get_buffer()
        result.connect("button_press_event", self._on_result_click)
        result.connect("populate_popup", self._on_result_popup)

        # Setup result text buffer formatting tags
        tag = Tag()
        tag.hword = self.rbuf.create_tag(scale=2.)
        tag.tone1 = self.rbuf.create_tag(foreground='#ff0000')
        tag.tone2 = self.rbuf.create_tag(foreground='#ddbb00')
        tag.tone3 = self.rbuf.create_tag(foreground='#00aa00')
        tag.tone4 = self.rbuf.create_tag(foreground='#3333ff')
        tag.tonenull = self.rbuf.create_tag(foreground='#888888')
        tag.basictrans = self.rbuf.create_tag(scale=1.3)
        self.tag = tag

        # Get expander and add recognizer to it
        self.recognizer = tegakigtk.recognizer.SimpleRecognizerWidget()
        self.recognizer.connect("commit-string", self._on_recognizer_commit)
        self.exp_recognizer = builder.get_object("exp_recognize")
        self.exp_recognizer.add(self.recognizer)

    def search(self, what=None):
        """Do the dictionary search and display the nicely formatted result"""
        # If the text was provided as an argument, update the searchbox
        if what != None:
            self.entry.set_text(what)

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

        # Display the result
        tag = self.tag
        self.rbuf.set_text('\n')
        num_results = 0
        for r in res:
            num_results += 1
            # Chinese
            self.rbuf.insert_with_tags(self.rbuf.get_end_iter(),
                                       r.HeadwordSimplified, tag.hword)
            if r.HeadwordSimplified != r.HeadwordTraditional:
                s = " (" + r.HeadwordTraditional + ")"
                self.rbuf.insert_with_tags(self.rbuf.get_end_iter(), 
                                           s, tag.hword)
            
            # Reading
            self.rbuf.insert(self.rbuf.get_end_iter(), "\n[ ")
            self._add_formatted_reading(r.Reading)
            self.rbuf.insert(self.rbuf.get_end_iter(), " ]\n\n")

            # Translation
            s = r.Translation[1:-1].split('/')
            basictrans = s[0] + "\n"
            extended = ""
            for i in range(1, min(len(s), 11)):
                m = "  " + unichr(12928+i-1) + " " + s[i] + "\n"
                extended += m
            for i in range(11, len(s)):
                m = "  (" + str(i) + ") " + s[i] + "\n"
                extended += m

            self._add_text_with_readings(basictrans, [tag.basictrans])
            self._add_text_with_readings(extended)
            self.rbuf.insert(self.rbuf.get_end_iter(), "\n\n")

        # Display an error message if the given expression was not found
        if num_results == 0:
            self.rbuf.set_text("\nExpression '" 
                               + unicode(self.entry.get_text())
                               + "' was not found in the dictionary!")

    def _add_text_with_readings(self, text, tags=[]):
        """Find readings in the text and format them properly"""
        tag = self.tag
        # add reading blocks and plaintext before them
        last = 0
        for match in re.finditer('\[(.*)\]', text):
            s = match.start(1)
            e = match.end(1)
            rd = self.reading.convert(match.group(1), self.dict.READING,
                        self.dict.READING, 
                        sourceOptions=self.dict.READING_OPTIONS)

            self.rbuf.insert_with_tags(self.rbuf.get_end_iter(), text[last:s],
                                       *tags)
            self._add_formatted_reading(rd, tags)
            last = e

        # append final part
        self.rbuf.insert_with_tags(self.rbuf.get_end_iter(), text[last:], 
                                   *tags)

    def _add_formatted_reading(self, reading, tags=[]):
        """Split reading string to syllables and add them with proper
           style according to tone"""
        tag = self.tag
        decomp = self.reading.decompose(reading, 'Pinyin')
        for ent in decomp:
            if self.reading.isReadingEntity(ent, 'Pinyin'):
                foo,tone = self.reading.splitEntityTone(ent, 'Pinyin')
                if tone == 1:
                    self.rbuf.insert_with_tags(self.rbuf.get_end_iter(), 
                                               ent, tag.tone1, *tags)
                elif tone == 2:
                    self.rbuf.insert_with_tags(self.rbuf.get_end_iter(), 
                                               ent, tag.tone2, *tags)
                elif tone == 3:
                    self.rbuf.insert_with_tags(self.rbuf.get_end_iter(), 
                                               ent, tag.tone3, *tags)
                elif tone == 4:
                    self.rbuf.insert_with_tags(self.rbuf.get_end_iter(), 
                                               ent, tag.tone4, *tags)
                else:
                    self.rbuf.insert_with_tags(self.rbuf.get_end_iter(), 
                                               ent, tag.tonenull, *tags)
            else:
                self.rbuf.insert_with_tags(self.rbuf.get_end_iter(), ent,
                                           *tags)

    def _on_entry_keypress(self, widget, event):
        """Do dictionary search when RETURN was pressed inside the search box
        """
        if(event.keyval == gtk.keysyms.Return):
            self.search()
        return False

    def _on_entry_changed(self, widget):
        """Update popup completition whenever searchbox contents is changed"""
        # Wildcard search for empty string is evil
        if len(self.entry.get_text()) == 0:
            return False

        # Get matching items from dictionary and update the model
        res = self.dict.getForHeadword(unicode(self.entry.get_text())+'*')
        self.compl_model.clear()
        for r in res:
            s = r.HeadwordSimplified 
            if r.HeadwordSimplified != r.HeadwordTraditional:
                s += " (" + r.HeadwordTraditional + ")"
            s += "  [" + r.Reading + "]"
            self.compl_model.append([s, r.HeadwordSimplified])
        return False

    def _on_compl_match_selected(self, completion, model, row):
        """When an item from popup completition was selected, update
           the search box with appropriate value"""
        self.entry.set_text(model[row][1])
        self.search()
        return True

    def _on_search_clicked(self, widget):
        """Do dictionary search when Search button was clicked"""
        self.search()

    def _on_result_click(self, widget, event):
        """If a CJK character was under the mouse pointer in the moment 
           of right-click, save the character for popup menu purposes"""
        self.sorder_to_popup = None

        # Right-click check
        if event.button != 3:
            return False

        # Get the character under the mouse pointer
        x,y = widget.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT,
                                             int(event.x), int(event.y))
        start = widget.get_iter_at_position(x, y)
        s, e = start[0], start[0].copy()
        e.forward_char()
        char = s.get_text(e)

        # If the character is not an CJK character, don't do anything
        if not self.cjk.isCharacterInDomain(char):
            return False

        self.sorder_to_popup = char 
        return False

    def _on_result_popup(self, widget, menu):
        """If a CJK character was targeted, add 'Show stroke order' item to
           the popup menu"""
        if self.sorder_to_popup != None:
            menu_sorder = gtk.MenuItem( "Show stroke order")
            menu_sorder.connect("activate", self._on_sorder_activate,
                                self.sorder_to_popup)
            menu_sorder.show()
            menu.prepend(menu_sorder)
        return False

    def _on_sorder_activate(self, widget, char):
        """Display stroke order animation window when "Show stroke order"
           context menu item was activated"""
        anim = sorder.StrokeOrderAnimation(char)
        anim.start()

    def _on_recognizer_commit(self, widget, char):
        """When a character from the recognizer was selected, add it to the
        searchbox"""
        self.entry.set_text(self.entry.get_text() + char)
        self.recognizer.clear_all()


# If directly called, start the GUI
if __name__ == "__main__":
    window = gtk.Window()
    dictionary = DictionaryWidget()
    
    window.add(dictionary)
    window.connect("destroy", gtk.main_quit)
    window.set_size_request(350,700)
    window.set_title("Tajpan dictionary")
    window.show_all()
    
    gtk.gdk.threads_init()
    gtk.gdk.threads_enter() 
    gtk.main()
    gtk.gdk.threads_leave()
