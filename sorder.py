#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import re
import sqlalchemy
import gtk
import cairo
import time
import threading

STROKE_DB = 'sqlite:///data/stroke.db'
CANVAS_SIZE = (300, 300)
ANIMATION_SPEED = 0.005 # pause between iterations in seconds
PAUSE_BETWEEN_STROKES = 0.5 # pause between strokes in seconds

class Stroke:
    """Container of stroke attributes
    
       direction  int(1-8)
       Stroke direction encoded as number.

       pause  boolean   
       Should there be a short pause after the stroke animation? (used for 
       building complex strokes from primitives)

       radical  boolean   
       Is this stroke a part of the radical?

       points  List of tuples (x,y), 0 <= x,y <= 300
       Corners of polygon representing the stroke

       xmin  int
       Leftmost point of the stroke

       xmax  int
       Rightmost point of the stroke

       ymin  int
       Uppermost point of the stroke
       
       ymax  int
       Lowest point of the stroke
    """
    # Stroke direction constants
    LEFT_TO_RIGHT = 1
    DOWN_RIGHT =    2
    DOWN =          3
    DOWN_LEFT =     4
    RIGHT_TO_LEFT = 5
    UP_LEFT =       6
    UP =            7
    UP_RIGHT =      8


class StrokeOrderAnimation:
    """Stroke order animation launcher"""

    def __init__(self, char):
        """Init instance attributes"""
        self.char = char

        # load data
        db = sqlalchemy.create_engine(STROKE_DB)
        tb = sqlalchemy.Table('strokeorder', sqlalchemy.MetaData(db), 
                              autoload=True)
        r = tb.select(tb.c.chr == self.char).execute().fetchone()
        self._parse_chr(r.data)

        # Setup window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("destroy", lambda w: self.stop())
        self.window.set_border_width(10)
        self.window.set_title("Stroke order of " + self.char)

        # Add my StrokeOrderWidget
        self.sow = StrokeOrderWidget(self.strokes)
        self.window.add(self.sow)

        # show window content
        self.window.show_all()

        # Setup the animation thread
        self.stop_event = threading.Event()
        self.anim_thread = threading.Thread(target=self._animate,
                                            args=(self.stop_event,))

    def start(self):
        """Start the animation"""
        self.anim_thread.start() 

    def stop(self):
        """Stop the animation"""
        self.stop_event.set()

    def _animate(self, stop_event):
        """Timer callback for animation iteration. Animation will continue
           until False is returned here"""
        while not stop_event.is_set():
            if self.sow.is_pause():
                stop_event.wait(PAUSE_BETWEEN_STROKES)
            stop_event.wait(ANIMATION_SPEED)
            # Ask gtk to redraw the widget
            self.sow.queue_draw()

    def _parse_chr(self, string):
        """Parse the stroke data of the entire character"""
        self.strokes = []
        for i in string.split("#"):
            self._parse_stroke(i)

    def _parse_stroke(self, string):
        """Parse stroke data of a single stroke"""
        stroke = Stroke()

        # Parse attributes
        match = re.search('([1-8])([PN])([RO]):', string)
        if match == None:
            return
        stroke.direction = int(match.group(1))
        stroke.pause = (match.group(2) == 'P') 
        stroke.radical = (match.group(3) == 'R') 
        stroke.drawn = False

        # Parse corners
        stroke.points = []
        for match in re.finditer('([0-9]+),([0-9]+)', string):
            stroke.points.append((int(match.group(1)),int(match.group(2))))

        # Find bounding rectangle
        stroke.xmin = min(stroke.points, key=lambda x: x[0])[0]
        stroke.xmax = max(stroke.points, key=lambda x: x[0])[0]
        stroke.ymin = min(stroke.points, key=lambda x: x[1])[1]
        stroke.ymax = max(stroke.points, key=lambda x: x[1])[1]
        
        # Add to the list
        self.strokes.append(stroke)


