# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import os
import logging
import time
import string

from . import Utils
from .polib import polib

SETTINGS_FILE = 'kodidevkit.sublime-settings'


class Addon(object):
    LANG_START_ID = 32000
    LANG_OFFSET = 2

    def __init__(self, *args, **kwargs):
        self.type = "python"
        self.po_files = []
        self.colors = []
        self.color_labels = set()
        self.fonts = {}
        self.xml_folders = []
        self.window_files = {}
        self.include_files = {}
        self.font_file = None
        self.includes = {}
        self.settings = kwargs.get("settings")
        self.path = kwargs.get("project_path")
        self.xml_file = os.path.join(self.path, "addon.xml")
        self.root = Utils.get_root_from_file(self.xml_file)
        self.kodi_version = self.root.find(".//import[@addon='xbmc.python']")
        self.version = self.root.attrib.get("version")
        for item in self.root.xpath("/addon[@id]"):
            self.name = item.attrib["id"]
            break
        self.load_xml_folders()
        self.update_xml_files()
        self.update_labels()

    def load_xml_folders(self):
        """
        find and load skin xml folder if existing
        """
        paths = [os.path.join(self.path, "resources", "skins", "Default", "720p"),
                 os.path.join(self.path, "resources", "skins", "Default", "1080i")]
        folder = Utils.check_paths(paths)
        self.xml_folders.append(folder)

    @property
    def lang_path(self):
        """
        returns the add-on language folder path
        """
        return os.path.join(self.path, "resources", "language")

    @property
    def changelog_path(self):
        """
        returns the add-on language folder path
        """
        return os.path.join(self.path, "changelog.txt")

    @property
    def primary_lang_folder(self):
        """
        returns default language folder (first one from settings file)
        """
        lang_folder = self.settings.get("language_folders")[0]
        lang_path = os.path.join(self.path, "resources", "language", lang_folder)
        if not os.path.exists(lang_path):
            os.makedirs(lang_path)
        return lang_path

    @property
    def media_path(self):
        """
        returns the add-on media folder path
        """
        return os.path.join(self.path, "resources", "skins", "Default", "media")

    @staticmethod
    def by_project(project_path, settings):
        """
        factory, return proper instance based on addon.xml
        """
        xml_file = os.path.join(project_path, "addon.xml")
        root = Utils.get_root_from_file(xml_file)
        if root.find(".//import[@addon='xbmc.python']") is None:
            from . import skin
            return skin.Skin(project_path=project_path,
                             settings=settings)
        else:
            return Addon(project_path=project_path,
                         settings=settings)
            # TODO: parse all python skin folders correctly

    def update_labels(self):
        """
        get addon po files and update po files list
        """
        self.po_files = self.get_po_files(self.lang_path)

    def get_po_files(self, lang_folder_root):
        """
        get list with pofile objects
        """
        po_files = []
        for item in self.settings.get("language_folders"):
            path = Utils.check_paths([os.path.join(lang_folder_root, item, "strings.po"),
                                      os.path.join(lang_folder_root, item, "resources", "strings.po")])
            if path:
                po_file = Utils.get_po_file(path)
                po_file.language = item
                po_files.append(po_file)
        return po_files

    def update_xml_files(self):
        """
        update list of all include and window xmls
        """
        self.window_files = {}
        for path in self.xml_folders:
            xml_folder = os.path.join(self.path, path)
            self.window_files[path] = []
            if not os.path.exists(xml_folder):
                return []
            for xml_file in os.listdir(xml_folder):
                filename = os.path.basename(xml_file)
                if not filename.endswith(".xml"):
                    continue
                if filename.lower() not in ["font.xml"]:
                    self.window_files[path].append(xml_file)
            logging.info("found %i XMLs in %s" % (len(self.window_files[path]), xml_folder))

    def create_new_po_file(self):
        """
        creates a new pofile and returns it (doesnt save yet)
        """
        po = polib.POFile()
        mail = ""
        actual_date = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        po.metadata = {
            'Project-Id-Version': '1.0',
            'Report-Msgid-Bugs-To': '%s' % mail,
            'POT-Creation-Date': actual_date,
            'PO-Revision-Date': actual_date,
            'Last-Translator': 'you <%s>' % mail,
            'Language-Team': 'English <%s>' % mail,
            'MIME-Version': '1.0',
            'Content-Type': 'text/plain; charset=utf-8',
            'Content-Transfer-Encoding': '8bit',
        }
        return po

    def create_new_label(self, word, filepath):
        """
        adds a label to the first pofile from settings (or creates new one if non-existing)
        """
        if not self.po_files:
            po = self.create_new_po_file()
            lang_folder = self.settings.get("language_folders")[0]
            if self.type == "skin":
                lang_path = os.path.join(self.path, "language", lang_folder)
            else:
                lang_path = os.path.join(self.path, "resources", "language", lang_folder)
            if not os.path.exists(lang_path):
                os.makedirs(lang_path)
            po.save(os.path.join(lang_path, "strings.po"))
            self.po_files.append(po)
            logging.critical("New language file created")
        else:
            po = self.po_files[0]
        string_ids = []
        for entry in po:
            try:
                string_ids.append(int(entry.msgctxt[1:]))
            except Exception:
                string_ids.append(entry.msgctxt)
        for label_id in range(self.LANG_START_ID, self.LANG_START_ID + 1000):
            if label_id not in string_ids:
                logging.info("first free: " + str(label_id))
                break
        entry = polib.POEntry(msgid=word,
                              msgstr="",
                              msgctxt="#%s" % label_id,
                              occurrences=[(filepath, None)])
        po.insert(index=int(label_id) - self.LANG_START_ID + self.LANG_OFFSET,
                  entry=entry)
        po.save(self.po_files[0].fpath)
        self.update_labels()
        return label_id

    def attach_occurrence_to_label(self, label_id, rel_path):
        if 31000 <= int(label_id[1:]) < 33000:
            entry = self.po_files[0].find(label_id, by="msgctxt")
            entry.occurrences.append((rel_path, None))
            self.po_files[0].save(self.po_files[0].fpath)

    def translate_path(self, path):
        """
        return translated path for textures
        """
        if path.startswith("special://skin/"):
            return os.path.join(self.path, path.replace("special://skin/", ""))
        else:
            return os.path.join(self.media_path, path)

    def return_node(self, keyword=None, folder=False):
        """
        get value from include list
        """
        if not keyword or not folder:
            return None
        if folder in self.fonts:
            for node in self.fonts[folder]:
                if node["name"] == keyword:
                    return node
        if folder in self.includes:
            for node in self.includes[folder]:
                if node["name"] == keyword:
                    return node
        return None

    def get_xml_files(self):
        """
        yields absolute paths of all window files
        """
        if self.xml_folders:
            for folder in self.xml_folders:
                for xml_file in self.window_files[folder]:
                    yield os.path.join(self.path, folder, xml_file)

    def bump_version(self, version):
        """
        bump addon.xml version and create changelog entry
        """
        self.root.attrib["version"] = version
        Utils.save_xml(self.xml_file, self.root)
        with open(self.changelog_path, "r") as f:
            contents = f.readlines()
        contents = [version, "", "-", "-", "", ""] + contents
        with open(self.changelog_path, "w") as f:
            f.write("\n".join(contents))

    def get_color_info(self, color_string):
        """
        return formatted info for *color_string, taken from color xmls (default + themes).
        """
        if all(c in string.hexdigits for c in color_string) and len(color_string) == 8:
            color_hex = "#" + color_string[2:]
            cont_color = Utils.get_cont_col(color_hex)
            alpha_percent = round(int(color_string[:2], 16) / (16 * 16) * 100)
            return '<a href="test" style="background-color:%s;color:%s">%d %% alpha</a>' % (color_hex, cont_color, alpha_percent)
