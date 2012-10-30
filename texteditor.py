#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import gtk
import pango
import tagtable

class TexteditorWidget(gtk.TextView):
    def __init__(self):
        gtk.TextView.__init__(self)

        # setup buffer with tagtable
        tag = tagtable.TaipanTagTable()
        self.buf = gtk.TextBuffer(tag)
        self.set_buffer(self.buf)
        self.buf.connect("changed", self._on_buffer_changed)

        # various tweaking
        self.set_pixels_below_lines(20)
        font = pango.FontDescription()
        font.set_stretch(pango.STRETCH_ULTRA_EXPANDED)
        font.set_size(24 * pango.SCALE)
        self.modify_font(font)

        # test
#        self.buf.insert_with_tags_by_name(self.buf.get_start_iter(),
#                                          "很高兴认识你!", "headword")

    def _on_buffer_changed(self, buf):
        s, e = buf.get_bounds()
        #buf.apply_tag_by_name("editor", s, e)
