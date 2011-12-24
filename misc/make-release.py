#!/usr/bin/env python
#
#     Copyright 2011, Kay Hayen, mailto:kayhayen@gmx.de
#
#     Part of "Nuitka", an optimizing Python compiler that is compatible and
#     integrates with CPython, but also works on its own.
#
#     If you submit Kay Hayen patches to this software in either form, you
#     automatically grant him a copyright assignment to the code, or in the
#     alternative a BSD license to the code, should your jurisdiction prevent
#     this. Obviously it won't affect code that comes to him indirectly or
#     code you don't submit to him.
#
#     This is to reserve my ability to re-license the code at any time, e.g.
#     the PSF. With this version of Nuitka, using it for Closed Source will
#     not be allowed.
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, version 3 of the License.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#     Please leave the whole of this copyright notice intact.
#

import os, sys, shutil, subprocess

assert os.path.isfile( "setup.py" ) and open( ".git/description" ).read().strip() == "Nuitka Staging"

branch_name = subprocess.check_output( "git name-rev --name-only HEAD".split() ).strip()

assert branch_name in ( b"master", b"develop" ), branch_name

shutil.rmtree( "dist", ignore_errors = True )
shutil.rmtree( "build", ignore_errors = True )

assert 0 == os.system( "python setup.py sdist --formats=bztar,gztar,zip" )

os.chdir( "dist" )

if os.path.exists( "deb_dist" ):
    shutil.rmtree( "deb_dist" )

assert 0 == os.system( "py2dsc *.tar.gz" )

os.chdir( "deb_dist" )

for entry in os.listdir( "." ):
    if os.path.isdir( entry ) and entry.startswith( "nuitka" ) and not entry.endswith( ".orig" ):
        break
else:
    assert False

assert 0 == os.system( "rsync -a ../../debian/ %s/debian/" % entry )

assert 0 == os.system( "rm *.dsc *.debian.tar.gz" )

os.chdir( entry )

# 1. Remove the inline copy of Scons. On Debian there is a dependency.
shutil.rmtree( "nuitka/build/inline_copy", False )

assert 0 == os.system( "EDITOR='true' dpkg-source --commit --include-removal . remove-inline-scons" )

assert 0 == os.system( "debuild" )

os.chdir( "../../.." )

assert os.path.isfile( "setup.py" ) and open( ".git/description" ).read().strip() == "Nuitka Staging"

assert 0 == os.system( "lintian --pedantic --fail-on-warnings dist/deb_dist/*.changes" )

os.system( "cp dist/deb_dist/*.deb dist/" )

assert os.path.exists( "dist/deb_dist" )

for filename in os.listdir( "dist/deb_dist" ):
    if os.path.isdir( "dist/deb_dist/" + filename ):
        shutil.rmtree( "dist/deb_dist/" + filename )

assert 0 == os.system( r"wine c:\\python27\\python.exe setup.py bdist_wininst --bitmap misc/Nuitka-Installer.bmp" )


for filename in os.listdir( "dist" ):
    if os.path.isfile( "dist/" + filename ):
        assert 0 == os.system( "chmod 644 dist/" + filename )
        assert 0 == os.system( "gpg --local-user 0BCF7396 --detach-sign dist/" + filename )

shutil.rmtree( "build", ignore_errors = True )
