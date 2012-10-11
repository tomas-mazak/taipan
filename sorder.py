#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import pygtk
pygtk.require('2.0')

import re
import sqlalchemy
import gtk
import gobject
import cairo
import time

CANVAS_SIZE = (300, 300)

class Stroke:
    pass

class StrokeOrderAnimation:
    """Display window with stroke order animation of given character"""

    def __init__(self, char):
        self.char = char

        # Fire up GtkBuilder
        self.gladefile = "tajpan.glade"
        self.builder = gtk.Builder()
        self.builder.add_from_file(self.gladefile)

        # Setup window
        self.window = self.builder.get_object("StrokeOrderWindow")
        self.window.connect("destroy", gtk.main_quit)

    def _parse_stroke(self, string):
        stroke = Stroke()

        match = re.search('([1-8])([PN])([RO]):', string)
        if match == None:
            return
        stroke.direction = int(match.group(1))
        stroke.pause = (match.group(2) == 'P') 
        stroke.radical = (match.group(3) == 'R') 

        stroke.points = []
        for match in re.finditer('([0-9]+),([0-9]+)', string):
            stroke.points.append((int(match.group(1)),int(match.group(2))))

        stroke.xmin = min(stroke.points, key=lambda x: x[0])[0]
        stroke.xmax = max(stroke.points, key=lambda x: x[0])[0]
        stroke.ymin = min(stroke.points, key=lambda x: x[1])[1]
        stroke.ymax = max(stroke.points, key=lambda x: x[1])[1]

        stroke.drawn = False

        self.strokes.append(stroke)

    def _parse_chr(self, string):
        self.strokes = []
        for i in string.split("#"):
            self._parse_stroke(i)

    def draw(self):
        style = self.canvas.get_style()
        gc = style.fg_gc[gtk.STATE_NORMAL]
        d = self.canvas.window
        for stroke in self.strokes:
            d.draw_polygon(gc, True, stroke.points)
        
    def start(self):
        # load data
        db = sqlalchemy.create_engine('sqlite:///data/stroke.db')
        tb = sqlalchemy.Table('strokeorder', sqlalchemy.MetaData(db), 
                              autoload=True)
        r = tb.select(tb.c.chr == self.char).execute().fetchone()
        self._parse_chr(r.data)

        # Add my StrokeOrderWidget
        self.sow = StrokeOrderWidget(self.strokes)
        self.window.add(self.sow)

        # start up
        self.window.show_all()
        gtk.main()


class StrokeOrderWidget(gtk.DrawingArea):
    def __init__(self, strokes):
        gtk.DrawingArea.__init__(self)
        self.set_size_request(CANVAS_SIZE[0], CANVAS_SIZE[1])
        self.connect("expose_event", self.expose)
        self.strokes = strokes
        self.curstroke = 0
        self.curpos = 0
        self.animated = False

    def expose(self, widget, event):
        self.cr = widget.window.cairo_create()
        if not self.animated:
            gobject.timeout_add(10, self.redraw)
            self.animated = True
            self.draw()
        self.draw()
        self.animate()
        return False

    def redraw(self):
        if self.curstroke >= len(self.strokes):
            return False
        self.queue_draw()
        return True

    def drawstroke(self, stroke, template = False):
        if template and not stroke.drawn:
            tone = 0.7
        else:
            tone = 0

        if stroke.radical:
            self.cr.set_source_rgb(1, tone, tone)
        else:
            self.cr.set_source_rgb(tone, tone, tone)

        self.cr.move_to(stroke.points[-1][0], stroke.points[-1][1])
        for p in stroke.points:
            self.cr.line_to(p[0], p[1])
        self.cr.fill()

    def draw(self):
        """Draw whole character in gray (as template)"""
        for i in range(len(self.strokes)-1, -1, -1):
            self.cr.set_source_rgb(0.7, 0.7, 0.7)
            self.drawstroke(self.strokes[i], True)

    def animate(self):
        """Draw one iteration"""
        stroke = self.strokes[self.curstroke]
        self.curpos += 1

        if stroke.direction == 1:
            self.cr.rectangle(0, 0, stroke.xmin + self.curpos, CANVAS_SIZE[1])
            self.cr.clip()
            self.cr.new_path()
            self.cr.set_source_rgb(0,0,0)
            self.drawstroke(stroke)
            if stroke.xmin + self.curpos >= stroke.xmax:
                if self.strokes[self.curstroke].pause:
                    time.sleep(0.5)
                self.strokes[self.curstroke].drawn = True
                self.curstroke += 1
                self.curpos = 0
        elif stroke.direction in (2,3,4):
            self.cr.rectangle(0, 0, CANVAS_SIZE[1], stroke.ymin + self.curpos)
            self.cr.clip()
            self.cr.new_path()
            self.cr.set_source_rgb(0,0,0)
            self.drawstroke(stroke)
            if stroke.ymin + self.curpos >= stroke.ymax:
                if self.strokes[self.curstroke].pause:
                    time.sleep(0.5)
                self.strokes[self.curstroke].drawn = True
                self.curstroke += 1
                self.curpos = 0
        elif stroke.direction == 5:
            self.cr.rectangle(stroke.xmax -self.curpos, 0, CANVAS_SIZE[0], 
                              CANVAS_SIZE[1])
            self.cr.clip()
            self.cr.new_path()
            self.cr.set_source_rgb(0,0,0)
            self.drawstroke(stroke)
            if stroke.xmax - self.curpos <= stroke.xmin:
                if self.strokes[self.curstroke].pause:
                    time.sleep(0.5)
                self.strokes[self.curstroke].drawn = True
                self.curstroke += 1
                self.curpos = 0
        else:
            self.cr.rectangle(0, stroke.ymax -self.curpos, CANVAS_SIZE[0], 
                              CANVAS_SIZE[1])
            self.cr.clip()
            self.cr.new_path()
            self.cr.set_source_rgb(0,0,0)
            self.drawstroke(stroke)
            if stroke.ymax - self.curpos <= stroke.ymin:
                if self.strokes[self.curstroke].pause:
                    time.sleep(0.5)
                self.strokes[self.curstroke].drawn = True
                self.curstroke += 1
                self.curpos = 0

        return True


# If directly called, start the GUI
if __name__ == "__main__":
    gui = StrokeOrderAnimation(unicode('涛'))
    gui.start()

