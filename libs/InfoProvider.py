import os
from Utils import *
import sublime
import codecs
from polib import polib
import re


SETTINGS_FILE = 'sublimekodi.sublime-settings'
DEFAULT_LANGUAGE_FOLDER = "English"


class InfoProvider():

    def __init__(self):
        self.include_list = {}
        self.include_file_list = {}
        self.window_file_list = {}
        self.color_list = []
        self.font_file = ""
        self.color_file = ""
        self.project_path = ""
        self.xml_path = ""
        self.builtin_list = []
        self.fonts = []
        self.string_list = []
        self.xml_folders = []
        self.addon_string_list = []
        self.labels_loaded = False
        self.settings_loaded = False

    def init_addon(self, path):
        self.project_path = path
        self.addon_xml_file = checkPaths([os.path.join(self.project_path, "addon.xml")])
        self.xml_folders = []
        if self.addon_xml_file:
            root = get_root_from_file(self.addon_xml_file)
            for node in root.findall('.//res'):
                self.xml_folders.append(node.attrib["folder"])
            if self.xml_folders:
                self.xml_path = os.path.join(path, self.xml_folders[0])
            else:
                self.xml_path = ""

    def get_colors(self):
        if self.project_path:
            paths = [os.path.join(self.project_path, "colors", "defaults.xml")]
            self.color_file = checkPaths(paths)
            if self.color_file:
                log("found color file: " + self.color_file)
                root = get_root_from_file(self.color_file)
                self.color_list = []
                for node in root.findall("color"):
                    color_dict = {"name": node.attrib["name"],
                                  "line": node.sourceline,
                                  "content": node.text,
                                  "filename": self.color_file}
                    self.color_list.append(color_dict)
                log("color list: %i colors found" % len(self.color_list))

    def get_fonts(self):
        if self.xml_folders:
            sublime.status_message("SublimeKodi: Updating fonts...")
            paths = [os.path.join(self.xml_path, "Font.xml"),
                     os.path.join(self.xml_path, "font.xml")]
            self.font_file = checkPaths(paths)
            if self.font_file:
                root = get_root_from_file(self.font_file)
                self.fonts = []
                for node in root.find("fontset").findall("font"):
                    string_dict = {"name": node.find("name").text,
                                   "size": node.find("size").text,
                                   "line": node.sourceline,
                                   "content": ET.tostring(node, pretty_print=True),
                                   "filename": node.find("filename").text}
                    self.fonts.append(string_dict)

    def update_include_list(self):
        self.include_list = {}
        for path in self.xml_folders:
            xml_folder = os.path.join(self.project_path, path)
            paths = [os.path.join(xml_folder, "Includes.xml"),
                     os.path.join(xml_folder, "includes.xml")]
            self.include_file_list[path] = []
            self.include_list[path] = []
            include_file = checkPaths(paths)
            self.update_includes(path, include_file)
            log("Include List: %i nodes found in '%s' folder." % (len(self.include_list[path]), path))

    def update_includes(self, path, xml_file):
        # recursive, walks through include files and updates include list and include file list
        if os.path.exists(xml_file):
            sublime.status_message("SublimeKodi: Updating Includes from " + xml_file)
            xml_folder = os.path.join(self.project_path, path)
            log("found include file: " + xml_file)
            root = get_root_from_file(xml_file)
            self.include_file_list[path].append(xml_file)
            self.include_list[path] += get_tags_from_file(xml_file, ["include", "variable", "constant"])
            for node in root.findall("include"):
                if "file" in node.attrib:
                    xml_file = os.path.join(xml_folder, node.attrib["file"])
                    self.update_includes(path, xml_file)
        else:
            log("Could not find include file " + xml_file)

    def update_xml_files(self):
        self.include_ref_list = {}
        for path in self.xml_folders:
            xml_folder = os.path.join(self.project_path, path)
            self.window_file_list[path] = get_xml_file_paths(xml_folder)

    def go_to_tag(self, view):
        keyword = findWord(view)
        if keyword:
            if keyword.isdigit():
                for node in self.string_list:
                    if node["id"] == "#" + keyword:
                        if int(keyword) >= 31000 and int(keyword) <= 33000:
                            file_path = self.addon_lang_path
                        else:
                            file_path = self.kodi_lang_path
                        sublime.active_window().open_file("%s:%s" % (file_path, node["line"]), sublime.ENCODED_POSITION)
                        return True
            else:
                for node in self.include_list[view.file_name().split(os.sep)[-2]]:
                    if node["name"] == keyword:
                        sublime.active_window().open_file("%s:%s" % (node["file"], node["line"]), sublime.ENCODED_POSITION)
                        return True
                for node in self.fonts:
                    if node["name"] == keyword:
                        sublime.active_window().open_file("%s:%s" % (self.font_file, node["line"]), sublime.ENCODED_POSITION)
                        return True
                for node in self.color_list:
                    if node["name"] == keyword:
                        sublime.active_window().open_file("%s:%s" % (self.color_file, node["line"]), sublime.ENCODED_POSITION)
                        return True
                log("no node with name %s found" % keyword)

    def return_node_content(self, keyword=None, return_entry="content"):
        if keyword:
            for node in self.fonts:
                if node["name"] == keyword:
                    return node[return_entry]
            view = sublime.active_window().active_view()
            for node in self.include_list[view.file_name().split(os.sep)[-2]]:
                if node["name"] == keyword:
                    return node[return_entry]
            # log("no node with name %s found" % keyword)

    def return_label(self, view, selection):
        if selection.isdigit():
            id_string = "#" + selection
            for item in self.string_list:
                if id_string == item["id"]:
                    tooltips = item["string"]
                    if self.use_native:
                        tooltips += "<br>" + item["native_string"]
                    return tooltips
        return ""

    def get_settings(self):
        history = sublime.load_settings(SETTINGS_FILE)
        self.kodi_path = history.get("kodi_path")
        log("kodi path: " + self.kodi_path)
        self.use_native = history.get("use_native_language")
        if self.use_native:
            self.language_folder = history.get("native_language")
            log("use native language: " + self.language_folder)
        else:
            self.language_folder = DEFAULT_LANGUAGE_FOLDER
            log("use default language: English")
        self.settings_loaded = True

    def get_addon_lang_file(self, path):
        if not self.addon_xml_file:
            return False
        paths = [os.path.join(path, "resources", "language", self.language_folder, "strings.po"),
                 os.path.join(path, "language", self.language_folder, "strings.po")]
        self.addon_lang_path = checkPaths(paths)
        if self.addon_lang_path:
            return codecs.open(self.addon_lang_path, "r", "utf-8").read()
        else:
            log("Could not find addon language file")
            log(paths)
            return ""

    def get_builtin_label(self):
        paths = [os.path.join(self.kodi_path, "addons", "resource.language.en_gb", "resources", "strings.po"),
                 os.path.join(self.kodi_path, "language", self.language_folder, "strings.po")]
        self.kodi_lang_path = checkPaths(paths)
        if self.kodi_lang_path:
            kodi_lang_file = codecs.open(self.kodi_lang_path, "r", "utf-8").read()
            po = polib.pofile(kodi_lang_file)
            self.builtin_list = []
            for entry in po:
                string = {"id": entry.msgctxt,
                          "line": entry.linenum,
                          "string": entry.msgid,
                          # "file": self.kodi_lang_path,
                          "native_string": entry.msgstr}
                self.builtin_list.append(string)
            self.labels_loaded = True
            log("Builtin labels loaded. Amount: %i" % len(self.builtin_list))
        else:
            log("Could not find kodi language file")
            return ""

    def update_labels(self):
        if not self.addon_xml_file:
            return False
        sublime.status_message("SublimeKodi: Updating Labels...")
        lang_file = self.get_addon_lang_file(self.project_path)
        po = polib.pofile(lang_file)
        log("Update labels for: %s" % self.project_path)
        self.addon_string_list = []
        for entry in po:
            string = {"id": entry.msgctxt,
                      "line": entry.linenum,
                      "string": entry.msgid,
                      # "file": self.addon_lang_path,
                      "native_string": entry.msgstr}
            self.addon_string_list.append(string)
        self.string_list = self.builtin_list + self.addon_string_list
        sublime.status_message("")
        log("Addon Labels updated. Amount: %i" % len(self.addon_string_list))

    def check_variables(self, tag_type):
        if tag_type == "variable":
            var_regex = "\$VAR\[(.*?)\]"
        else:
            var_regex = "<include.*>(.*?)<\/include>"
        var_refs = []
        unused_vars = []
        undefined_vars = []
        for folder in self.xml_folders:
            for xml_file in self.window_file_list[folder]:
                path = os.path.join(self.project_path, folder, xml_file)
                with open(path, encoding="utf8") as f:
                    for i, line in enumerate(f.readlines()):
                        for match in re.finditer(var_regex, line):
                            item = {"line": i + 1,
                                    "type": tag_type,
                                    "file": path,
                                    "name": match.group(1).split(",")[0]}
                            var_refs.append(item)
            for ref in var_refs:
                for node in self.include_list[folder]:
                    if node["type"] == tag_type and node["name"] == ref["name"]:
                        break
                else:
                    undefined_vars.append(ref)
            ref_list = [d['name'] for d in var_refs]
            for node in self.include_list[folder]:
                if node["type"] == tag_type and node["name"] not in ref_list:
                    unused_vars.append(node)
        return undefined_vars, unused_vars

    def check_values(self):
        # available for all controls
        listitems = []
        for folder in self.xml_folders:
            for xml_file in self.window_file_list[folder]:
                path = os.path.join(self.project_path, folder, xml_file)
                new_items = self.check_file(path)
                listitems.extend(new_items)
        return listitems

    def check_file(self, path):
        xml_file = os.path.basename(path)
        common = ["description", "camera", "posx", "posy", "top", "bottom", "left", "right", "centertop", "centerbottom", "centerleft", "centerright", "width", "height", "visible", "include", "animation"]
        list_common = ["focusedlayout", "itemlayout", "content", "onup", "ondown", "onleft", "onright", "onback", "orientation", "preloaditems", "scrolltime", "pagecontrol", "viewtype", "autoscroll", "hitrect"]
        # allowed child nodes for different control types (+ some other nodes)
        tag_checks = [[".//control[@type='button']/*", common + ["colordiffuse", "texturefocus", "texturenofocus", "label", "label2", "font", "textcolor", "disabledcolor", "selectedcolor", "shadowcolor", "align", "aligny", "textoffsetx", "textoffsety", "pulseonselect", "onclick", "onfocus", "onunfocus", "onup", "onleft", "onright", "ondown", "onback", "textwidth", "focusedcolor", "invalidcolor", "angle", "hitrect", "enable"]],
                      [".//control[@type='radiobutton']/*", common + ["colordiffuse", "texturefocus", "texturenofocus", "label", "selected", "font", "textcolor", "disabledcolor", "selectedcolor", "shadowcolor", "align", "aligny", "textoffsetx", "textoffsety", "pulseonselect", "onclick", "onfocus", "onunfocus", "onup", "onleft", "onright", "ondown", "onback", "textwidth", "focusedcolor", "angle", "hitrect", "enable", "textureradioonfocus", "textureradioofffocus", "textureradioonnofocus", "textureradiooffnofocus", "textureradioon", "textureradiooff", "radioposx", "radioposy", "radiowidth", "radioheight"]],
                      [".//control[@type='spincontrol']/*", common + ["colordiffuse", "textureup", "textureupfocus", "texturedown", "texturedownfocus", "spinwidth", "spinheight", "spinposx", "spinposy" "label", "subtype", "font", "textcolor", "disabledcolor", "shadowcolor", "align", "aligny", "textoffsetx", "textoffsety", "pulseonselect", "onfocus", "onunfocus", "onup", "onleft", "onright", "ondown", "onback", "hitrect", "enable"]],
                      [".//control[@type='togglebutton']/*", common + ["colordiffuse", "texturefocus", "alttexturefocus", "alttexturenofocus", "altclick", "texturenofocus", "label", "altlabel", "usealttexture", "font", "textcolor", "disabledcolor", "shadowcolor", "align", "aligny", "textoffsetx", "textoffsety", "pulseonselect", "onclick", "onfocus", "onunfocus", "onup", "onleft", "onright", "ondown", "onback", "textwidth", "focusedcolor", "subtype", "hitrect", "enable"]],
                      [".//control[@type='label']/*", common + ["align", "aligny", "scroll", "scrollout", "info", "number", "angle", "haspath", "label", "textcolor", "selectedcolor", "font", "shadowcolor", "disabledcolor", "pauseatend", "wrapmultiline", "scrollspeed", "scrollsuffix", "textoffsetx", "textoffsety"]],
                      [".//control[@type='textbox']/*", common + ["align", "aligny", "autoscroll", "label", "info", "font", "textcolor", "selectedcolor", "shadowcolor", "pagecontrol"]],
                      [".//control[@type='edit']/*", common + ["colordiffuse", "align", "aligny", "label", "hinttext", "font", "textoffsetx", "textoffsety", "pulseonselect", "textcolor", "disabledcolor", "invalidcolor", "focusedcolor", "shadowcolor", "texturefocus", "texturenofocus", "onclick", "onfocus", "onunfocus", "onup", "onleft", "onright", "ondown", "onback", "textwidth", "hitrect", "enable"]],
                      [".//control[@type='image']/*", common + ["align", "aligny", "aspectratio", "fadetime", "colordiffuse", "texture", "bordertexture", "bordersize", "info"]],
                      [".//control[@type='multiimage']/*", common + ["align", "aligny", "aspectratio", "fadetime", "colordiffuse", "imagepath", "timeperimage", "loop", "info", "randomize", "pauseatend"]],
                      [".//control[@type='scrollbar']/*", common + ["texturesliderbackground", "texturesliderbar", "texturesliderbarfocus", "textureslidernib", "textureslidernibfocus", "pulseonselect", "orientation", "showonepage", "pagecontrol", "onclick", "onfocus", "onunfocus", "onup", "onleft", "onright", "ondown", "onback"]],
                      [".//control[@type='progress']/*", common + ["texturebg", "lefttexture", "colordiffuse", "righttexture", "overlaytexture", "midtexture", "info", "reveal"]],
                      [".//control[@type='list']/*", common + list_common],
                      [".//control[@type='wraplist']/*", common + list_common + ["focusposition"]],
                      [".//control[@type='panel']/*", common + list_common],
                      [".//control[@type='fixedlist']/*", common + list_common + ["movement", "focusposition"]],
                      [".//content/*", ["item", "include"]],
                      [".//variable/*", ["value"]]]
        # allowed attributes for some specific nodes
        att_checks = [[["aspectratio"], ["align", "aligny", "scalediffuse"]],
                      [["texture"], ["background", "flipx", "flipy", "fallback", "border", "diffuse", "colordiffuse"]],
                      [["label"], ["fallback"]],
                      [["defaultcontrol"], ["always"]],
                      [["visible"], ["allowhiddenfocus"]],
                      [["align", "aligny", "posx", "posy", "textoffsetx", "textoffsety"], []],
                      [["height", "width"], ["min", "max"]],
                      [["camera"], ["x", "y"]],
                      [["hitrect"], ["x", "y", "w", "h"]],
                      [["onload", "onunload", "onclick", "onleft", "onright", "onup", "ondown", "onback", "onfocus", "onunfocus", "value"], ["condition"]],
                      [["property"], ["name", "fallback"]],
                      [["focusedlayout", "itemlayout"], ["height", "width", "condition"]],
                      [["item"], ["id"]],
                      [["control"], ["id", "type"]],
                      [["variable"], ["name"]],
                      [["include"], ["name", "condition", "file"]],
                      [["animation"], ["start", "end", "effect", "tween", "easing", "time", "condition", "reversible", "type", "center", "delay", "pulse", "loop", "acceleration"]],
                      [["effect"], ["start", "end", "tween", "easing", "time", "condition", "type", "center", "delay", "pulse", "loop", "acceleration"]]]
        # check correct parantheses for some nodes
        bracket_tags = ["visible", "enable", "usealttexture", "selected"]
        # check some nodes to use noop instead of "-" / empty
        noop_tags = ["onclick", "onfocus", "onunfocus", "onup", "onleft", "onright", "ondown", "onback"]
        # check that some nodes only exist once on each level
        # todo: special cases: label for fadelabel
        double_tags = ["camera", "posx", "posy", "top", "bottom", "left", "right", "centertop", "centerbottom", "centerleft", "centerright", "width", "height",
                       "colordiffuse", "texturefocus", "texturenofocus", "font", "selected", "textcolor", "disabledcolor", "selectedcolor",
                       "shadowcolor", "align", "aligny", "textoffsetx", "textoffsety", "pulseonselect", "textwidth", "focusedcolor", "invalidcolor", "angle", "hitrect"]
        # check that some nodes only contain specific text
        allowed_text = [[["align"], ["left", "center", "right", "justify"]],
                        [["aspectratio"], ["keep", "scale", "stretch", "center"]],
                        [["aligny"], ["top", "center", "bottom"]],
                        [["orientation"], ["horizontal", "vertical"]],
                        [["subtype"], ["page", "int", "float", "text"]],
                        [["action"], ["volume", "seek"]],
                        [["scroll", "randomize", "scrollout", "pulseonselect", "reverse", "usecontrolcoords"], ["false", "true", "yes", "no"]]]
        # check that some attributes may only contain specific values
        allowed_attr = [["align", ["left", "center", "right", "justify"]],
                        ["aligny", ["top", "center", "bottom"]],
                        ["flipx", ["true", "false"]],
                        ["flipy", ["true", "false"]]]
        root = get_root_from_file(path)
        tree = ET.ElementTree(root)
        listitems = []
        for check in tag_checks:
            for node in root.xpath(check[0]):
                if node.tag not in check[1]:
                    item = {"line": node.sourceline,
                            "type": node.tag,
                            "filename": xml_file,
                            "message": ["invalid tag in line %i: %s" % (node.sourceline, node.tag), xml_file],
                            "file": path}
                    listitems.append(item)
        for check in att_checks:
            xpath = ".//" + " | .//".join(check[0])
            for node in root.xpath(".//%s" % xpath):
                for attr in node.attrib:
                    if attr not in check[1]:
                        item = {"line": node.sourceline,
                                "type": node.tag,
                                "filename": xml_file,
                                "message": ["invalid attribute in line %i: %s" % (node.sourceline, attr), xml_file],
                                "file": path}
                        listitems.append(item)
        xpath = ".//" + " | .//".join(bracket_tags)
        for node in root.xpath(xpath):
            if not node.text or not check_brackets(node.text):
                condition = str(node.text).replace("  ", "").replace("\t", "")
                item = {"line": node.sourceline,
                        "type": node.tag,
                        "filename": xml_file,
                        "message": ["Brackets do not match in line %i: %s" % (node.sourceline, condition), xml_file],
                        "file": path}
                listitems.append(item)
        for node in root.xpath(".//*[@condition]"):
            if not check_brackets(node.attrib["condition"]):
                condition = str(node.attrib["condition"]).replace("  ", "").replace("\t", "")
                item = {"line": node.sourceline,
                        "type": node.tag,
                        "filename": xml_file,
                        "message": ["Brackets do not match in line %i: %s" % (node.sourceline, condition), xml_file],
                        "file": path}
                listitems.append(item)
        xpath = ".//" + " | .//".join(noop_tags)
        for node in root.xpath(xpath):
            if node.text == "-" or not node.text:
                item = {"line": node.sourceline,
                        "type": node.tag,
                        "filename": xml_file,
                        "message": ["Use 'noop' for empty calls in line %i <%s>" % (node.sourceline, node.tag), xml_file],
                        "file": path}
                listitems.append(item)
        xpath = ".//" + " | .//".join(double_tags)
        for node in root.xpath(xpath):
            if not node.getchildren():
                xpath = tree.getpath(node)
                if xpath.endswith("]") and not xpath.endswith("[1]"):

                    item = {"line": node.sourceline,
                            "type": node.tag,
                            "filename": xml_file,
                            "message": ["Invalid multiple tags in line %i: %s" % (node.sourceline, node.tag), xml_file],
                            "file": path}
                    listitems.append(item)
        for check in allowed_text:
            xpath = ".//" + " | .//".join(check[0])
            for node in root.xpath(xpath):
                if node.text.lower() not in check[1]:
                    item = {"line": node.sourceline,
                            "type": node.tag,
                            "filename": xml_file,
                            "message": ["invalid value for %s in line %i: %s" % (node.tag, node.sourceline, node.text), xml_file],
                            "file": path}
                    listitems.append(item)
        for check in allowed_attr:
            for node in root.xpath(".//*[(@%s)]" % check[0]):
                if node.attrib[check[0]] not in check[1]:
                    item = {"line": node.sourceline,
                            "type": node.tag,
                            "filename": xml_file,
                            "message": ["invalid value for %s attribute in line %i: %s" % (check[0], node.sourceline, node.attrib[check[0]]), xml_file],
                            "file": path}
                    listitems.append(item)
        fontlist = ["-"]
        for item in self.fonts:
            fontlist.append(item["name"])
        for node in root.xpath(".//font"):
            if not node.getchildren() and node.text not in fontlist:
                item = {"line": node.sourceline,
                        "type": node.tag,
                        "filename": xml_file,
                        "message": ["invalid font in line %i: %s" % (node.sourceline, node.text), xml_file],
                        "file": path}
                listitems.append(item)
        return listitems
