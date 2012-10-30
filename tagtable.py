#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import gtk

class TaipanTagTable(gtk.TextTagTable):
    def __init__(self):
        gtk.TextTagTable.__init__(self)

        # Add all text tags
        tag = gtk.TextTag("headword")
        tag.set_property('scale', 2.)
        self.add(tag)

        tag = gtk.TextTag("tone1")
        tag.set_property('foreground', '#ff0000')
        self.add(tag)

        tag = gtk.TextTag("tone2")
        tag.set_property('foreground', '#ddbb00')
        self.add(tag)

        tag = gtk.TextTag("tone3")
        tag.set_property('foreground', '#00aa00')
        self.add(tag)

        tag = gtk.TextTag("tone4")
        tag.set_property('foreground', '#3333ff')
        self.add(tag)

        tag = gtk.TextTag("tonenull")
        tag.set_property('foreground', '#888888')
        self.add(tag)

        tag = gtk.TextTag("basictrans")
        tag.set_property('scale', 1.3)
        self.add(tag)

        tag = gtk.TextTag("editor")
        tag.set_property('scale', 2.0)
        tag.set_property('family', '很高兴认识你')
        self.add(tag)
