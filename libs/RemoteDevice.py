from Utils import *
import os


class RemoteDevice():

    def __init__(self):
        self.is_busy = False
        pass

    def setup(self, settings):
        self.settings = settings
        self.connected = False
        self.userdata_folder = self.settings.get("remote_userdata_folder")
        self.ip = self.settings.get("remote_ip")

    # @check_busy
    def adb_connect(self, ip):
        self.ip = ip
        self.panel_log("Connect to remote with ip %s" % ip)
        result = command_line("adb", ["connect", str(ip)])
        self.panel_log(result)
        self.connected = True

    @run_async
    @check_busy
    def adb_connect_async(self, ip):
        self.adb_connect(ip)

    @check_busy
    def adb_reconnect(self, ip=""):
        if not ip:
            ip = self.ip
        self.adb_disconnect()
        self.adb_connect(ip)

    @run_async
    def adb_reconnect_async(self, ip=""):
        self.adb_reconnect(ip)

    # @check_busy
    def adb_disconnect(self):
        self.panel_log("Disconnect from remote")
        result = command_line("adb", ["disconnect"])
        self.panel_log(result)
        self.connected = False

    @run_async
    @check_busy
    def adb_disconnect_async(self):
        self.adb_disconnect()

    @check_busy
    def adb_push(self, source, target):
        if not target.endswith('/'):
            target += '/'
        result = command_line("adb", ["push", source.replace('\\', '/'), target.replace('\\', '/')])
        self.panel_log(result)

    @run_async
    @check_busy
    def adb_push_async(self, source, target):
        self.adb_push(source, target)

    @check_busy
    def adb_pull(self, path, target):
        result = command_line("adb", ["pull", path, target])
        self.panel_log(result)

    @run_async
    @check_busy
    def adb_pull_async(self, path, target):
        self.adb_pull(path, target)

    @run_async
    @check_busy
    def adb_restart_server(self):
        pass

    @run_async
    @check_busy
    def push_to_box(self, addon, all_file=False):
        self.panel_log("push %s to remote" % addon)
        for root, dirs, files in os.walk(addon):
            # ignore git files
            if ".git" in root.split(os.sep):
                continue
            if not all_file and os.path.basename(root) not in ['1080i', '720p']:
                continue
            else:
                target = '%saddons/%s%s' % (self.userdata_folder, os.path.basename(addon), root.replace(addon, "").replace('\\', '/'))
                command_line("adb", ["shell", "mkdir", target])
            for f in files:
                if f.endswith('.pyc') or f.endswith('.pyo'):
                    continue
                result = command_line("adb", ["push", os.path.join(root, f).replace('\\', '/'), target.replace('\\', '/')])
                self.panel_log(result)
        self.panel_log("All files pushed")

    @run_async
    def get_log(self, open_function, target):
        self.panel_log("Pull logs from remote")
        self.adb_pull("%stemp/xbmc.log" % self.userdata_folder, target)
        # self.adb_pull("%stemp/xbmc.old.log" % self.userdata_folder)
        self.panel_log("Finished pulling logs")
        open_function(os.path.join(target, "xbmc.log"))

    @run_async
    @check_busy
    def clear_cache(self):
        result = command_line("adb", ["shell", "rm", "-rf", os.path.join(self.userdata_folder, "temp")])
        self.panel_log(result)

    def panel_log(self, text):
        try:
            import sublime
            wnd = sublime.active_window()
            wnd.run_command("log", {"label": text.strip()})
        except Exception as e:
            log(e)
            log(text)