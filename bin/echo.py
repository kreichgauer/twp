#!/usr/bin/env python
import time
from twp.echo import echo

t=echo.Transport('www.dcl.hpi.uni-potsdam.de', 80)
t.start()
while True:
	try:
		time.sleep(1)
	except KeyboardInterrupt:
		print("Shutting down...")
		t.stop()
		t.join()
		break
