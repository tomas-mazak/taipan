# -*- coding: UTF-8 -*-

import re
import subprocess
import platform
from distutils.core import setup, Extension

def pkg_config(package, option):
    sub = subprocess.Popen(["pkg-config",option,package],
                           stdout=subprocess.PIPE)
    spaces = re.compile('\s+',re.DOTALL)
    args = spaces.split(sub.stdout.read().strip())
    sub.stdout.close()
    sub.wait()
    return [a[2:] for a in args]

def get_macros():
    if platform.system() in ["Darwin", "Windows"]:
        return []
    else:
        return [("HAVE_MEMALIGN", None)]
 
wagomu_ext = Extension('_wagomu', ['wagomu.cpp',
                                  'wagomu.i'],
                       include_dirs = pkg_config('glib-2.0','--cflags'),
                       libraries = pkg_config('glib-2.0','--libs'),
                       define_macros=get_macros(),
                       library_dirs = pkg_config('glib-2.0','--libs'),
                       swig_opts=['-c++'])

setup(name='taipan',
      version='0.1',
      description='Chinese dictionary and learning tool',
      author='Tomas Mazak',
      author_email='tomas@valec.net',
      url='https://github.com/tomas-mazak/taipan',
      packages=['taipan', 'taipan.cjklib', 'taipan.cjklib.dictionary',
                'taipan.cjklib.reading', 'taipan.cjklib.build', 
                'taipan.tegaki', 'taipan.tegaki.engines', 'taipan.tegakigtk'],
      py_modules=['wagomu'],
      ext_modules=[wagomu_ext],
      scripts=['scripts/taipan'],
      package_data={'taipan': ['taipan.glade', 'cjklib.db', 'stroke.db'], 
                    'taipan.cjklib': ['cjklib.conf'],
                    'taipan.tegaki': ['models/wagomu/handwriting-zh_CN.*',
                                      'data/strokes/*']}
      )
