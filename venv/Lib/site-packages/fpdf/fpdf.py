#!/usr/bin/env python
# -*- coding: latin-1 -*-
# ****************************************************************************
# * Software: FPDF for python                                                *
# * Version:  1.7.10                                                         *
# * Date:     2010-09-10                                                     *
# * Last update: 2017-08-16                                                  *
# * License:  LGPL v3.0                                                      *
# *                                                                          *
# * Original Author (PHP):  Olivier PLATHEY 2004-12-31                       *
# * Ported to Python 2.4 by Max (maxpat78@yahoo.it) on 2006-05               *
# * Maintainer:  Mariano Reingart (reingart@gmail.com) et al since 2008 est. *
# * NOTE: 'I' and 'D' destinations are disabled, and simply print to STDOUT  *
# ****************************************************************************

from __future__ import division, with_statement

from datetime import datetime
from functools import wraps
import math
import errno
import os, sys, zlib, struct, re, tempfile, struct

from .ttfonts import TTFontFile
from .fonts import fpdf_charwidths
from .php import substr, sprintf, print_r, StrToUTF16BE, StringToArray
from .py3k import PY3K, pickle, urlopen, BytesIO, Image, basestring, unicode, exception, b, hashpath

# Global variables
FPDF_VERSION = '1.7.10'
FPDF_FONT_DIR = os.path.join(os.path.dirname(__file__),'font')
FPDF_CACHE_MODE = 0 # 0 - in same folder, 1 - none, 2 - hash
FPDF_CACHE_DIR = None
SYSTEM_TTFONTS = None

PAGE_FORMATS = {
    "a3": (841.89, 1190.55),
    "a4": (595.28, 841.89),
    "a5": (420.94, 595.28),
    "letter": (612, 792),
    "legal": (612, 1008),
}

def set_global(var, val):
    globals()[var] = val

def load_cache(filename):
    """Return unpickled object, or None if cache unavailable"""
    if not filename:
        return None
    try:
        with open(filename, "rb") as fh:
            return pickle.load(fh)
    except (IOError, ValueError):  # File missing, unsupported pickle, etc
        return None

