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
""" Standard plug-in to find data files.

"""

import os

from nuitka import Options
from nuitka.plugins.PluginBase import NuitkaPluginBase
from nuitka.utils.FileOperations import listDir

known_data_files = {
    # Key is the package name to trigger it
    # Value is a tuple of 2 element tuples, thus trailing commas, where
    # the target path can be specified (None is just default, i.e. the
    # package directory) and the filename relative to the source package
    # directory
    "site": ((None, "orig-prefix.txt"),),
    "nose.core": ((None, "usage.txt"),),
    "scrapy": ((None, "VERSION"),),
    "requests": (("certifi", "../certifi/cacert.pem"),),
    "importlib_resources": ((None, "version.txt"),),
    "boto": ((None, "./endpoints.json"),),
    "moto": (
        (None, "./ec2/resources/instance_types.json"),
        (None, "./ec2/resources/amis.json"),
    ),
}


def _createEmptyDirText(filename):
    # We create the same content all the time, pylint: disable=unused-argument
    return "This directory has to be present, even if otherwise empty.\n"


generated_data_files = {
    "Cryptodome.Util._raw_api": (
        ("Cryptodome/Util", ".keep_dir.txt", _createEmptyDirText),
    ),
    "Crypto.Util._raw_api": (("Crypto/Util", ".keep_dir.txt", _createEmptyDirText),),
}


class NuitkaPluginDataFileCollector(NuitkaPluginBase):
    plugin_name = "data-files"

    @staticmethod
    def isRelevant():
        return Options.isStandaloneMode()

    @staticmethod
    def isAlwaysEnabled():
        return True

    def considerDataFiles(self, module):
        module_name = module.getFullName()

        if module_name in known_data_files:
            for target_dir, filename in known_data_files[module_name]:
                source_path = os.path.join(module.getCompileTimeDirectory(), filename)

                if os.path.isfile(source_path):
                    if target_dir is None:
                        target_dir = module_name.replace(".", os.path.sep)

                    yield (
                        source_path,
                        os.path.normpath(os.path.join(target_dir, filename)),
                    )

        if module_name in generated_data_files:
            for target_dir, filename, func in generated_data_files[module_name]:
                if target_dir is None:
                    target_dir = module_name.replace(".", os.path.sep)

                yield (func, os.path.normpath(os.path.join(target_dir, filename)))

        if module_name == "lib2to3.pgen2":
            for source_path, filename in listDir(
                os.path.join(module.getCompileTimeDirectory(), "..")
            ):
                if not filename.endswith(".pickle"):
                    continue

                yield (source_path, os.path.normpath(os.path.join("lib2to3", filename)))
