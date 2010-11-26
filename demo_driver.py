import sys
from curses_menu import CursesGuard, Menu

if __name__ == '__main__': # {{{
    if len(sys.argv) > 1:
        with file(sys.argv[1]) as f:
            l = f.readlines()
    else:
        with file('words6.txt') as f:
            l = sum([ x.split() for x in f.readlines() ],[])
    with CursesGuard() as window:
        m = Menu(window, l or ['abacus','binary','cipher'])
        while isinstance(m, Menu): m = m.run()
    print m
    # }}}