class StrokeOrderWidget(gtk.DrawingArea):
    """Gtk widget displaying a stroke order animation
    
    strokes  list of Stroke objects
    List of strokes to be shown

    curstroke  int(index to strokes list)
    Currently animated stroke

    curpos  int
    Iteration of single stroke animation
    """

    def __init__(self, strokes):
        """Init the widget and setup the attributes"""
        gtk.DrawingArea.__init__(self)
        self.set_size_request(CANVAS_SIZE[0], CANVAS_SIZE[1])
        self.connect("expose_event", self._expose)

        self.strokes = strokes
        self.curstroke = 0
        self.curpos = 0
        self.pause = True

    def is_pause(self):
        """Return and clear the pause flag"""
        ret = self.pause
        self.pause = False
        return ret

    def _expose(self, widget, event):
        """Draw the next state iteration when GTK asks for redrawing"""
        self.cr = widget.window.cairo_create()
        self._draw_template()
        self._next_iteration()
        return False

    def _draw_stroke(self, stroke, template = False):
        """Draw a single stroke using appropriate color"""
        # Template is drawn in light tones, drawn strokes in rich colors
        if template and not stroke.drawn:
            tone = 0.7
        else:
            tone = 0

        # Radical strokes are drawn in red, others are drawn in black
        if stroke.radical:
            self.cr.set_source_rgb(1, tone, tone)
        else:
            self.cr.set_source_rgb(tone, tone, tone)

        # Draw the filled polygon
        self.cr.move_to(stroke.points[-1][0], stroke.points[-1][1])
        for p in stroke.points:
            self.cr.line_to(p[0], p[1])
        self.cr.fill()

    def _draw_template(self):
        """Draw whole character template"""
        for stroke in reversed(self.strokes):
            self._draw_stroke(stroke, True)

    def _next_iteration(self):
        """Draw a single iteration of the animation"""
        # If the end of the animation was reached, restart it 
        if self.curstroke >= len(self.strokes):
            self.curpos = 0
            self.curstroke = 0
            for s in self.strokes:
                s.drawn = False

        # Move forward
        stroke = self.strokes[self.curstroke]
        self.curpos += 1

        # Prepare clipping mask according to stroke direction
        if stroke.direction == Stroke.LEFT_TO_RIGHT:
            x, y, w, h = 0, 0, stroke.xmin + self.curpos, CANVAS_SIZE[1]
            condition = stroke.xmin + self.curpos
            limit = stroke.xmax
        elif stroke.direction in (Stroke.DOWN_RIGHT, Stroke.DOWN,
                                  Stroke.DOWN_LEFT):
            x, y, w, h = 0, 0, CANVAS_SIZE[1], stroke.ymin + self.curpos
            condition = stroke.ymin + self.curpos
            limit = stroke.ymax
        elif stroke.direction == Stroke.RIGHT_TO_LEFT:
            x, y = stroke.xmax - self.curpos, 0
            w, h = CANVAS_SIZE[0], CANVAS_SIZE[1]
            condition = stroke.xmin
            limit = stroke.xmax - self.curpos
        elif stroke.direction in (Stroke.UP_LEFT, Stroke.UP, Stroke.UP_RIGHT):
            x, y = 0, stroke.ymax - self.curpos
            w, h = CANVAS_SIZE[0], CANVAS_SIZE[1]
            condition = stroke.ymin
            limit = stroke.ymax - self.curpos

        # Apply clipping mask
        self.cr.rectangle(x, y, w, h)
        self.cr.clip()
        self.cr.new_path()
        self._draw_stroke(stroke)

        # If limit was reached, move to the next stroke
        if condition >= limit:
            if self.strokes[self.curstroke].pause:
                self.pause = True
            self.strokes[self.curstroke].drawn = True
            self.curstroke += 1
            self.curpos = 0

        return True


# If directly called, start the GUI
if __name__ == "__main__":
    gui = StrokeOrderAnimation(unicode('我'))
    gui.window.connect("destroy", gtk.main_quit)
    gui.start()
    gtk.gdk.threads_init()
    gtk.gdk.threads_enter()
    gtk.main()
    gtk.gdk.threads_leave()
