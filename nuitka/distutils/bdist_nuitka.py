#     Copyright 2019, Kay Hayen, mailto:kay.hayen@gmail.com
#
#     Part of "Nuitka", an optimizing Python compiler that is compatible and
#     integrates with CPython, but also works on its own.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
""" Nuitka distutils integration.

"""

import distutils.command.build  # @UnresolvedImport pylint: disable=I0021,import-error,no-name-in-module
import distutils.command.install  # @UnresolvedImport pylint: disable=I0021,import-error,no-name-in-module
import os
import subprocess
import sys

import wheel.bdist_wheel  # @UnresolvedImport pylint: disable=I0021,import-error,no-name-in-module


def setuptools_build_hook(dist, keyword, value):
    # If the user project setup.py includes the key "build_with_nuitka=True" all
    # build operations (build, bdist_wheel, install etc) will run via Nuitka.
    # pylint: disable=unused-argument

    if not value:
        return

    dist.cmdclass = dist.cmdclass or {}  # Ensure is a dict
    dist.cmdclass["build"] = build
    dist.cmdclass["install"] = install
    dist.cmdclass["bdist_wheel"] = bdist_nuitka


# Class name enforced by distutils, must match the command name.
# pylint: disable=C0103
class build(distutils.command.build.build):

    # pylint: disable=attribute-defined-outside-init
    def run(self):
        self.compile_packages = self.distribution.packages or ()
        self.py_modules = self.distribution.py_modules or ()

        if not self.compile_packages and not self.py_modules:
            sys.exit("Missing both compile_packages and py_modules, aborting...")

        # Python2 does not allow super on this old style class.
        distutils.command.build.build.run(self)

        self._build(os.path.abspath(self.build_lib))

    def _build(self, build_lib):
        # High complexity, pylint: disable=too-many-locals

        # Nuitka wants the main package by filename, probably we should stop
        # needing that.
        from nuitka.importing.Importing import findModule, setMainScriptDirectory
        from nuitka.utils.ModuleNames import ModuleName
        from nuitka.__past__ import (  # pylint: disable=I0021,redefined-builtin
            Iterable,
            unicode,
        )

        old_dir = os.getcwd()
        os.chdir(build_lib)

        # Search in the build directory preferably.
        setMainScriptDirectory(".")

        package, main_filename, finding = findModule(
            importing=None,
            module_name=ModuleName(
                self.compile_packages[0]
                if self.compile_packages
                else self.py_modules[0]
            ),
            parent_package=None,
            level=0,
            warn=False,
        )

        # Check expectations, e.g. do not compile built-in modules.
        assert finding == "absolute", finding

        if package is not None:
            output_dir = os.path.join(build_lib, package)
        else:
            output_dir = build_lib

        command = [
            sys.executable,
            "-m",
            "nuitka",
            "--module",
            "--plugin-enable=pylint-warnings",
            "--output-dir=%s" % output_dir,
            "--nofollow-import-to=*.tests",
            "--show-modules",
            "--remove-output",
        ]

        command += [
            "--include-package=%s" % package_name
            for package_name in self.compile_packages
        ]

        command += [
            "--include-module=%s" % module_name for module_name in self.py_modules
        ]

        # Process any extra options from setuptools
        if "nuitka" in self.distribution.command_options:
            for option, value in self.distribution.command_options["nuitka"].items():
                option = "--" + option.lstrip("-")
                if value is None:
                    command.append(option)
                elif isinstance(value, bool):
                    option = "--" + ("no" if not value else "") + option.lstrip("-")
                    command.append(option)
                elif isinstance(value, Iterable) and not isinstance(
                    value, (unicode, bytes, str)
                ):
                    for val in value:
                        command.append("%s=%s" % (option, val))
                else:
                    command.append("%s=%s" % (option, value))

        command.append(main_filename)

        subprocess.check_call(command, cwd=build_lib)

        for root, _, filenames in os.walk(build_lib):
            for filename in filenames:
                fullpath = os.path.join(root, filename)

                if fullpath.lower().endswith((".py", ".pyw", ".pyc", ".pyo")):
                    os.unlink(fullpath)

        os.chdir(old_dir)

        self.build_lib = build_lib


# pylint: disable=C0103
class install(distutils.command.install.install):

    # pylint: disable=attribute-defined-outside-init
    def finalize_options(self):
        distutils.command.install.install.finalize_options(self)
        # Ensure the purelib folder is not used
        self.install_lib = self.install_platlib


# pylint: disable=C0103
class bdist_nuitka(wheel.bdist_wheel.bdist_wheel):
    def initialize_options(self):
        # Register the command class overrides above
        dist = self.distribution
        dist.cmdclass = dist.cmdclass or {}  # Ensure is a dict
        dist.cmdclass["build"] = build
        dist.cmdclass["install"] = install

        wheel.bdist_wheel.bdist_wheel.initialize_options(self)

    # pylint: disable=attribute-defined-outside-init
    def finalize_options(self):
        wheel.bdist_wheel.bdist_wheel.finalize_options(self)
        # Force module to use correct platform in name
        self.root_is_pure = False
        self.plat_name_supplied = self.plat_name is not None

    def write_wheelfile(self, wheelfile_base, generator=None):
        if generator is None:
            from nuitka.Version import getNuitkaVersion

            generator = "Nuitka (%s)" % getNuitkaVersion()

        wheel.bdist_wheel.bdist_wheel.write_wheelfile(
            self, wheelfile_base=wheelfile_base, generator=generator
        )
