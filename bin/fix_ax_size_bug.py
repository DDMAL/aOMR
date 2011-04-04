# This file will go through and replace all the AXZ files with their
# hand-pre-processed originals.
from optparse import OptionParser
import lxml
import os
import zipfile
import time
import tempfile
import shutil
from PIL import Image
from lxml import etree

""" Manages the merge between Caylin's work, the new AXZ files with the 
    cropping and deskewing, and the redone set of AXZs with no cropping and 
    deskewing.
"""


if __name__ == "__main__":
    parser = OptionParser("ax_files_directory output_directory")
    (options, args) = parser.parse_args()
    
    
    for dirpath, dirnames, filenames in os.walk(args[0]):
        for fn in filenames:
            if fn is ".DS_Store":
                continue
            
            print "Processing {0}".format(fn)
            
            # open axz file
            c_tmpdir = tempfile.mkdtemp()
            c_zip = zipfile.ZipFile(os.path.join(dirpath, fn), 'r')
            for name in c_zip.namelist():
                f = open(os.path.join(c_tmpdir, name), 'wb')
                f.write(c_zip.read(name))
                f.close()
            c_zip.close()
            
            im0 = Image.open(os.path.join(c_tmpdir, 'img0.tif'))
            width, height = im0.size
            
            xmlf = open(os.path.join(c_tmpdir, 'index.xml'), 'r')
            t = etree.parse(xmlf)
            xmlf.close()
            
            impage=t.xpath("//impage")[0]
            impage.attrib['width'] = str(width)
            impage.attrib['height'] = str(height)
            
            t.write(os.path.join(c_tmpdir, "index.xml"))
            
            o_tmpdir = tempfile.mkdtemp()
            o_zip = zipfile.ZipFile(os.path.join(o_tmpdir, fn), 'w')
            for name in os.listdir(c_tmpdir):
                o_zip.write(os.path.join(c_tmpdir, name), name)
            o_zip.close()
            shutil.move(os.path.join(o_tmpdir, fn), os.path.join(args[1], fn))
            
            shutil.rmtree(c_tmpdir)
            shutil.rmtree(o_tmpdir)
            
            
    # filter the files that caylin has done so far.
    # caylins_files = [f for f in os.listdir(args[0]) if os.path.getmtime(os.path.join(args[0], f)) > time.mktime(time.strptime("08 Jan 2011", "%d %b %Y"))]
    # untouched_files = [f for f in os.listdir(args[0]) if f not in caylins_files]
    # redone_set = os.listdir(args[2])
    
    # print "Caylin's files: {0}".format(caylins_files)
    # print "Untouched files: {0}".format(untouched_files)
    # print "Redone set: {0}".format(redone_set)
    
    # for dirpath, dirnames, filenames in os.walk(args[1]):
    #     for fn in filenames:
    #         filenum = format(int(fn.split("__")[0]), '04d')
    #         newname = "liber-usualis-1961_Page_{0}.axz".format(filenum)
    #         
    #         if fn in caylins_files:
    #             if fn is ".DS_Store":
    #                 continue
    #             print "{0} is in Caylin's files".format(fn)
    #             # this file has been processed, so we need to swap the img0.tif
    #             # files.
    #             c_tmpdir = tempfile.mkdtemp()
    #             c_zip = zipfile.ZipFile(os.path.join(args[0], fn), 'r')
    #             for name in c_zip.namelist():
    #                 f = open(os.path.join(c_tmpdir, name), 'wb')
    #                 f.write(c_zip.read(name))
    #                 f.close()
    #             c_zip.close()
    #             
    #             n_tmpdir = tempfile.mkdtemp()
    #             n_zip = zipfile.ZipFile(os.path.join(args[1], fn), 'r')
    #             for name in n_zip.namelist():
    #                 f = open(os.path.join(n_tmpdir, name), 'wb')
    #                 f.write(n_zip.read(name))
    #                 f.close()
    #             n_zip.close()
    #             
    #             os.unlink(os.path.join(n_tmpdir, 'img0.tif'))
    #             shutil.move(os.path.join(c_tmpdir, "img0.tif"), os.path.join(n_tmpdir, "img0.tif"))
    #             
    #             o_tmpdir = tempfile.mkdtemp()
    #             # with zipfile.ZipFile(os.path.join(o_tmpdir, newname), 'w') as o_zip:
    #             #     for name in os.listdir(n_tmpdir):
    #             #         o_zip.write(os.path.join(n_tmpdir, name), name)
    #             o_zip = zipfile.ZipFile(os.path.join(o_tmpdir, newname), 'w')
    #             for name in os.listdir(n_tmpdir):
    #                 o_zip.write(os.path.join(n_tmpdir, name), name)
    #             o_zip.close()
    #             shutil.move(os.path.join(o_tmpdir, newname), os.path.join(args[3], newname))
    #             
    #             # clean up
    #             shutil.rmtree(c_tmpdir)
    #             shutil.rmtree(n_tmpdir)
    #             shutil.rmtree(o_tmpdir)
    #         else:
    #             print "{0} is not in Caylin's files".format(fn)
    #             # just copy over the newly-redone set of axz files.
    #             try:
    #                 shutil.copy(os.path.join(args[2], newname), os.path.join(args[3], newname))
    #             except Exception, e:
    #                 print " -----> Skipping {0} because {1}".format(fn, e)
    
    print "Done!"