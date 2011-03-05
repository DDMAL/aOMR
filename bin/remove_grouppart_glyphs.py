#!/usr/bin/env python

#
# Script for removing _group_part.* glyphs from Gamera training data
#
# Usage:
#    python remove_grouppart_glyphs.py old.xml > new.xml
#
# Author:
#    Christian Brandt (2011)
#
# License:
#    Maybe freely used, copied and modified
#

import sys
filename = None
if len(sys.argv) > 1:
   filename = sys.argv[1]
else:
   sys.stderr.write("Usage: %s <input_filename>\n" % (sys.argv[0]))
   sys.exit(1)

f = open(filename)
lines = f.readlines()
f.close()
lastglyphline = -1
grouppart = False
todel = []
#print len(lines)
for i,line in enumerate(lines):
   if line.find("<glyph") >= 0:
      lastglyphline = i
#      print lastglyphline

   if line.find("_group._part") >= 0:
      grouppart = True
#      print grouppart

   if (line.find("</glyph") >= 0) and grouppart == True:
      for j in range(lastglyphline, i+1):
#         print lines[j]
         todel.append(j)
      grouppart = False
#      print lastglyphline, i, grouppart

##rint len(lines)

for i,j in enumerate(todel):
   lines.pop(j-i)


for l in lines:
   print l[:-1]