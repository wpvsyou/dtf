# Android Device Testing Framework ("dtf")
# Copyright 2013-2015 Jake Valletta (@jake_valletta)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
""" dtf's package manager """

from dtf.module import Module
import dtf.globals
import dtf.logging as log
import dtf.core.packagemanager as packagemanager

from argparse import ArgumentParser
from lxml import etree

import os
import os.path
import tempfile
import zipfile

TAG = "pm"

DTF_DATA_DIR = dtf.globals.DTF_DATA_DIR
DTF_BINARIES_DIR = dtf.globals.DTF_BINARIES_DIR
DTF_LIBRARIES_DIR = dtf.globals.DTF_LIBRARIES_DIR
DTF_MODULES_DIR = dtf.globals.DTF_MODULES_DIR
DTF_PACKAGES_DIR = dtf.globals.DTF_PACKAGES_DIR
DTF_DB = dtf.globals.DTF_DB

TYPE_BINARY = packagemanager.TYPE_BINARY
TYPE_LIBRARY = packagemanager.TYPE_LIBRARY
TYPE_MODULE = packagemanager.TYPE_MODULE
TYPE_PACKAGE = packagemanager.TYPE_PACKAGE

# No log to file.
log.LOG_LEVEL_FILE = 0

class pm(Module):

    """Module class for dtf pm"""

    @classmethod
    def usage(cls):

        """Print Usage"""

        print "dtf Package Manager"
        print ""
        print "Subcommands:"
        print "    delete      Delete an item from main database."
        print "    export      Export entire main database to dtf ZIP."
        print "    install     Install a dtf ZIP or single item."
        print "    list        List all installed items."
        print "    purge       Purge all installed items, reset DB."
        print ""

    def do_install(self, args):

        """Attempt to install new content"""

        parser = ArgumentParser(prog='pm install',
                            description='Install a item or DTF ZIP of items.')
        parser.add_argument('--zip', dest='zipfile', default=None,
                            help='Install a DTF ZIP file containing items.')
        parser.add_argument('--single', metavar="ITEM", dest='single_type',
                            default=None, help='Install a single item.')
        parser.add_argument('--name', metavar="val", dest='single_name',
                            default=None, help="Item name [SINGLE ONLY].")
        parser.add_argument('--local_name', metavar="val",
                            dest='single_local_name', default=None,
                            help="Item local name [SINGLE ONLY].")
        parser.add_argument('--install_name', metavar="val",
                            dest='single_install_name', default=None,
                            help="Item install name [SINGLE ONLY].")
        parser.add_argument('--version', metavar="val", dest='single_version',
                            default=None,
                            help="Item version (#.# format) [SINGLE ONLY].")
        parser.add_argument('--author', nargs='+', metavar="val",
                            dest='single_author', default=None,
                            help="Item author (email is fine). [SINGLE ONLY].")
        parser.add_argument('--about', nargs='+', metavar="val",
                            dest='single_about', default=None,
                            help="About string for a module. [SINGLE ONLY].")
        parser.add_argument('--health', metavar="val", dest='single_health',
                            default=None, help="Item health [SINGLE ONLY].")
        parser.add_argument('--auto', dest='single_auto', action='store_const',
                            const=True, default=False,
                            help="Automatically parse module [SINGLE ONLY].")
        parser.add_argument('--force', dest='force', action='store_const',
                            const=True, default=False,
                            help="Force installation of component(s).")

        parsed_args = parser.parse_args(args)

        zip_file_name = parsed_args.zipfile
        single_type = parsed_args.single_type
        force_mode = parsed_args.force

        if zip_file_name is not None and single_type is not None:
            log.e(TAG, "Cannot install both DTF ZIP and single item. Exiting.")
            return -1

        if zip_file_name is None and single_type is None:
            log.e(TAG, "ZIP mode or single item mode not detected. Exiting.")
            return -2

        # Install zip.
        if zip_file_name is not None:
            if zipfile.is_zipfile(zip_file_name):
                return packagemanager.install_zip(zip_file_name,
                                                  force=force_mode)

            else:
                log.e(TAG, "'%s' is not a valid ZIP file or does not exist."
                        % (zip_file_name))
                return -3

        # Install single.
        else:
            # Check for auto-mode:
            if parsed_args.single_auto:
                # Only modules can be auto-parsed
                if single_type == TYPE_MODULE:
                    log.i(TAG, "Attempting to auto parse...")

                    item = self.auto_parse_module(parsed_args)
                    if item is None:
                        log.e(TAG, "Error autoparsing module!")
                        return -9
                else:
                    log.e(TAG, "Autoparse is only available for modules!")
                    return -4
            # Not auto
            else:
                item = self.parse_single_item(parsed_args)
                if item is None:
                    log.e(TAG, "Error parsing single item!")
                    return -5

            # Now do the installation.
            if single_type == TYPE_BINARY:
                return packagemanager.install_single_binary(item,
                                                            force=force_mode)
            elif single_type == TYPE_LIBRARY:
                return packagemanager.install_single_library(item,
                                                            force=force_mode)
            elif single_type == TYPE_MODULE:
                return packagemanager.install_single_module(item,
                                                            force=force_mode)
            elif single_type == TYPE_PACKAGE:
                return packagemanager.install_single_package(item,
                                                            force=force_mode)

    def do_delete(self, args):

        """Attempt to remove content"""

        parser = ArgumentParser(prog='pm delete',
                            description='Remove a item from disk and database.')
        parser.add_argument('--type', metavar="val", dest='item_type',
                            default=None, help='The type of the item')
        parser.add_argument('--name', metavar="val", dest='item_name',
                            default=None, help="Item to uninstall.")
        parser.add_argument('--force', dest='force', action='store_const',
                            const=True, default=False,
                            help="Force deletion of component.")

        parsed_args = parser.parse_args(args)

        force_mode = parsed_args.force

        name = parsed_args.item_name
        if name is None:
            log.e(TAG, "'--name' is required for delete mode. Exiting.")
            return -1

        item_type = parsed_args.item_type

        if item_type == TYPE_BINARY:
            rtn = packagemanager.delete_binary(name, force=force_mode)
        elif item_type == TYPE_LIBRARY:
            rtn = packagemanager.delete_library(name, force=force_mode)
        elif item_type == TYPE_MODULE:
            rtn = packagemanager.delete_module(name, force=force_mode)
        elif item_type == TYPE_PACKAGE:
            rtn = packagemanager.delete_package(name, force=force_mode)
        else:
            log.e(TAG, "Invalid type passed to delete. Exiting.")
            rtn = -2

        return rtn

    def do_export(self, args):

        """Perform an export"""

        rtn = 0

        parser = ArgumentParser(prog='pm export',
                                description='Export installed content.')
        parser.add_argument('output_name', type=str,
                                help='The output file name.')

        parsed_args = parser.parse_args(args)

        output_name = parsed_args.output_name

        if os.path.isfile(output_name):
            log.e(TAG, "Output file already exists!")
            return -1

        # Generate a list of populated items.
        export_items = self.generate_export_items()

        if len(export_items) == 0:
            log.e(TAG, "Nothing to export!")
            return -2

        output_zip = zipfile.ZipFile(output_name, 'w',
                                     compression=zipfile.ZIP_DEFLATED)

        # Generate the XML
        export_manifest = tempfile.NamedTemporaryFile()

        rtn = self.generate_export_xml(export_items, export_manifest)
        if rtn != 0:
            log.e(TAG, "Unable to generate export manifest!")
            output_zip.close()
            return rtn

        # Add the manifest
        output_zip.write(export_manifest.name, packagemanager.MANIFEST_NAME)

        export_manifest.close()

        # Finally, add the content
        rtn = self.add_export_content(export_items, output_zip)
        if rtn != 0:
            log.e(TAG, "Unable to add content to the export ZIP!")
            output_zip.close()
            return rtn

        output_zip.close()

        log.i(TAG, "Export completed!")

        return rtn

    def do_list(self, args):

        """List installed content"""

        rtn = 0

        parser = ArgumentParser(prog='pm list',
                                  description='List installed components.')
        parser.add_argument('-v', dest='verbose', action='store_const',
                                  const=True, default=False,
                                  help="Force deletion of component.")
        parser.add_argument('d_filter', type=str, nargs='?',
                                  help='An optional filter.')

        parsed_args = parser.parse_args(args)

        d_filter = parsed_args.d_filter
        verbose = parsed_args.verbose

        if d_filter is not None:

            if d_filter == "binaries":
                self.print_installed_binaries(verbose)
            elif d_filter == "libraries":
                self.print_installed_libraries(verbose)
            elif d_filter == "modules":
                self.print_installed_modules(verbose)
            elif d_filter == "packages":
                self.print_installed_packages(verbose)
            else:
                log.e(TAG, "Unknown filter specified : %s" % d_filter)
                rtn = -3

        else:
            self.print_installed_binaries(verbose)
            self.print_installed_libraries(verbose)
            self.print_installed_modules(verbose)
            self.print_installed_packages(verbose)

        return rtn

    def do_purge(self):

        """Purge dtf DB"""

        print "!!!! WARNING !!!!"
        print ""
        print "This will delete all content, and reset the database!!"
        print "Are you sure you want to do this? [N/y]",

        res = raw_input()

        if res.lower() == "y":
            return packagemanager.purge()
        else:
            return 0

    @classmethod
    def format_version(cls, minor, major):

        """Format version of item"""

        if minor is None and major is None:
            return "No Version"

        else:
            major_version = major
            minor_version = minor

            if major is None:
                major_version = "0"
            if minor is None:
                minor_version = "0"

            return "v%s.%s" % (major_version, minor_version)

    def add_export_content(self, export_items, export_zip):

        """Add content to our ZIP file"""

        for item in export_items:
            if item.type == TYPE_LIBRARY or item.type == TYPE_PACKAGE:

                for root, dirs, files in os.walk(item.install_name):

                    for dir_name in dirs:
                        file_path = os.path.join(root, dir_name)
                        rel_path = os.path.relpath(os.path.join(root, dir_name),
                                                   item.install_name)
                        zip_path = os.path.join(item.local_name, rel_path)

                        log.d(TAG, "Adding dir '%s' as '%s'"
                                % (file_path, zip_path))

                        export_zip.write(file_path, zip_path)

                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        rel_path = os.path.relpath(
                                            os.path.join(root, file_name),
                                            item.install_name)
                        zip_path = os.path.join(item.local_name, rel_path)

                        log.d(TAG, "Adding '%s' as '%s'"
                                % (file_path, zip_path))

                        export_zip.write(file_path, zip_path)
            else:
                log.d(TAG, "Adding '%s' as '%s'"
                        % (item.install_name, item.local_name))

                export_zip.write(item.install_name, item.local_name)

        return 0

    def generate_export_xml(self, export_items, manifest_f):

        """Create and populate manifest"""

        rtn = 0
        root = etree.Element('Items')

        # Add binaries
        bin_items = [item for item in export_items
                        if item.type == TYPE_BINARY]

        for item in bin_items:

            item_xml = etree.SubElement(root, 'Item')
            item_xml.attrib['type'] = TYPE_BINARY
            item_xml.attrib['name'] = item.name
            item_xml.attrib['majorVersion'] = item.major_version
            item_xml.attrib['minorVersion'] = item.minor_version
            item_xml.attrib['health'] = item.health
            item_xml.attrib['author'] = item.author
            item_xml.attrib['localName'] = item.local_name

        # Add libraries
        lib_items = [item for item in export_items
                        if item.type == TYPE_LIBRARY]

        for item in lib_items:

            item_xml = etree.SubElement(root, 'Item')
            item_xml.attrib['type'] = TYPE_LIBRARY
            item_xml.attrib['name'] = item.name
            item_xml.attrib['majorVersion'] = item.major_version
            item_xml.attrib['minorVersion'] = item.minor_version
            item_xml.attrib['health'] = item.health
            item_xml.attrib['author'] = item.author
            item_xml.attrib['localName'] = item.local_name

        # Add modules
        mod_items = [item for item in export_items
                        if item.type == TYPE_MODULE]

        for item in mod_items:

            item_xml = etree.SubElement(root, 'Item')
            item_xml.attrib['type'] = TYPE_MODULE
            item_xml.attrib['name'] = item.name
            item_xml.attrib['majorVersion'] = item.major_version
            item_xml.attrib['minorVersion'] = item.minor_version
            item_xml.attrib['health'] = item.health
            item_xml.attrib['about'] = item.about
            item_xml.attrib['author'] = item.author
            item_xml.attrib['localName'] = item.local_name

        # Add packages
        pkg_items = [item for item in export_items
                        if item.type == TYPE_PACKAGE]

        for item in pkg_items:

            item_xml = etree.SubElement(root, 'Item')
            item_xml.attrib['type'] = TYPE_PACKAGE
            item_xml.attrib['name'] = item.name
            item_xml.attrib['majorVersion'] = item.major_version
            item_xml.attrib['minorVersion'] = item.minor_version
            item_xml.attrib['health'] = item.health
            item_xml.attrib['author'] = item.author
            item_xml.attrib['localName'] = item.local_name

        # Write it all out
        export_tree = etree.ElementTree(root)
        export_tree.write(manifest_f, pretty_print=True)
        manifest_f.flush()

        return rtn

    def generate_export_items(self):

        """Create a list of items"""

        items = list()

        # Get all binaries
        for binary in packagemanager.get_binaries():

            binary.local_name = "binaries/%s" % binary.name
            binary.install_name = "%s/%s" % (DTF_BINARIES_DIR, binary.name)
            items.append(binary)

        # Get all libraries
        for library in packagemanager.get_libraries():

            library.local_name = "libraries/%s" % library.name
            library.install_name = "%s/%s" % (DTF_LIBRARIES_DIR, library.name)
            items.append(library)

        # Get all modules
        for module in packagemanager.get_modules():

            module.local_name = "modules/%s" % module.name
            module.install_name = "%s/%s" % (DTF_MODULES_DIR, module.name)
            items.append(module)

        # Get all packages
        for package in packagemanager.get_packages():

            package.local_name = "packages/%s" % package.name
            package.install_name = "%s/%s" % (DTF_PACKAGES_DIR, package.name)
            items.append(package)

        return items

    def print_installed_binaries(self, verbose):

        """Print installed binaries"""

        print "Installed Binaries"

        for binary in packagemanager.get_binaries():

            # Format version
            version = self.format_version(binary.minor_version,
                                          binary.major_version)

            print "\t%s (%s)" % (binary.name, version)
            if verbose:
                print "\t   About: %s" % binary.about
                print "\t   Author: %s" % binary.author
                print "\t   Health: %s" % binary.health

        return 0

    def print_installed_libraries(self, verbose):

        """Print installed libraries"""

        print "Installed Libraries"

        for library in packagemanager.get_libraries():

            # Format version
            version = self.format_version(library.minor_version,
                                          library.major_version)

            print "\t%s (%s)" % (library.name, version)
            if verbose:
                print "\t   About: %s" % library.about
                print "\t   Author: %s" % library.author
                print "\t   Health: %s" % library.health

        return 0

    def print_installed_modules(self, verbose):

        """Print installed modules"""

        print "Installed Modules"

        for module in packagemanager.get_modules():

            # Format version
            version = self.format_version(module.minor_version,
                                          module.major_version)

            print "\t%s (%s)" % (module.name, version)
            if verbose:
                print "\t   About: %s" % module.about
                print "\t   Author: %s" % module.author
                print "\t   Health: %s" % module.health

        return 0

    def print_installed_packages(self, verbose):

        """Print installed packages"""

        print "Installed Packages"

        for package in packagemanager.get_packages():

            # Format version
            version = self.format_version(package.minor_version,
                                          package.major_version)

            print "\t%s (%s)" % (package.name, version)
            if verbose:
                print "\t   About: %s" % package.about
                print "\t   Author: %s" % package.author
                print "\t   Health: %s" % package.health

        return 0

    def auto_parse_module(self, args):

        """Automatically parse module and return Item"""

        item = None
        name = args.single_name
        install_name = args.single_install_name
        local_name = args.single_local_name

        if install_name is None:
            log.d(TAG, "install_name is null, using name...")
            install_name = name
        if local_name is None:
            log.d(TAG, "local_name is null, using name...")
            local_name = name

        # Does the resource even exist?
        if not os.path.isfile(local_name):
            log.e(TAG, "Local module resource '%s' does not exist!"
                    % (local_name))
            return None

        if packagemanager.is_python_module(local_name, install_name):
            log.d(TAG, "Python mode selected")

            item = packagemanager.parse_python_module(local_name,
                                                      install_name)
            if item is None:
                log.e(TAG, "Error parsing Python module!")
                return None

        elif packagemanager.is_bash_module(local_name):
            log.d(TAG, "Bash mode selected")

            item = packagemanager.parse_bash_module(local_name,
                                                    install_name)
            if item is None:
                log.e(TAG, "Error parsing Bash module!")
                return None

        else:
            log.e(TAG, "Auto parse for Python and Bash failed!")
            return None

        return item

    def parse_single_item(self, args):

        """Parse args, return Item"""

        item = packagemanager.Item()

        name = args.single_name
        if name is None:
            log.e(TAG, "No '--name' specified in single item mode. Exiting.")
            return None

        item.name = name

        single_type = args.single_type
        if single_type not in packagemanager.VALID_TYPES:
            log.e(TAG, "Invalid type passed to single. Exiting.")
            return None

        item.type = single_type

        health = args.single_health
        if health not in packagemanager.VALID_HEALTH_VALUES:
            log.e(TAG, "Invalid health specified. Exiting.")
            return None

        item.health = health

        version = args.single_version
        if version is not None:
            try:
                (item.major_version, item.minor_version) = version.split('.')
            except ValueError:
                log.e(TAG, "Version string is not valid. Exiting.")
                return None
        else:
            item.major_version = None
            item.minor_version = None

        try:
            item.author = " ".join(args.single_author)
        except TypeError:
            item.author = None

        try:
            item.about = " ".join(args.single_about)
        except TypeError:
            item.about = None

        install_name = args.single_install_name
        local_name = args.single_local_name

        if install_name is None:
            log.d(TAG, "install_name is null, using name...")
            install_name = name
        if local_name is None:
            log.d(TAG, "local_name is null, using name...")
            local_name = name

        item.install_name = install_name
        item.local_name = local_name

        if item.type == TYPE_BINARY:
            if not os.path.isfile(item.local_name):
                log.e(TAG, "Local item '%s' does not exist. Exiting."
                        % (item.local_name))
                return None
        elif item.type == TYPE_LIBRARY:
            if not os.path.isdir(item.local_name):
                log.e(TAG, "Local directory '%s' does not exist. Exiting."
                        % (item.local_name))
                return None
        elif item.type == TYPE_MODULE:
            if not os.path.isfile(item.local_name):
                log.e(TAG, "Local item '%s' does not exist. Exiting."
                        % (item.local_name))
                return None
        elif item.type == TYPE_PACKAGE:
            if not os.path.isdir(item.local_name):
                log.e(TAG, "Local directory '%s' does not exist. Exiting."
                        % (item.local_name))
                return None

        return item

    def execute(self, args):

        """Main module executor"""

        self.name = self.__self__

        rtn = 0

        # Set things up if they haven't been already
        if packagemanager.create_data_dirs() != 0:
            log.e(TAG, "Unable to setup dtf data directories!")
            return -4

        if not os.path.isfile(DTF_DB):
            if packagemanager.initialize_db() != 0:
                log.e(TAG, "Error creating and populating dtf db!!")
                return -7

        if len(args) < 1:
            return self.usage()

        sub_cmd = args.pop(0)

        if sub_cmd == "install":
            rtn = self.do_install(args)
        elif sub_cmd == "delete":
            rtn = self.do_delete(args)
        elif sub_cmd == "export":
            rtn = self.do_export(args)
        elif sub_cmd == "list":
            rtn = self.do_list(args)
        elif sub_cmd == "purge":
            rtn = self.do_purge()
        else:
            log.e(TAG, "Sub-command '%s' not found!" % sub_cmd)
            rtn = self.usage()

        return rtn
