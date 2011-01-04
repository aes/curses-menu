#!/usr/bin/env python
# {{{ head comment
"""
dirt is an interactive curses user interface for changing directory in shells.

It's nice, but there are a lot things that need to be done.

Put the contents of dirt.sh in your .bashrc, or just source it.
"""
# }}}

import curses as C

def u8(s):
    if not isinstance(s, unicode): s = unicode(s, 'utf-8', 'replace')
    return s.encode('utf-8')

def levenshtein(a,b): # {{{
    "Calculates the Levenshtein distance between a and b."
    n, m = len(a), len(b)
    if n > m: a,b, n,m = b,a, m,n
    cur = range(n+1)
    for i in range(1,m+1):
        prev, cur = cur, [i]+[0]*n
        for j in range(1,n+1):
            add,rem,chg = prev[j]+1, cur[j-1]+1, prev[j-1]+int(a[j-1]!=b[i-1])
            cur[j] = min(add, rem, chg)
    return cur[n]
    # }}}

def dist(a, b):
    a, b = a.lower(), b.lower()
    d = levenshtein(a, b) - len(b)
    if a in b:  d -= len(a) + b.find(a) / len(b)
    return d

class Pad(object): # {{{
    cc   = [ C.A_NORMAL, C.A_REVERSE ]
    __slots__ = ['menu','pad','dim','_s']
    #
    sel = property(lambda self: self.menu.s)
    win = property(lambda self: self.menu.w)
    #
    def __init__(self, menu):
        self.menu = menu
        self.repop()
    def __len__(self): return self.dim[0]
    def repop(self):
        m = self.menu
        self.dim = (len(m)+1, max(2, m.max_width())+1)
        self.pad = p = C.newpad(*self.dim)
        self._s = s = self.sel
        #
        for i in range((len(m))):
            p.addstr(i, 0, str(m[i]), self.cc[i==s])
    def update(self, win=None):
        if len(self) != len(self.menu): self.repop()
        win = win or self.win
        l, p, s, _s, z = self.menu, self.pad, self.sel, self._s, self.dim
        p.addstr(_s, 0, str(l[_s]), self.cc[0])
        p.addstr(s,  0, str(l[s ]), self.cc[1])
        self._s = s
        y, x = win.getmaxyx()
        if y < 2 or x < 4: raise RuntimeError
        q = min((max(s - y/2, 0)), len(l)-y+1)
        ys, xs = self.dim
        yp = min(y-1, ys-1-q)
        xp = min(x-1, xs-1)
        p.overlay(win, q,0, 1,1, yp, xp)
    # }}}

class Menu(object): # {{{
    # {{{
    def _prev(o):     o.s = max(           0, o.s - 1)
    def _next(o):     o.s = min(len(o.l) - 1, o.s + 1)
    def _pgup(o):     o.s = max(           0, o.s - o.page)
    def _pgdn(o):     o.s = min(len(o.l) - 1, o.s + o.page)
    def _first(o):    o.s = 0
    def _last(o):     o.s = len(o.l) - 1
    def _del(o):      o.l, o.s = o.l[:o.s]+o.l[o.s+1:], min(len(o.l) - 2, o.s)
    def _done(o, *a): raise StopIteration, a
    def _srch(o):     return InteractiveMenu(o)
    # }}}
    # {{{
    QUIT = []
    page = 10
    cc   = [ C.A_NORMAL, C.A_REVERSE ]
    m = { C.KEY_UP:     _prev,
          C.KEY_DOWN:   _next,
          C.KEY_PPAGE:  _pgup,
          C.KEY_NPAGE:  _pgdn,
          C.KEY_HOME:   _first,
          C.KEY_END:    _last,
          ord("\n"):    lambda o: o.l[o.s],
          ord("\r"):    lambda o: o.l[o.s],
          ord('/'):     _srch,
          ord('_'):     _srch,
          ord('q'):     _done,
          27:           _done,
    } # }}}
    def __init__(self, w, l, s=0, **extra): # {{{
        self.w = w
        self.l = l
        self.s = s
        self.extra = extra
        c = self.__class__
        self.t = extra.get('title',  c.__name__.replace('Menu',''))
        self.m = extra.get('keymap', c.m)
        # }}}
    def __len__(self):        return len(self.l)
    def __getitem__(self, i): return self.l[i]
    def max_width(self):      return max([len(x) for x in self.l])
    def input(self, c):       return self.m.get(c)
    def update(self):
        w = self.w
        w.clear()
        self._p.update(w)
        w.addstr(0, 1, self.t, C.A_BOLD)
        w.refresh()
    def run(self):
        self._p = Pad(self)
        while True:
            self.update()
            try:                      c = self.w.getch()
            except KeyboardInterrupt: c = 27
            f = self.input(c)
            if callable(f):
                c = f(self)
                if c: return c != Menu.QUIT and c or None
    # }}}

class InteractiveMenu(Menu): # {{{
    def _bs(o):
        if not o.q: return o.ctx
        o.q = o.q[:-1]
        o._redo()
    m = dict(Menu.m.items() + {
            C.KEY_BACKSPACE: _bs,
            C.KEY_LEFT:      lambda o: o.ctx,
            27:              lambda o: o.ctx,
        }.items())
    def __init__(self, ctx, dist=dist):
        self.dist, self.ctx, self.q = dist, ctx, ''
        super(InteractiveMenu, self).__init__(ctx.w, ctx.l[:])
    def _redo(self):
        q = self.q
        m = [ (self.dist(q, y), y) for y in self.l ]
        m.sort()
        l = []
        for i, x in enumerate(m):
            if i % 2:  l = [x]+l
            else:      l = l+[x]
        self.t = '/'+self.q+' '
        self.s, self.l = len(l)/2, [ y for x, y in l ]
    def input(self, c):
        if not (31 < c < 127): return self.m.get(c) or self.ctx.input(c)
        self.q += chr(c)
        self._redo()
    # }}}


def wrap(f): # {{{
    try:
        import locale
        locale.setlocale(locale.LC_ALL, '')
        code = locale.getpreferredencoding()

        stdscr = C.initscr(); C.noecho(); C.cbreak()
        stdscr.keypad(1)
        C.curs_set(0)

        ret = f(stdscr)

    except Exception:
        ret = None

    C.curs_set(1); C.nocbreak(); stdscr.keypad(0); C.echo(); C.endwin()
    return ret
    # }}}

class CursesGuard: # {{{
    def __enter__(self):
        import locale
        locale.setlocale(locale.LC_ALL, '')
        code = locale.getpreferredencoding()

        self.stdscr = C.initscr()
        C.noecho()
        C.cbreak()
        self.stdscr.keypad(1)
        C.curs_set(0)
        return self.stdscr
    def __exit__(self, type, value, traceback):
        C.curs_set(1);
        C.nocbreak();
        self.stdscr.keypad(0);
        C.echo();
        C.endwin()
        False
    # }}}