class FPDF(object):
    "PDF Generation class"

    def __init__(self, orientation = 'P', unit = 'mm', format = 'A4'):
        # Some checks
        self._dochecks()
        # Initialization of properties
        self.offsets = {}               # array of object offsets
        self.page = 0                   # current page number
        self.n = 2                      # current object number
        self.buffer = bytearray()         # buffer holding in-memory PDF
        self.pages = {}                 # array containing pages and metadata
        self.state = 0                  # current document state
        self.fonts = {}                 # array of used fonts
        self.font_files = {}            # array of font files
        self.diffs = {}                 # array of encoding differences
        self.images = {}                # array of used images
        self.page_links = {}            # array of links in pages
        self.links = {}                 # array of internal links
        self.in_footer = 0              # flag set when processing footer
        self.lastw = 0
        self.lasth = 0                  # height of last cell printed
        self.font_family = ''           # current font family
        self.font_style = ''            # current font style
        self.font_size_pt = 12          # current font size in points
        self.font_stretching = 100      # current font stretching
        self.underline = 0              # underlining flag
        self.draw_color = '0 G'
        self.fill_color = '0 g'
        self.text_color = '0 g'
        self.color_flag = 0             # indicates whether fill and text colors are different
        self.ws = 0                     # word spacing
        self.angle = 0
        # Standard fonts
        self.core_fonts={'courier': 'Courier', 'courierB': 'Courier-Bold',
            'courierI': 'Courier-Oblique', 'courierBI': 'Courier-BoldOblique',
            'helvetica': 'Helvetica', 'helveticaB': 'Helvetica-Bold',
            'helveticaI': 'Helvetica-Oblique',
            'helveticaBI': 'Helvetica-BoldOblique',
            'times': 'Times-Roman', 'timesB': 'Times-Bold',
            'timesI': 'Times-Italic', 'timesBI': 'Times-BoldItalic',
            'symbol': 'Symbol', 'zapfdingbats': 'ZapfDingbats'}
        self.core_fonts_encoding = "latin-1"
        self.encode_error_handling = "strict"
        # Scale factor
        if unit == "pt":
            self.k = 1
        elif unit == "mm":
            self.k = 72 / 25.4
        elif unit == "cm":
            self.k = 72 / 2.54
        elif unit == 'in':
            self.k = 72.
        else:
            self.error("Incorrect unit: " + unit)
        # Page format
        self.fw_pt, self.fh_pt = self.get_page_format(format, self.k)
        self.dw_pt = self.fw_pt
        self.dh_pt = self.fh_pt
        self.fw = self.fw_pt / self.k
        self.fh = self.fh_pt / self.k
        # Page orientation
        orientation = orientation.lower()
        if orientation in ('p', 'portrait'):
            self.def_orientation = 'P'
            self.w_pt = self.fw_pt
            self.h_pt = self.fh_pt
        elif orientation in ('l', 'landscape'):
            self.def_orientation = 'L'
            self.w_pt = self.fh_pt
            self.h_pt = self.fw_pt
        else:
            self.error('Incorrect orientation: ' + orientation)
        self.cur_orientation = self.def_orientation
        self.w = self.w_pt / self.k
        self.h = self.h_pt / self.k
        # Page margins (1 cm)
        margin = 28.35 / self.k
        self.set_margins(margin, margin)
        # Interior cell margin (1 mm)
        self.c_margin = margin / 10.0
        # line width (0.2 mm)
        self.line_width = .567 / self.k
        # Automatic page break
        self.set_auto_page_break(1, 2 * margin)
        # Full width display mode
        self.set_display_mode('fullwidth')
        # Enable compression
        self.set_compression(1)
        # Set default PDF version number
        self.pdf_version = '1.3'

    @staticmethod
    def get_page_format(format, k):
        "Return scale factor, page w and h size in points"
        if isinstance(format, basestring):
            format = format.lower()
            if format in PAGE_FORMATS:
                return PAGE_FORMATS[format]
            else:
                raise RuntimeError("Unknown page format: " + format)
        else:
            return (format[0] * k, format[1] * k)

    def check_page(fn):
        "Decorator to protect drawing methods"
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            if not self.page and not kwargs.get('split_only'):
                self.error("No page open, you need to call add_page() first")
            else:
                return fn(self, *args, **kwargs)
        return wrapper

    def set_margins(self, left,top,right=-1):
        "Set left, top and right margins"
        self.l_margin=left
        self.t_margin=top
        if(right==-1):
            right=left
        self.r_margin=right

    def set_left_margin(self, margin):
        "Set left margin"
        self.l_margin=margin
        if(self.page>0 and self.x<margin):
            self.x=margin

    def set_top_margin(self, margin):
        "Set top margin"
        self.t_margin=margin

    def set_right_margin(self, margin):
        "Set right margin"
        self.r_margin=margin

    def set_auto_page_break(self, auto,margin=0):
        "Set auto page break mode and triggering margin"
        self.auto_page_break=auto
        self.b_margin=margin
        self.page_break_trigger=self.h-margin

    def set_display_mode(self, zoom,layout='continuous'):
        """Set display mode in viewer

        The "zoom" argument may be 'fullpage', 'fullwidth', 'real',
        'default', or a number, interpreted as a percentage."""

        if(zoom=='fullpage' or zoom=='fullwidth' or zoom=='real' or zoom=='default' or not isinstance(zoom,basestring)):
            self.zoom_mode=zoom
        else:
            self.error('Incorrect zoom display mode: '+zoom)
        if(layout=='single' or layout=='continuous' or layout=='two' or layout=='default'):
            self.layout_mode=layout
        else:
            self.error('Incorrect layout display mode: '+layout)

    def set_compression(self, compress):
        "Set page compression"
        self.compress=compress

    def set_title(self, title):
        "Title of document"
        self.title=title

    def set_subject(self, subject):
        "Subject of document"
        self.subject=subject

    def set_author(self, author):
        "Author of document"
        self.author=author

    def set_keywords(self, keywords):
        "Keywords of document"
        self.keywords=keywords

    def set_creator(self, creator):
        "Creator of document"
        self.creator=creator

    def set_doc_option(self, opt, value):
        "Set document option"
        if opt == "core_fonts_encoding":
            self.core_fonts_encoding = value
        elif opt == "encode_error_handling":
            if value not in ('strict', 'ignore', 'replace'):
                self.error("Invalid value for \"encode_error_handling\" option")
            self.encode_error_handling = value
        else:
            self.error("Unknown document option \"%s\"" % str(opt))

    def alias_nb_pages(self, alias='{nb}'):
        "Define an alias for total number of pages"
        self.str_alias_nb_pages=alias
        return alias

    def error(self, msg):
        "Fatal error"
        raise RuntimeError('FPDF error: '+msg)

    def open(self):
        "Begin document"
        self.state=1

    def close(self):
        "Terminate document"
        if(self.state==3):
            return
        if(self.page==0):
            self.add_page()
        #Page footer
        self.in_footer=1
        self.footer()
        self.in_footer=0
        #close page
        self._endpage()
        #close document
        self._enddoc()

    def add_page(self, orientation = '', format = '', same = False):
        "Start a new page, if same page format will be same as previous"
        if(self.state==0):
            self.open()
        family=self.font_family
        if self.underline:
            style = self.font_style + 'U'
        else:
            style = self.font_style
        size=self.font_size_pt
        lw=self.line_width
        dc=self.draw_color
        fc=self.fill_color
        tc=self.text_color
        cf=self.color_flag
        stretching=self.font_stretching
        if(self.page>0):
            #Page footer
            self.in_footer=1
            self.footer()
            self.in_footer=0
            #close page
            self._endpage()
        #Start new page
        self._beginpage(orientation, format, same)
        #Set line cap style to square
        self._out(b'2 J')
        #Set line width
        self.line_width=lw
        self._out(sprintf(b'%.2f w',lw*self.k))
        #Set font
        if(family):
            self.set_font(family,style,size)
        #Set colors
        self.draw_color=dc
        if(dc!='0 G'):
            self._out(dc)
        self.fill_color=fc
        if(fc!='0 g'):
            self._out(fc)
        self.text_color=tc
        self.color_flag=cf
        #Page header
        self.header()
        #Restore line width
        if(self.line_width!=lw):
            self.line_width=lw
            self._out(sprintf(b'%.2f w',lw*self.k))
        #Restore font
        if(family):
            self.set_font(family,style,size)
        #Restore colors
        if(self.draw_color!=dc):
            self.draw_color=dc
            self._out(dc)
        if(self.fill_color!=fc):
            self.fill_color=fc
            self._out(fc)
        self.text_color=tc
        self.color_flag=cf
        #Restore stretching
        if(stretching != 100):
            self.set_stretching(stretching)

    def header(self):
        "Header to be implemented in your own inherited class"
        pass

    def footer(self):
        "Footer to be implemented in your own inherited class"
        pass

    def page_no(self):
        "Get current page number"
        return self.page

    def set_draw_color(self, r,g=-1,b=-1):
        "Set color for all stroking operations"
        if((r==0 and g==0 and b==0) or g==-1):
            self.draw_color=sprintf(b'%.3f G',r/255.0)
        else:
            self.draw_color=sprintf(b'%.3f %.3f %.3f RG',r/255.0,g/255.0,b/255.0)
        if(self.page>0):
            self._out(self.draw_color)

    def set_fill_color(self,r,g=-1,b=-1):
        "Set color for all filling operations"
        if((r==0 and g==0 and b==0) or g==-1):
            self.fill_color=sprintf(b'%.3f g',r/255.0)
        else:
            self.fill_color=sprintf(b'%.3f %.3f %.3f rg',r/255.0,g/255.0,b/255.0)
        self.color_flag=(self.fill_color!=self.text_color)
        if(self.page>0):
            self._out(self.fill_color)

    def set_text_color(self, r,g=-1,b=-1):
        "Set color for text"
        if((r==0 and g==0 and b==0) or g==-1):
            self.text_color=sprintf(b'%.3f g',r/255.0)
        else:
            self.text_color=sprintf(b'%.3f %.3f %.3f rg',r/255.0,g/255.0,b/255.0)
        self.color_flag=(self.fill_color!=self.text_color)

    def get_string_width(self, s, normalized = False):
        "Get width of a string in the current font"
        # normalized is parameter for internal use
        s = s if normalized else self.normalize_text(s)
        cw=self.current_font['cw']
        w=0
        if self.unifontsubset:
            for char in s:
                char = ord(char)
                if len(cw) > char:
                    w += cw[char] # ord(cw[2*char])<<8 + ord(cw[2*char+1])
                #elif (char>0 and char<128 and isset($cw[chr($char)])) { $w += $cw[chr($char)]; }
                elif (self.current_font['desc']['MissingWidth']) :
                    w += self.current_font['desc']['MissingWidth']
                #elif (isset($this->CurrentFont['MissingWidth'])) { $w += $this->CurrentFont['MissingWidth']; }
                else:
                    w += 500
        else:
            s = s.encode(self.core_fonts_encoding, self.encode_error_handling)
            if PY3K:
                for byte_val in s:
                    w += cw.get(chr(byte_val), 0)
            else:
                for ch in s:
                    w += cw.get(ch, 0)
        if self.font_stretching != 100:
            w = w * self.font_stretching / 100.0
        return w * self.font_size / 1000.0

    def set_line_width(self, width):
        "Set line width"
        self.line_width=width
        if(self.page>0):
            self._out(sprintf(b'%.2f w',width*self.k))

    @check_page
    def line(self, x1,y1,x2,y2):
        "Draw a line"
        self._out(sprintf(b'%.2f %.2f m %.2f %.2f l S',x1*self.k,(self.h-y1)*self.k,x2*self.k,(self.h-y2)*self.k))

    def _set_dash(self, dash_length=False, space_length=False):
        if(dash_length and space_length):
            s = sprintf(b'[%.3f %.3f] 0 d', dash_length*self.k, space_length*self.k)
        else:
            s = '[] 0 d'
        self._out(s)

    @check_page
    def dashed_line(self, x1,y1,x2,y2, dash_length=1, space_length=1):
        """Draw a dashed line. Same interface as line() except:
           - dash_length: Length of the dash
           - space_length: Length of the space between dashes"""
        self._set_dash(dash_length, space_length)
        self.line(x1, y1, x2, y2)
        self._set_dash()

    @check_page
    def rect(self, x,y,w,h,style=''):
        "Draw a rectangle"
        if(style=='F'):
            op=b'f'
        elif(style=='FD' or style=='DF'):
            op=b'B'
        else:
            op=b'S'
        self._out(sprintf(b'%.2f %.2f %.2f %.2f re %s',x*self.k,(self.h-y)*self.k,w*self.k,-h*self.k,op))

    @check_page
    def ellipse(self, x,y,w,h,style=''):
        "Draw a ellipse"
        if(style=='F'):
            op='f'
        elif(style=='FD' or style=='DF'):
            op='B'
        else:
            op='S'

        cx = x + w/2.0
        cy = y + h/2.0
        rx = w/2.0
        ry = h/2.0

        lx = 4.0/3.0*(math.sqrt(2)-1)*rx
        ly = 4.0/3.0*(math.sqrt(2)-1)*ry

        self._out(sprintf(b'%.2f %.2f m %.2f %.2f %.2f %.2f %.2f %.2f c',
            (cx+rx)*self.k, (self.h-cy)*self.k,
            (cx+rx)*self.k, (self.h-(cy-ly))*self.k,
            (cx+lx)*self.k, (self.h-(cy-ry))*self.k,
            cx*self.k, (self.h-(cy-ry))*self.k))
        self._out(sprintf(b'%.2f %.2f %.2f %.2f %.2f %.2f c',
            (cx-lx)*self.k, (self.h-(cy-ry))*self.k,
            (cx-rx)*self.k, (self.h-(cy-ly))*self.k,
            (cx-rx)*self.k, (self.h-cy)*self.k))
        self._out(sprintf(b'%.2f %.2f %.2f %.2f %.2f %.2f c',
            (cx-rx)*self.k, (self.h-(cy+ly))*self.k,
            (cx-lx)*self.k, (self.h-(cy+ry))*self.k,
            cx*self.k, (self.h-(cy+ry))*self.k))
        self._out(sprintf(b'%.2f %.2f %.2f %.2f %.2f %.2f c %s',
            (cx+lx)*self.k, (self.h-(cy+ry))*self.k,
            (cx+rx)*self.k, (self.h-(cy+ly))*self.k,
            (cx+rx)*self.k, (self.h-cy)*self.k,
            op))

    def add_font(self, family, style='', fname='', uni=False):
        "Add a TrueType or Type1 font"
        family = family.lower()
        if (fname == ''):
            fname = family.replace(' ','') + style.lower() + '.pkl'
        if (family == 'arial'):
            family = 'helvetica'
        style = style.upper()
        if (style == 'IB'):
            style = 'BI'
        fontkey = family+style
        if fontkey in self.fonts:
            # Font already added!
            return
        if (uni):
            global SYSTEM_TTFONTS, FPDF_CACHE_MODE, FPDF_CACHE_DIR
            if os.path.exists(fname):
                ttffilename = fname
            elif (FPDF_FONT_DIR and
                os.path.exists(os.path.join(FPDF_FONT_DIR, fname))):
                ttffilename = os.path.join(FPDF_FONT_DIR, fname)
            elif (SYSTEM_TTFONTS and
                os.path.exists(os.path.join(SYSTEM_TTFONTS, fname))):
                ttffilename = os.path.join(SYSTEM_TTFONTS, fname)
            else:
                raise RuntimeError("TTF Font file not found: %s" % fname)
            name = ''
            if FPDF_CACHE_MODE == 0:
                unifilename = os.path.splitext(ttffilename)[0] + '.pkl'
            elif FPDF_CACHE_MODE == 2:
                unifilename = os.path.join(FPDF_CACHE_DIR, \
                    hashpath(ttffilename) + ".pkl")
            else:
                unifilename = None
            font_dict = load_cache(unifilename)
            if font_dict is None:
                ttf = TTFontFile()
                ttf.getMetrics(ttffilename)
                desc = {
                    'Ascent': int(round(ttf.ascent, 0)),
                    'Descent': int(round(ttf.descent, 0)),
                    'CapHeight': int(round(ttf.capHeight, 0)),
                    'Flags': ttf.flags,
                    'FontBBox': "[%s %s %s %s]" % (
                        int(round(ttf.bbox[0], 0)),
                        int(round(ttf.bbox[1], 0)),
                        int(round(ttf.bbox[2], 0)),
                        int(round(ttf.bbox[3], 0))),
                    'ItalicAngle': int(ttf.italicAngle),
                    'StemV': int(round(ttf.stemV, 0)),
                    'MissingWidth': int(round(ttf.defaultWidth, 0)),
                    }
                # Generate metrics .pkl file
                font_dict = {
                    'name': re.sub('[ ()]', '', ttf.fullName),
                    'type': 'TTF',
                    'desc': desc,
                    'up': round(ttf.underlinePosition),
                    'ut': round(ttf.underlineThickness),
                    'ttffile': ttffilename,
                    'fontkey': fontkey,
                    'originalsize': os.stat(ttffilename).st_size,
                    'cw': ttf.charWidths,
                    }
                if unifilename:
                    try:
                        with open(unifilename, "wb") as fh:
                            pickle.dump(font_dict, fh)
                    except IOError:
                        if not exception().errno == errno.EACCES:
                            raise  # Not a permission error.
                del ttf
            if hasattr(self,'str_alias_nb_pages'):
                sbarr = list(range(0,57))   # include numbers in the subset!
            else:
                sbarr = list(range(0,32))
            self.fonts[fontkey] = {
                'i': len(self.fonts)+1, 'type': font_dict['type'],
                'name': font_dict['name'], 'desc': font_dict['desc'],
                'up': font_dict['up'], 'ut': font_dict['ut'],
                'cw': font_dict['cw'],
                'ttffile': font_dict['ttffile'], 'fontkey': fontkey,
                'subset': sbarr, 'unifilename': unifilename,
                }
            self.font_files[fontkey] = {'length1': font_dict['originalsize'],
                                        'type': "TTF", 'ttffile': ttffilename}
            self.font_files[fname] = {'type': "TTF"}
        else:
            with open(fname, 'rb') as fontfile:
                font_dict = pickle.load(fontfile)
            self.fonts[fontkey] = {'i': len(self.fonts)+1}
            self.fonts[fontkey].update(font_dict)
            diff = font_dict.get('diff')
            if (diff):
                #Search existing encodings
                d = 0
                nb = len(self.diffs)
                for i in range(1, nb+1):
                    if(self.diffs[i] == diff):
                        d = i
                        break
                if (d == 0):
                    d = nb + 1
                    self.diffs[d] = diff
                self.fonts[fontkey]['diff'] = d
            filename = font_dict.get('filename')
            if (filename):
                if (font_dict['type'] == 'TrueType'):
                    originalsize = font_dict['originalsize']
                    self.font_files[filename]={'length1': originalsize}
                else:
                    self.font_files[filename]={'length1': font_dict['size1'],
                                               'length2': font_dict['size2']}

    def set_font(self, family,style='',size=0):
        "Select a font; size given in points"
        family=family.lower()
        if(family==''):
            family=self.font_family
        if(family=='arial'):
            family='helvetica'
        elif(family=='symbol' or family=='zapfdingbats'):
            style=''
        style=style.upper()
        if('U' in style):
            self.underline=1
            style=style.replace('U','')
        else:
            self.underline=0
        if(style=='IB'):
            style='BI'
        if(size==0):
            size=self.font_size_pt
        #Test if font is already selected
        if(self.font_family==family and self.font_style==style and self.font_size_pt==size):
            return
        #Test if used for the first time
        fontkey=family+style
        if fontkey not in self.fonts:
            #Check if one of the standard fonts
            if fontkey in self.core_fonts:
                if fontkey not in fpdf_charwidths:
                    #Load metric file
                    name=os.path.join(FPDF_FONT_DIR,family)
                    if(family=='times' or family=='helvetica'):
                        name+=style.lower()
                    with open(name+'.font') as file:
                        exec(compile(file.read(), name+'.font', 'exec'))
                    if fontkey not in fpdf_charwidths:
                        self.error('Could not include font metric file for'+fontkey)
                i=len(self.fonts)+1
                self.fonts[fontkey]={'i':i,'type':'core','name':self.core_fonts[fontkey],'up':-100,'ut':50,'cw':fpdf_charwidths[fontkey]}
            else:
                self.error('Undefined font: '+family+' '+style)
        #Select it
        self.font_family=family
        self.font_style=style
        self.font_size_pt=size
        self.font_size=size/self.k
        self.current_font=self.fonts[fontkey]
        self.unifontsubset = (self.fonts[fontkey]['type'] == 'TTF')
        if(self.page>0):
            self._out(sprintf(b'BT /F%d %.2f Tf ET',self.current_font['i'],self.font_size_pt))

    def set_font_size(self, size):
        "Set font size in points"
        if(self.font_size_pt==size):
            return
        self.font_size_pt=size
        self.font_size=size/self.k
        if(self.page>0):
            self._out(sprintf(b'BT /F%d %.2f Tf ET',self.current_font['i'],self.font_size_pt))

    def set_stretching(self, factor):
        "Set from stretch factor percents (default: 100.0)"
        if(self.font_stretching == factor):
            return
        self.font_stretching = factor
        if (self.page > 0):
            self._out(sprintf(b'BT %.2f Tz ET', self.font_stretching))

    def add_link(self):
        "Create a new internal link"
        n=len(self.links)+1
        self.links[n]=(0,0)
        return n

    def set_link(self, link,y=0,page=-1):
        "Set destination of internal link"
        if(y==-1):
            y=self.y
        if(page==-1):
            page=self.page
        self.links[link]=[page,y]

    def link(self, x,y,w,h,link):
        "Put a link on the page"
        if not self.page in self.page_links:
            self.page_links[self.page] = []
        self.page_links[self.page] += [(x*self.k,self.h_pt-y*self.k,w*self.k,h*self.k,link),]

    @check_page
    def text(self, x, y, txt=''):
        "Output a string"
        txt = self.normalize_text(txt)
        if (self.unifontsubset):
            txt2 = self._escape(StrToUTF16BE(txt, False))
            for uni in StringToArray(txt):
                self.current_font['subset'].append(uni)
        else:
            txt2 = self._escape(txt.encode(self.core_fonts_encoding, self.encode_error_handling))
        s=sprintf(b'BT %.2f %.2f Td (%s) Tj ET',x*self.k,(self.h-y)*self.k, txt2)
        if(self.underline and txt!=''):
            s+=b' '+self._dounderline(x,y,txt)
        if(self.color_flag):
            s=b'q '+self.text_color+b' '+s+b' Q'
        self._out(s)

    @check_page
    def rotate(self, angle, x=None, y=None):
        if x is None:
            x = self.x
        if y is None:
            y = self.y
        if self.angle!=0:
            self._out(b'Q')
        self.angle = angle
        if angle!=0:
            angle *= math.pi/180
            c = math.cos(angle)
            s = math.sin(angle)
            cx = x*self.k
            cy = (self.h-y)*self.k
            s = sprintf(b'q %.5F %.5F %.5F %.5F %.2F %.2F cm 1 0 0 1 %.2F %.2F cm',c,s,-s,c,cx,cy,-cx,-cy)
            self._out(s)

    def accept_page_break(self):
        "Accept automatic page break or not"
        return self.auto_page_break

    @check_page
    def cell(self, w,h=0,txt='',border=0,ln=0,align='',fill=0,link=''):
        "Output a cell"
        txt = self.normalize_text(txt)
        k=self.k
        if(self.y+h>self.page_break_trigger and not self.in_footer and self.accept_page_break()):
            #Automatic page break
            x=self.x
            ws=self.ws
            if(ws>0):
                self.ws=0
                self._out(b'0 Tw')
            self.add_page(same = True)
            self.x=x
            if(ws>0):
                self.ws=ws
                self._out(sprintf(b'%.3f Tw',ws*k))
        if(w==0):
            w=self.w-self.r_margin-self.x
        s=b''
        if(fill==1 or border==1):
            if(fill==1):
                if border==1:
                    op=b'B'
                else:
                    op=b'f'
            else:
                op=b'S'
            s=sprintf(b'%.2f %.2f %.2f %.2f re %s ',self.x*k,(self.h-self.y)*k,w*k,-h*k,op)
        if(isinstance(border,basestring)):
            x=self.x
            y=self.y
            if('L' in border):
                s+=sprintf(b'%.2f %.2f m %.2f %.2f l S ',x*k,(self.h-y)*k,x*k,(self.h-(y+h))*k)
            if('T' in border):
                s+=sprintf(b'%.2f %.2f m %.2f %.2f l S ',x*k,(self.h-y)*k,(x+w)*k,(self.h-y)*k)
            if('R' in border):
                s+=sprintf(b'%.2f %.2f m %.2f %.2f l S ',(x+w)*k,(self.h-y)*k,(x+w)*k,(self.h-(y+h))*k)
            if('B' in border):
                s+=sprintf(b'%.2f %.2f m %.2f %.2f l S ',x*k,(self.h-(y+h))*k,(x+w)*k,(self.h-(y+h))*k)
        if(txt!=''):
            if(align=='R'):
                dx=w-self.c_margin-self.get_string_width(txt, True)
            elif(align=='C'):
                dx=(w-self.get_string_width(txt, True))/2.0
            else:
                dx=self.c_margin
            if(self.color_flag):
                s+=b'q '+self.text_color+b' '

            # If multibyte, Tw has no effect - do word spacing using an adjustment before each space
            if (self.ws and self.unifontsubset):
                for uni in StringToArray(txt):
                    self.current_font['subset'].append(uni)
                space = self._escape(StrToUTF16BE(' ', False))
                s += sprintf(b'BT 0 Tw %.2F %.2F Td [',(self.x + dx) * k,(self.h - (self.y + 0.5*h+ 0.3 * self.font_size)) * k)
                t = txt.split(' ')
                numt = len(t)
                for i in range(numt):
                    tx = t[i]
                    tx = b'(' + self._escape(StrToUTF16BE(tx, False)) + b')'
                    s += sprintf(b'%s ', tx)
                    if ((i+1)<numt):
                        adj = -(self.ws * self.k) * 1000 / self.font_size_pt
                        s += sprintf(b'%d(%s) ', adj, space)
                s += b'] TJ'
                s += b' ET'
            else:
                if (self.unifontsubset):
                    txt2 = self._escape(StrToUTF16BE(txt, False))
                    for uni in StringToArray(txt):
                        self.current_font['subset'].append(uni)
                else:
                    txt2 = self._escape(txt.encode(self.core_fonts_encoding, self.encode_error_handling))
                s += sprintf(b'BT %.2f %.2f Td (%s) Tj ET',(self.x+dx)*k,(self.h-(self.y+.5*h+.3*self.font_size))*k,txt2)

            if(self.underline):
                s+=b' '+self._dounderline(self.x+dx,self.y+.5*h+.3*self.font_size,txt)
            if(self.color_flag):
                s+=b' Q'
            if(link):
                self.link(self.x+dx,self.y+.5*h-.5*self.font_size,self.get_string_width(txt, True),self.font_size,link)
        if(s):
            self._out(s)
        self.lasth=h
        if(ln>0):
            #Go to next line
            self.y+=h
            if(ln==1):
                self.x=self.l_margin
        else:
            self.x+=w

    @check_page
    def multi_cell(self, w, h, txt='', border=0, align='J', fill=0, split_only=False):
        "Output text with automatic or explicit line breaks"
        txt = self.normalize_text(txt)
        ret = [] # if split_only = True, returns splited text cells
        cw=self.current_font['cw']
        if(w==0):
            w=self.w-self.r_margin-self.x
        wmax=(w-2*self.c_margin)*1000.0/self.font_size
        s=txt.replace("\r",'')
        nb=len(s)
        if(nb>0 and s[nb-1]=="\n"):
            nb-=1
        b=0
        if(border):
            if(border==1):
                border='LTRB'
                b='LRT'
                b2='LR'
            else:
                b2=''
                if('L' in border):
                    b2+='L'
                if('R' in border):
                    b2+='R'
                if ('T' in border):
                    b=b2+'T'
                else:
                    b=b2
        sep=-1
        i=0
        j=0
        l=0
        ns=0
        nl=1
        while(i<nb):
            #Get next character
            c=s[i]
            if(c=="\n"):
                #Explicit line break
                if(self.ws>0):
                    self.ws=0
                    if not split_only:
                        self._out(b'0 Tw')
                if not split_only:
                    self.cell(w,h,substr(s,j,i-j),b,2,align,fill)
                else:
                    ret.append(substr(s,j,i-j))
                i+=1
                sep=-1
                j=i
                l=0
                ns=0
                nl+=1
                if(border and nl==2):
                    b=b2
                continue
            if(c==' '):
                sep=i
                ls=l
                ns+=1
            if self.unifontsubset:
                l += self.get_string_width(c, True) / self.font_size*1000.0
            else:
                if ord(c) < 128:
                    l += cw.get(c,0)
                else:
                    encoded_chars = c.encode(self.core_fonts_encoding, self.encode_error_handling)
                    if PY3K:
                        for byte_val in encoded_chars:
                            l += cw.get(chr(byte_val), 0)
                    else:
                        for ch in encoded_chars:
                            l += cw.get(ch, 0)
            if(l>wmax):
                #Automatic line break
                if(sep==-1):
                    if(i==j):
                        i+=1
                    if(self.ws>0):
                        self.ws=0
                        if not split_only:
                            self._out(b'0 Tw')
                    if not split_only:
                        self.cell(w,h,substr(s,j,i-j),b,2,align,fill)
                    else:
                        ret.append(substr(s,j,i-j))
                else:
                    if(align=='J'):
                        if ns>1:
                            self.ws=(wmax-ls)/1000.0*self.font_size/(ns-1)
                        else:
                            self.ws=0
                        if not split_only:
                            self._out(sprintf(b'%.3f Tw',self.ws*self.k))
                    if not split_only:
                        self.cell(w,h,substr(s,j,sep-j),b,2,align,fill)
                    else:
                        ret.append(substr(s,j,sep-j))
                    i=sep+1
                sep=-1
                j=i
                l=0
                ns=0
                nl+=1
                if(border and nl==2):
                    b=b2
            else:
                i+=1
        #Last chunk
        if(self.ws>0):
            self.ws=0
            if not split_only:
                self._out(b'0 Tw')
        if(border and 'B' in border):
            b+='B'
        if not split_only:
            self.cell(w,h,substr(s,j,i-j),b,2,align,fill)
            self.x=self.l_margin
        else:
            ret.append(substr(s,j,i-j))
        return ret

    @check_page
    def write(self, h, txt='', link=''):
        "Output text in flowing mode"
        txt = self.normalize_text(txt)
        cw=self.current_font['cw']
        w=self.w-self.r_margin-self.x
        wmax=(w-2*self.c_margin)*1000.0/self.font_size
        s=txt.replace("\r",'')
        nb=len(s)
        sep=-1
        i=0
        j=0
        l=0
        nl=1
        while(i<nb):
            #Get next character
            c=s[i]
            if(c=="\n"):
                #Explicit line break
                self.cell(w,h,substr(s,j,i-j),0,2,'',0,link)
                i+=1
                sep=-1
                j=i
                l=0
                if(nl==1):
                    self.x=self.l_margin
                    w=self.w-self.r_margin-self.x
                    wmax=(w-2*self.c_margin)*1000.0/self.font_size
                nl+=1
                continue
            if(c==' '):
                sep=i
            if self.unifontsubset:
                l += self.get_string_width(c, True) / self.font_size*1000.0
            else:
                l += cw.get(c,0)
            if(l>wmax):
                #Automatic line break
                if(sep==-1):
                    if(self.x>self.l_margin):
                        #Move to next line
                        self.x=self.l_margin
                        self.y+=h
                        w=self.w-self.r_margin-self.x
                        wmax=(w-2*self.c_margin)*1000.0/self.font_size
                        i+=1
                        nl+=1
                        continue
                    if(i==j):
                        i+=1
                    self.cell(w,h,substr(s,j,i-j),0,2,'',0,link)
                else:
                    self.cell(w,h,substr(s,j,sep-j),0,2,'',0,link)
                    i=sep+1
                sep=-1
                j=i
                l=0
                if(nl==1):
                    self.x=self.l_margin
                    w=self.w-self.r_margin-self.x
                    wmax=(w-2*self.c_margin)*1000.0/self.font_size
                nl+=1
            else:
                i+=1
        #Last chunk
        if(i!=j):
            self.cell(l/1000.0*self.font_size,h,substr(s,j),0,0,'',0,link)

    @check_page
    def image(self, name, x=None, y=None, w=0,h=0,type='',link='', is_mask=False, mask_image=None,
            image_fp=None, halign=None, valign=None):
        "Put an image on the page"
        if not name in self.images:
            #First use of image, get info
            if type == '':
                pos = name.rfind('.')
                if pos == -1:
                    self.error('image file has no extension and no type was specified: '+name)
                type = substr(name, pos+1)
            type = type.lower()
            if type in ('jpg', 'jpeg'):
                info = self._parsejpg(name, image_fp)
            elif(type == 'png'):
                info = self._parsepng(name, image_fp)
            else:
                #Allow for additional formats
                #maybe the image is not showing the correct extension,
                #but the header is OK,
                succeed_parsing = False
                #try all the parsing functions
                parsing_functions = [self._parsejpg,self._parsepng,self._parsegif]
                for pf in parsing_functions:
                    try:
                        info = pf(name, image_fp)
                        succeed_parsing = True
                        break
                    except:
                        pass
                #last resource
                if not succeed_parsing:
                    mtd='_parse'+type
                    if not hasattr(self,mtd):
                        self.error('Unsupported image type: '+type)
                    info=getattr(self, mtd)(name)
                mtd='_parse'+type
                if not hasattr(self,mtd):
                    self.error('Unsupported image type: '+type)
                info=getattr(self, mtd)(name)
            info['i']=len(self.images)+1
            # is_mask and mask_image
            if is_mask and info['cs'] != 'DeviceGray':
                self.error('Mask must be a gray scale image')
            if mask_image:
                info['masked'] = mask_image
            self.images[name]=info
        else:
            info=self.images[name]
        #Automatic width and height calculation if needed
        if(w==0 and h==0):
            #Put image at 72 dpi
            w=info['w']/self.k
            h=info['h']/self.k
        elif(w==0):
            w=h*info['w']/info['h']
        elif(h==0):
            h=w*info['h']/info['w']

        if halign or valign:
            # horizontal and vertical alignment of image within given width and height
            # by keeping original image aspect ratio
            image_width, image_height = info['w'], info['h']
            if image_width <= w and image_height <= h:
                image_display_width, image_display_height = image_width, image_height
            else:
                size_ratio = image_width / image_height
                tmp = w / size_ratio
                if tmp <= h:
                    image_display_width = w
                    image_display_height = tmp
                else:
                    image_display_width = h * size_ratio
                    image_display_height = h
            if halign == 'C':  # center
                x += (w - image_display_width) / 2
            elif halign == 'R':  # right
                x += w - image_display_width
            if valign in ('C', 'M'):  # center/middle
                y += (h - image_display_height) / 2
            elif valign == 'B':  # bottom
                y += h - image_display_height
            w, h = image_display_width, image_display_height

        # Flowing mode
        if y is None:
            if (self.y + h > self.page_break_trigger and not self.in_footer and self.accept_page_break()):
                #Automatic page break
                x = self.x
                self.add_page(same = True)
                self.x = x
            y = self.y
            self.y += h
        if x is None:
            x = self.x
        if not is_mask:
            self._out(sprintf(b'q %.2f 0 0 %.2f %.2f %.2f cm /I%d Do Q',w*self.k,h*self.k,x*self.k,(self.h-(y+h))*self.k,info['i']))
        if(link):
            self.link(x,y,w,h,link)

        return info

    @check_page
    def ln(self, h=''):
        "Line Feed; default value is last cell height"
        self.x=self.l_margin
        if(isinstance(h, basestring)):
            self.y+=self.lasth
        else:
            self.y+=h

    def get_x(self):
        "Get x position"
        return self.x

    def set_x(self, x):
        "Set x position"
        if(x>=0):
            self.x=x
        else:
            self.x=self.w+x

    def get_y(self):
        "Get y position"
        return self.y

    def set_y(self, y):
        "Set y position and reset x"
        self.x=self.l_margin
        if(y>=0):
            self.y=y
        else:
            self.y=self.h+y

    def set_xy(self, x,y):
        "Set x and y positions"
        self.set_y(y)
        self.set_x(x)

    def output(self, name='',dest=''):
        """Output PDF to some destination

        By default the PDF is written to sys.stdout. If a name is given, the
        PDF is written to a new file. If dest='S' is given, the PDF data is
        returned as a byte string."""

        #Finish document if necessary
        if(self.state<3):
            self.close()
        dest=dest.upper()
        if(dest==''):
            if(name==''):
                dest='I'
            else:
                dest='F'
        if dest in ('I', 'D'):
            sys.stdout.write(self.buffer)
        elif dest=='F':
            #Save to local file
            with open(name,'wb') as f:
                f.write(self.buffer)
        elif dest=='S':
            #Return as bytes
            return bytes(self.buffer)
        else:
            self.error('Incorrect output destination: '+dest)

    def normalize_text(self, txt):
        "Check that text input is unicode"
        if not PY3K and isinstance(txt, str):
            return txt.decode("utf-8")
        return txt

    def _dochecks(self):
        #Check for locale-related bug
