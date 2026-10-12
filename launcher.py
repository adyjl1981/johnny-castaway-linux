#!/usr/bin/python3
import sys
if len(sys.argv) > 1 and sys.argv[1] == 'idle':
    sys.argv.pop(1)
    from johnny_castaway.idle import main
else:
    from johnny_castaway.gui import main
main()