#        if(1.1==1):
#            self.error("Don\'t alter the locale before including class file");
        #Check for decimal separator
        if(sprintf('%.1f',1.0)!='1.0'):
            import locale
            locale.setlocale(locale.LC_NUMERIC,'C')

    def _getfontpath(self):
        return FPDF_FONT_DIR+'/'

    def _putpages(self):
        nb = self.page
        if hasattr(self, 'str_alias_nb_pages'):
            # Replace number of pages in fonts using subsets (unicode)
            alias = StrToUTF16BE(self.str_alias_nb_pages, False)
            r = StrToUTF16BE(str(nb), False)
            for n in range(1, nb + 1):
                self.pages[n]["content"] = \
                    self.pages[n]["content"].replace(alias, r)
            # Now repeat for no pages in non-subset fonts
            for n in range(1,nb + 1):
                self.pages[n]["content"] = \
                    self.pages[n]["content"].replace(self.str_alias_nb_pages,
                        str(nb))
        if self.def_orientation == 'P':
            dw_pt = self.dw_pt
            dh_pt = self.dh_pt
        else:
            dw_pt = self.dh_pt
            dh_pt = self.dw_pt
        if self.compress:
            filter = b'/Filter /FlateDecode '
        else:
            filter = b''
        for n in range(1, nb + 1):
            # Page
            self._newobj()
            self._out(b'<</Type /Page')
            self._out(b'/Parent 1 0 R')
            w_pt = self.pages[n]["w_pt"]
            h_pt = self.pages[n]["h_pt"]
            if w_pt != dw_pt or h_pt != dh_pt:
                self._out(sprintf(b'/MediaBox [0 0 %.2f %.2f]', w_pt, h_pt))
            self._out(b'/Resources 2 0 R')
            if self.page_links and n in self.page_links:
                # Links
                annots = b'/Annots ['
                for pl in self.page_links[n]:
                    rect = sprintf(b'%.2f %.2f %.2f %.2f', pl[0], pl[1],
                        pl[0] + pl[2], pl[1] - pl[3])
                    annots += b'<</Type /Annot /Subtype /Link /Rect [' + \
                        rect + b'] /Border [0 0 0] '
                    if isinstance(pl[4], basestring):
                        annots += b'/A <</S /URI /URI ' + \
                            self._textstring(pl[4]) + b'>>>>'
                    else:
                        l = self.links[pl[4]]
                        if l[0] in self.orientation_changes:
                            h = w_pt
                        else:
                            h = h_pt
                        annots += sprintf(b'/Dest [%d 0 R /XYZ 0 %.2f null]>>',
                            1 + 2 * l[0], h - l[1] * self.k)
                self._out(annots + b']')
            if self.pdf_version > '1.3':
                self._out(b"/Group <</Type /Group /S /Transparency"\
                    b"/CS /DeviceRGB>>")
            self._out(b'/Contents %d 0 R>>' % (self.n + 1))
            self._out(b'endobj')
            # Page content
            content = self.pages[n]["content"]
            if self.compress:
                p = zlib.compress(content)
            else:
                p = content
            self._newobj()
            self._out(b'<<%s/Length %d>>' % (filter, len(p)))
            self._putstream(p)
            self._out(b'endobj')
        # Pages root
        self.offsets[1] = len(self.buffer)
        self._out(b'1 0 obj')
        self._out(b'<</Type /Pages')
        kids = b'/Kids ['
        for i in range(0, nb):
            kids += b'%d 0 R ' % (3 + 2 * i)
        self._out(kids + b']')
        self._out(b'/Count %d' % nb)
        self._out(sprintf(b'/MediaBox [0 0 %.2f %.2f]', dw_pt, dh_pt))
        self._out(b'>>')
        self._out(b'endobj')

    def _putfonts(self):
        nf=self.n
        for diff in self.diffs:
            #Encodings
            self._newobj()
            self._out(b'<</Type /Encoding /BaseEncoding /WinAnsiEncoding /Differences [%d]>>' % self.diffs[diff])
            self._out(b'endobj')
        for name,info in self.font_files.items():
            if 'type' in info and info['type'] != 'TTF':
                #Font file embedding
                self._newobj()
                self.font_files[name]['n']=self.n
                with open(self._getfontpath()+name,'rb',1) as f:
                    font=f.read()
                compressed=(substr(name,-2)=='.z')
                if(not compressed and 'length2' in info):
                    header=(ord(font[0])==128)
                    if(header):
                        #Strip first binary header
                        font=substr(font,6)
                    if(header and ord(font[info['length1']])==128):
                        #Strip second binary header
                        font=substr(font,0,info['length1'])+substr(font,info['length1']+6)
                self._out(b'<</Length '+str(len(font)))
                if(compressed):
                    self._out(b'/Filter /FlateDecode')
                self._out(b'/Length1 %d' % info['length1'])
                if('length2' in info):
                    self._out(b'/Length2 %d /Length3 0' % info['length2'])
                self._out(b'>>')
                self._putstream(font)
                self._out(b'endobj')
        flist = [(x[1]["i"],x[0],x[1]) for x in self.fonts.items()]
        flist.sort()
        for idx,k,font in flist:
            #Font objects
            self.fonts[k]['n']=self.n+1
            type=font['type']
            name=font['name']
            if(type=='core'):
                #Standard font
                self._newobj()
                self._out(b'<</Type /Font')
                self._out(b'/BaseFont /'+name.encode())
                self._out(b'/Subtype /Type1')
                if(name!='Symbol' and name!='ZapfDingbats'):
                    self._out(b'/Encoding /WinAnsiEncoding')
                self._out(b'>>')
                self._out(b'endobj')
            elif(type=='Type1' or type=='TrueType'):
                #Additional Type1 or TrueType font
                self._newobj()
                self._out(b'<</Type /Font')
                self._out(b'/BaseFont /'+name.encode())
                self._out(b'/Subtype /'+type.encode())
                self._out(b'/FirstChar 32 /LastChar 255')
                self._out(b'/Widths %d 0 R' % (self.n+1))
                self._out(b'/FontDescriptor %d 0 R' % (self.n+2))
                if(font['enc']):
                    if('diff' in font):
                        self._out(b'/Encoding %d 0 R' % (nf+font['diff']))
                    else:
                        self._out(b'/Encoding /WinAnsiEncoding')
                self._out(b'>>')
                self._out(b'endobj')
                #Widths
                self._newobj()
                cw=font['cw']
                s=b'['
                for i in range(32,256):
                    # Get doesn't raise exception; returns 0 instead of None if not set
                    s+=b'%d ' % (cw.get(chr(i)) or 0)
                self._out(s+b']')
                self._out(b'endobj')
                #Descriptor
                self._newobj()
                s=b'<</Type /FontDescriptor /FontName /'+name.encode()
                for k in (b'Ascent', b'Descent', b'CapHeight', b'Flags', b'FontBBox', b'ItalicAngle', b'StemV', b'MissingWidth'):
                    s += b' /%s %s' % (k, font['desc'][k].encode())
                filename=font['file']
                if(filename):
                    s+=b' /FontFile'
                    if type!='Type1':
                        s+=b'2'
                    s+=b' '+str(self.font_files[filename]['n']).encode()+b' 0 R'
                self._out(s+b'>>')
                self._out(b'endobj')
            elif (type == 'TTF'):
                self.fonts[k]['n'] = self.n + 1
                ttf = TTFontFile()
                fontname = 'MPDFAA' + '+' + font['name']
                subset = font['subset']
                del subset[0]
                ttfontstream = ttf.makeSubset(font['ttffile'], subset)
                ttfontsize = len(ttfontstream)
                fontstream = zlib.compress(ttfontstream)
                codeToGlyph = ttf.codeToGlyph
                ##del codeToGlyph[0]
                # Type0 Font
                # A composite font - a font composed of other fonts, organized hierarchically
                self._newobj()
                self._out(b'<</Type /Font')
                self._out(b'/Subtype /Type0')
                self._out(b'/BaseFont /' + fontname.encode() + b'')
                self._out(b'/Encoding /Identity-H')
                self._out(b'/DescendantFonts [%d 0 R]' % (self.n + 1))
                self._out(b'/ToUnicode %d 0 R' % (self.n + 2))
                self._out(b'>>')
                self._out(b'endobj')

                # CIDFontType2
                # A CIDFont whose glyph descriptions are based on TrueType font technology
                self._newobj()
                self._out(b'<</Type /Font')
                self._out(b'/Subtype /CIDFontType2')
                self._out(b'/BaseFont /' + fontname.encode() + b'')
                self._out(b'/CIDSystemInfo %d 0 R' % (self.n + 2))
                self._out(b'/FontDescriptor %d 0 R' % (self.n + 3))
                if (font['desc'].get('MissingWidth')):
                    self._out(b'/DW %d' % font['desc']['MissingWidth'])
                self._putTTfontwidths(font, ttf.maxUni)
                self._out(b'/CIDToGIDMap %d 0 R' % (self.n + 4))
                self._out(b'>>')
                self._out(b'endobj')

                # ToUnicode
                self._newobj()
                toUni = b"/CIDInit /ProcSet findresource begin\n" \
                        b"12 dict begin\n" \
                        b"begincmap\n" \
                        b"/CIDSystemInfo\n" \
                        b"<</Registry (Adobe)\n" \
                        b"/Ordering (UCS)\n" \
                        b"/Supplement 0\n" \
                        b">> def\n" \
                        b"/CMapName /Adobe-Identity-UCS def\n" \
                        b"/CMapType 2 def\n" \
                        b"1 begincodespacerange\n" \
                        b"<0000> <FFFF>\n" \
                        b"endcodespacerange\n" \
                        b"1 beginbfrange\n" \
                        b"<0000> <FFFF> <0000>\n" \
                        b"endbfrange\n" \
                        b"endcmap\n" \
                        b"CMapName currentdict /CMap defineresource pop\n" \
                        b"end\n" \
                        b"end"
                self._out(b'<</Length %d>>' % (len(toUni)))
                self._putstream(toUni)
                self._out(b'endobj')

                # CIDSystemInfo dictionary
                self._newobj()
                self._out(b'<</Registry (Adobe)')
                self._out(b'/Ordering (UCS)')
                self._out(b'/Supplement 0')
                self._out(b'>>')
                self._out(b'endobj')

                # Font descriptor
                self._newobj()
                self._out(b'<</Type /FontDescriptor')
                self._out(b'/FontName /' + fontname.encode())
                for kd in ('Ascent', 'Descent', 'CapHeight', 'Flags', 'FontBBox', 'ItalicAngle', 'StemV', 'MissingWidth'):
                    v = font['desc'][kd]
                    if (kd == 'Flags'):
                        v = v | 4
                        v = v & ~32 # SYMBOLIC font flag
                    if isinstance(v, int):
                        self._out(b' /%s %d' % (kd.encode(), v))
                    else:
                        self._out(b' /%s %s' % (kd.encode(), v.encode()))
                self._out(b'/FontFile2 %d 0 R' % (self.n + 2))
                self._out(b'>>')
                self._out(b'endobj')

                # Embed CIDToGIDMap
                # A specification of the mapping from CIDs to glyph indices
                cidtogidmap = bytearray(256*256*2)
                for cc, glyph in codeToGlyph.items():
                    cidtogidmap[cc*2] = (glyph >> 8)
                    cidtogidmap[cc*2 + 1] = (glyph & 0xFF)
                cidtogidmap = zlib.compress(bytes(cidtogidmap))
                self._newobj()
                self._out(b'<</Length %d' % len(cidtogidmap))
                self._out(b'/Filter /FlateDecode')
                self._out(b'>>')
                self._putstream(cidtogidmap)
                self._out(b'endobj')

                #Font file
                self._newobj()
                self._out(b'<</Length %d' % len(fontstream))
                self._out(b'/Filter /FlateDecode')
                self._out(b'/Length1 %d' % ttfontsize)
                self._out(b'>>')
                self._putstream(fontstream)
                self._out(b'endobj')
                del ttf
            else:
                #Allow for additional types
                mtd='_put'+type.lower()
                if(not method_exists(self,mtd)):
                    self.error('Unsupported font type: '+type)
                self.mtd(font)

    def _putTTfontwidths(self, font, maxUni):
        if font['unifilename']:
            cw127fname = os.path.splitext(font['unifilename'])[0] + '.cw127.pkl'
        else:
            cw127fname = None
        font_dict = load_cache(cw127fname)
        if font_dict is None:
            rangeid = 0
            range_ = {}
            range_interval = {}
            prevcid = -2
            prevwidth = -1
            interval = False
            startcid = 1
        else:
            rangeid = font_dict['rangeid']
            range_ = font_dict['range']
            prevcid = font_dict['prevcid']
            prevwidth = font_dict['prevwidth']
            interval = font_dict['interval']
            range_interval = font_dict['range_interval']
            startcid = 128
        cwlen = maxUni + 1

        # for each character
        subset = set(font['subset'])
        for cid in range(startcid, cwlen):
            if cid == 128 and cw127fname and not os.path.exists(cw127fname):
                try:
                    with open(cw127fname, "wb") as fh:
                        font_dict = {}
                        font_dict['rangeid'] = rangeid
                        font_dict['prevcid'] = prevcid
                        font_dict['prevwidth'] = prevwidth
                        font_dict['interval'] = interval
                        font_dict['range_interval'] = range_interval
                        font_dict['range'] = range_
                        pickle.dump(font_dict, fh)
                except IOError:
                    if not exception().errno == errno.EACCES:
                        raise  # Not a permission error.
            if cid > 255 and (cid not in subset): #
                continue
            width = font['cw'][cid]
            if (width == 0):
                continue
            if (width == 65535): width = 0
            if ('dw' not in font or (font['dw'] and width != font['dw'])):
                if (cid == (prevcid + 1)):
                    if (width == prevwidth):
                        if (width == range_[rangeid][0]):
                            range_.setdefault(rangeid, []).append(width)
                        else:
                            range_[rangeid].pop()
                            # new range
                            rangeid = prevcid
                            range_[rangeid] = [prevwidth, width]
                        interval = True
                        range_interval[rangeid] = True
                    else:
                        if (interval):
                            # new range
                            rangeid = cid
                            range_[rangeid] = [width]
                        else:
                            range_[rangeid].append(width)
                        interval = False
                else:
                    rangeid = cid
                    range_[rangeid] = [width]
                    interval = False
                prevcid = cid
                prevwidth = width
        prevk = -1
        nextk = -1
        prevint = False
        for k, ws in sorted(range_.items()):
            cws = len(ws)
            if (k == nextk and not prevint and (not k in range_interval or cws < 3)):
                if (k in range_interval):
                    del range_interval[k]
                range_[prevk] = range_[prevk] + range_[k]
                del range_[k]
            else:
                prevk = k
            nextk = k + cws
            if (k in range_interval):
                prevint = (cws > 3)
                del range_interval[k]
                nextk -= 1
            else:
                prevint = False
        w = []
        for k, ws in sorted(range_.items()):
            if (len(set(ws)) == 1):
                w.append(b' %d %d %s' % (k, k + len(ws) - 1, str(ws[0]).encode('ascii')))
            else:
                w.append(b' %d [ %s ]\n' % (k, ' '.join([str(int(h)) for h in ws]).encode('ascii'))) ##
        self._out(b'/W [%s]' % b''.join(w))

    def _putimages(self):
        filter=b''
        if self.compress:
            filter=b'/Filter /FlateDecode '
        i = [(x[1]["i"],x[1]) for x in self.images.items()]
        i.sort()
        for idx,info in i:
            self._putimage(info)
            del info['data']
            if 'smask' in info:
                del info['smask']

    def _putimage(self, info):
        if 'data' in info:
            self._newobj()
            info['n']=self.n
            self._out(b'<</Type /XObject')
            self._out(b'/Subtype /Image')
            self._out(b'/Width %d' % info['w'])
            self._out(b'/Height %d' % info['h'])
            # set mask object for this image
            if 'masked' in info:
                self._out(b'/SMask %d 0 R' % (info['masked']['n']+1))

            if(info['cs']=='Indexed'):
                self._out(b'/ColorSpace [/Indexed /DeviceRGB %d %d 0 R]' % (len(info['pal'])//3-1, self.n+1))
            else:
                self._out(b'/ColorSpace /' + info['cs'].encode())
                if(info['cs']=='DeviceCMYK'):
                    self._out(b'/Decode [1 0 1 0 1 0 1 0]')
            self._out(b'/BitsPerComponent %d' % info['bpc'])
            if 'f' in info:
                self._out(b'/Filter /'+info['f'].encode())
            if 'dp' in info:
                self._out(b'/DecodeParms <<' + info['dp'].encode() + b'>>')
            if('trns' in info and isinstance(info['trns'], list)):
                trns = b''
                for i in range(0,len(info['trns'])):
                    trns += b'%d %d ' % (info['trns'][i], info['trns'][i])
                self._out(b'/Mask [' + trns + b']')
            if('smask' in info):
                self._out(b'/SMask %d 0 R' % (self.n+1))
            self._out(b'/Length %d>>' % len(info['data']))
            self._putstream(info['data'])
            self._out(b'endobj')
            # Soft mask
            if('smask' in info):
                dp = '/Predictor 15 /Colors 1 /BitsPerComponent 8 /Columns ' + str(info['w'])
                smask = {'w': info['w'], 'h': info['h'], 'cs': 'DeviceGray', 'bpc': 8, 'f': info['f'], 'dp': dp, 'data': info['smask']}
                self._putimage(smask)
            #Palette
            if(info['cs']=='Indexed'):
                self._newobj()
                filter = self.compress and b'/Filter /FlateDecode ' or b''
                if self.compress:
                    pal=zlib.compress(info['pal'])
                else:
                    pal=info['pal']
                self._out(b'<<%s/Length %d>>' % (filter, len(pal)))
                self._putstream(pal)
                self._out(b'endobj')

    def _putxobjectdict(self):
        i = [(x["i"],x["n"]) for x in self.images.values()]
        i.sort()
        for idx,n in i:
            self._out(b'/I%d %d 0 R' % (idx, n))

    def _putresourcedict(self):
        self._out(b'/ProcSet [/PDF /Text /ImageB /ImageC /ImageI]')
        self._out(b'/Font <<')
        f = [(x["i"],x["n"]) for x in self.fonts.values()]
        f.sort()
        for idx,n in f:
            self._out(b'/F%d %d 0 R' % (idx, n))
        self._out(b'>>')
        self._out(b'/XObject <<')
        self._putxobjectdict()
        self._out(b'>>')

    def _putresources(self):
        self._putfonts()
        self._putimages()
        #Resource dictionary
        self.offsets[2] = len(self.buffer)
        self._out(b'2 0 obj')
        self._out(b'<<')
        self._putresourcedict()
        self._out(b'>>')
        self._out(b'endobj')

    def _putinfo(self):
        self._out(b'/Producer ' + self._textstring('PyFPDF '+FPDF_VERSION+' http://pyfpdf.googlecode.com/'))
        if hasattr(self,'title'):
            self._out(b'/Title '+self._textstring(self.title))
        if hasattr(self,'subject'):
            self._out(b'/Subject '+self._textstring(self.subject))
        if hasattr(self,'author'):
            self._out(b'/Author '+self._textstring(self.author))
        if hasattr (self,'keywords'):
            self._out(b'/Keywords '+self._textstring(self.keywords))
        if hasattr(self,'creator'):
            self._out(b'/Creator '+self._textstring(self.creator))
        self._out(b'/CreationDate '+self._textstring('D:'+datetime.now().strftime('%Y%m%d%H%M%S')))

    def _putcatalog(self):
        self._out(b'/Type /Catalog')
        self._out(b'/Pages 1 0 R')
        if(self.zoom_mode=='fullpage'):
            self._out(b'/OpenAction [3 0 R /Fit]')
        elif(self.zoom_mode=='fullwidth'):
            self._out(b'/OpenAction [3 0 R /FitH null]')
        elif(self.zoom_mode=='real'):
            self._out(b'/OpenAction [3 0 R /XYZ null null 1]')
        elif(not isinstance(self.zoom_mode,basestring)):
            self._out(sprintf(b'/OpenAction [3 0 R /XYZ null null %s]',self.zoom_mode/100))
        if(self.layout_mode=='single'):
            self._out(b'/PageLayout /SinglePage')
        elif(self.layout_mode=='continuous'):
            self._out(b'/PageLayout /OneColumn')
        elif(self.layout_mode=='two'):
            self._out(b'/PageLayout /TwoColumnLeft')

    def _putheader(self):
        self._out(b'%PDF-' + self.pdf_version.encode())

    def _puttrailer(self):
        self._out(b'/Size %d' % (self.n+1))
        self._out(b'/Root %d 0 R' % (self.n))
        self._out(b'/Info %d 0 R' % (self.n-1))

    def _enddoc(self):
        self._putheader()
        self._putpages()
        self._putresources()
        #Info
        self._newobj()
        self._out(b'<<')
        self._putinfo()
        self._out(b'>>')
        self._out(b'endobj')
        #Catalog
        self._newobj()
        self._out(b'<<')
        self._putcatalog()
        self._out(b'>>')
        self._out(b'endobj')
        #Cross-ref
        o=len(self.buffer)
        self._out(b'xref')
        self._out(b'0 %d' % (self.n+1))
        self._out(b'0000000000 65535 f ')
        for i in range(1,self.n+1):
            self._out(sprintf(b'%010d 00000 n ',self.offsets[i]))
        #Trailer
        self._out(b'trailer')
        self._out(b'<<')
        self._puttrailer()
        self._out(b'>>')
        self._out(b'startxref')
        self._out(str(o).encode())
        self._out(b'%%EOF')
        self.state=3

    def _beginpage(self, orientation, format, same):
        self.page += 1
        self.pages[self.page] = {"content": b''}
        self.state = 2
        self.x = self.l_margin
        self.y = self.t_margin
        self.font_family = ''
        self.font_stretching = 100
        if not same:
            # Page format
            if format:
                # Change page format
                self.fw_pt, self.fh_pt = self.get_page_format(format, self.k)
            else:
                # Set to default format
                self.fw_pt = self.dw_pt
                self.fh_pt = self.dh_pt
            self.fw = self.fw_pt / self.k
            self.fh = self.fh_pt / self.k
            # Page orientation
            if not orientation:
                orientation = self.def_orientation
            else:
                orientation = orientation[0].upper()
            if orientation == 'P':
                self.w_pt = self.fw_pt
                self.h_pt = self.fh_pt
            else:
                self.w_pt = self.fh_pt
                self.h_pt = self.fw_pt
            self.w = self.w_pt / self.k
            self.h = self.h_pt / self.k
            self.cur_orientation = orientation
            self.page_break_trigger = self.h - self.b_margin
            self.cur_orientation = orientation
        self.pages[self.page]["w_pt"] = self.w_pt
        self.pages[self.page]["h_pt"] = self.h_pt

    def _endpage(self):
        #End of page contents
        self.state=1

    def _newobj(self):
        #Begin a new object
        self.n+=1
        self.offsets[self.n] = len(self.buffer)
        self._out(b'%d 0 obj' % self.n)

    def _dounderline(self, x, y, txt):
        #Underline text
        up=self.current_font['up']
        ut=self.current_font['ut']
        w=self.get_string_width(txt, True)+self.ws*txt.count(' ')
        return sprintf(b'%.2f %.2f %.2f %.2f re f',x*self.k,(self.h-(y-up/1000.0*self.font_size))*self.k,w*self.k,-ut/1000.0*self.font_size_pt)

    def load_resource(self, reason, filename):
        "Load external file"
        # by default loading from network is allowed for all images
        if reason == "image":
            if filename.startswith("http://") or filename.startswith("https://"):
                f = BytesIO(urlopen(filename).read())
            else:
                f = open(filename, "rb")
            return f
        else:
            self.error("Unknown resource loading reason \"%s\"" % reason)

    def _parsejpg(self, filename, image_fp=None):
        # Extract info from a JPEG file
        f = None
        try:
            f = image_fp if image_fp else self.load_resource("image", filename)
            while True:
                markerHigh, markerLow = struct.unpack('BB', f.read(2))
                if markerHigh != 0xFF or markerLow < 0xC0:
                    raise SyntaxError('No JPEG marker found')
                elif markerLow == 0xDA: # SOS
                    raise SyntaxError('No JPEG SOF marker found')
                elif (markerLow == 0xC8 or # JPG
                      (markerLow >= 0xD0 and markerLow <= 0xD9) or # RSTx
                      (markerLow >= 0xF0 and markerLow <= 0xFD)): # JPGx
                    pass
                else:
                    dataSize, = struct.unpack('>H', f.read(2))
                    data = f.read(dataSize - 2) if dataSize > 2 else ''
                    if ((markerLow >= 0xC0 and markerLow <= 0xC3) or # SOF0 - SOF3
                        (markerLow >= 0xC5 and markerLow <= 0xC7) or # SOF4 - SOF7
                        (markerLow >= 0xC9 and markerLow <= 0xCB) or # SOF9 - SOF11
                        (markerLow >= 0xCD and markerLow <= 0xCF)): # SOF13 - SOF15
                        bpc, height, width, layers = struct.unpack_from('>BHHB', data)
                        colspace = 'DeviceRGB' if layers == 3 else ('DeviceCMYK' if layers == 4 else 'DeviceGray')
                        break
        except Exception:
            if f:
                f.close()
            self.error('Missing or incorrect image file: %s. error: %s' % (filename, str(exception())))

        with f:
            # Read whole file from the start
            f.seek(0)
            data = f.read()
        return {'w':width,'h':height,'cs':colspace,'bpc':bpc,'f':'DCTDecode','data':data}

    def _parsegif(self, filename, image_fp=None):
        # Extract info from a GIF file (via PNG conversion)
        if Image is None:
            self.error('PIL is required for GIF support')
        try:
            im = Image.open(image_fp if image_fp else filename)
        except Exception:
            self.error('Missing or incorrect image file: %s. error: %s' % (filename, str(exception())))
        else:
            # Use temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as \
                    f:
                tmp = f.name
            if "transparency" in im.info:
                im.save(tmp, transparency = im.info['transparency'])
            else:
                im.save(tmp)
            info = self._parsepng(tmp)
            os.unlink(tmp)
        return info

    def _parsepng(self, filename, image_fp=None):
        #Extract info from a PNG file
        f = image_fp if image_fp else self.load_resource("image", filename)
        #Check signature
        magic = f.read(8).decode("latin1")
        signature = '\x89'+'PNG'+'\r'+'\n'+'\x1a'+'\n'
        if not PY3K: signature = signature.decode("latin1")
        if(magic!=signature):
            self.error('Not a PNG file: ' + filename)
        #Read header chunk
        f.read(4)
        chunk = f.read(4).decode("latin1")
        if(chunk!='IHDR'):
            self.error('Incorrect PNG file: ' + filename)
        w=self._freadint(f)
        h=self._freadint(f)
        bpc=ord(f.read(1))
        if(bpc>8):
            self.error('16-bit depth not supported: ' + filename)
        ct=ord(f.read(1))
        if(ct==0 or ct==4):
            colspace='DeviceGray'
        elif(ct==2 or ct==6):
            colspace='DeviceRGB'
        elif(ct==3):
            colspace='Indexed'
        else:
            self.error('Unknown color type: ' + filename)
        if(ord(f.read(1))!=0):
            self.error('Unknown compression method: ' + filename)
        if(ord(f.read(1))!=0):
            self.error('Unknown filter method: ' + filename)
        if(ord(f.read(1))!=0):
            self.error('Interlacing not supported: ' + filename)
        f.read(4)
        dp='/Predictor 15 /Colors '
        if colspace == 'DeviceRGB':
            dp+='3'
        else:
            dp+='1'
        dp+=' /BitsPerComponent '+str(bpc)+' /Columns '+str(w)+''
        #Scan chunks looking for palette, transparency and image data
        pal=''
        trns=''
        data=bytearray() if PY3K else str()
        n=1
        while n != None:
            n=self._freadint(f)
            type=f.read(4).decode("latin1")
            if(type=='PLTE'):
                #Read palette
                pal=f.read(n)
                f.read(4)
            elif(type=='tRNS'):
                #Read transparency info
                t=f.read(n)
                if(ct==0):
                    trns=[ord(substr(t,1,1)),]
                elif(ct==2):
                    trns=[ord(substr(t,1,1)),ord(substr(t,3,1)),ord(substr(t,5,1))]
                else:
                    pos=t.find('\x00'.encode("latin1"))
                    if(pos!=-1):
                        trns=[pos,]
                f.read(4)
            elif(type=='IDAT'):
                #Read image data block
                data+=f.read(n)
                f.read(4)
            elif(type=='IEND'):
                break
            else:
                f.read(n+4)
        if(colspace=='Indexed' and not pal):
            self.error('Missing palette in ' + filename)
        f.close()
        info = {'w':w,'h':h,'cs':colspace,'bpc':bpc,'f':'FlateDecode','dp':dp,'pal':pal,'trns':trns,}
        if(ct>=4):
            # Extract alpha channel
            data = zlib.decompress(data)
            color = bytearray() if PY3K else b('')
            alpha = bytearray() if PY3K else b('')
            if(ct==4):
                # Gray image
                length = 2*w
                for i in range(h):
                    pos = (1+length)*i
                    color += b(data[pos])
                    alpha += b(data[pos])
                    line = substr(data, pos+1, length)
                    for x in range(0, length, 2):
                        color += line[x:x+1]
                        alpha += line[x+1:x+2]
            else:
                # RGB image
                length = 4*w
                for i in range(h):
                    pos = (1+length)*i
                    color += b(data[pos])
                    alpha += b(data[pos])
                    line = substr(data, pos+1, length)
                    for x in range(0, length, 4):
                        color += line[x:x+3]
                        alpha += line[x+3:x+4]
            del data
            data = zlib.compress(color)
            info['smask'] = zlib.compress(alpha)
            if (self.pdf_version < '1.4'):
                self.pdf_version = '1.4'
        info['data'] = data
        return info

    def _freadint(self, f):
        #Read a 4-byte integer from file
        try:
            return struct.unpack('>I', f.read(4))[0]
        except:
            return None

    def _textstring(self, s):
        #Format a text string and return as bytes
        return b'(' + self._escape(s.encode()) + b')'

    def _escape(self, s):
        #Add \ before \, ( and )
        return s.replace(b'\\',b'\\\\').replace(b')',b'\\)').replace(b'(',b'\\(').replace(b'\r',b'\\r')

    def _putstream(self, s):
        self._out(b'stream')
        self._out(s)
        self._out(b'endstream')

    def _out(self, s):
        assert isinstance(s, (bytes, bytearray))
        # Add a line to the document
        if(self.state == 2):
            self.pages[self.page]["content"] += (s + b"\n")
        else:
            self.buffer += (s + b"\n")

    @check_page
    def interleaved2of5(self, txt, x, y, w=1.0, h=10.0):
        "Barcode I2of5 (numeric), adds a 0 if odd lenght"
        narrow = w / 3.0
        wide = w

        # wide/narrow codes for the digits
        bar_char={'0': 'nnwwn', '1': 'wnnnw', '2': 'nwnnw', '3': 'wwnnn',
                  '4': 'nnwnw', '5': 'wnwnn', '6': 'nwwnn', '7': 'nnnww',
                  '8': 'wnnwn', '9': 'nwnwn', 'A': 'nn', 'Z': 'wn'}

        self.set_fill_color(0)
        code = txt
        # add leading zero if code-length is odd
        if len(code) % 2 != 0:
            code = '0' + code

        # add start and stop codes
        code = 'AA' + code.lower() + 'ZA'

        for i in range(0, len(code), 2):
            # choose next pair of digits
            char_bar = code[i]
            char_space = code[i+1]
            # check whether it is a valid digit
            if not char_bar in bar_char.keys():
                raise RuntimeError ('Char "%s" invalid for I25: ' % char_bar)
            if not char_space in bar_char.keys():
                raise RuntimeError ('Char "%s" invalid for I25: ' % char_space)

            # create a wide/narrow-seq (first digit=bars, second digit=spaces)
            seq = ''
            for s in range(0, len(bar_char[char_bar])):
                seq += bar_char[char_bar][s] + bar_char[char_space][s]

            for bar in range(0, len(seq)):
                # set line_width depending on value
                if seq[bar] == 'n':
                    line_width = narrow
                else:
                    line_width = wide

                # draw every second value, the other is represented by space
                if bar % 2 == 0:
                    self.rect(x, y, line_width, h, 'F')

                x += line_width


    @check_page
    def code39(self, txt, x, y, w=1.5, h=5.0):
        """Barcode 3of9"""
        dim = {'w': w, 'n': w/3.}
        chars = {
            '0': 'nnnwwnwnn', '1': 'wnnwnnnnw', '2': 'nnwwnnnnw',
            '3': 'wnwwnnnnn', '4': 'nnnwwnnnw', '5': 'wnnwwnnnn',
            '6': 'nnwwwnnnn', '7': 'nnnwnnwnw', '8': 'wnnwnnwnn',
            '9': 'nnwwnnwnn', 'A': 'wnnnnwnnw', 'B': 'nnwnnwnnw',
            'C': 'wnwnnwnnn', 'D': 'nnnnwwnnw', 'E': 'wnnnwwnnn',
            'F': 'nnwnwwnnn', 'G': 'nnnnnwwnw', 'H': 'wnnnnwwnn',
            'I': 'nnwnnwwnn', 'J': 'nnnnwwwnn', 'K': 'wnnnnnnww',
            'L': 'nnwnnnnww', 'M': 'wnwnnnnwn', 'N': 'nnnnwnnww',
            'O': 'wnnnwnnwn', 'P': 'nnwnwnnwn', 'Q': 'nnnnnnwww',
            'R': 'wnnnnnwwn', 'S': 'nnwnnnwwn', 'T': 'nnnnwnwwn',
            'U': 'wwnnnnnnw', 'V': 'nwwnnnnnw', 'W': 'wwwnnnnnn',
            'X': 'nwnnwnnnw', 'Y': 'wwnnwnnnn', 'Z': 'nwwnwnnnn',
            '-': 'nwnnnnwnw', '.': 'wwnnnnwnn', ' ': 'nwwnnnwnn',
            '*': 'nwnnwnwnn', '$': 'nwnwnwnnn', '/': 'nwnwnnnwn',
            '+': 'nwnnnwnwn', '%': 'nnnwnwnwn',
        }
        self.set_fill_color(0)
        for c in txt.upper():
            if c not in chars:
                raise RuntimeError('Invalid char "%s" for Code39' % c)
            for i, d in enumerate(chars[c]):
                if i % 2 == 0:
                    self.rect(x, y, dim[d], h, 'F')
                x += dim[d]
            x += dim['n']
