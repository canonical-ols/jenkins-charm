import os

from unittest import mock

from testtools.matchers import PathExists

from charmhelpers.core import hookenv

from charmtest import CharmTest

from charms.layer.jenkins import paths
from charms.layer.jenkins.plugins import Plugins


@mock.patch("test_plugins.Plugins._restart_jenkins")
class PluginsTest(CharmTest):

    def setUp(self):
        super(PluginsTest, self).setUp()
        self.plugins = Plugins()

        self.fakes.fs.add(paths.PLUGINS)
        os.makedirs(paths.PLUGINS)
        self.fakes.users.add("jenkins", 123)
        self.fakes.groups.add("jenkins", 123)
        self.orig_plugins_site = hookenv.config()["plugins-site"]
        self.fakes.processes.wget.locations["http://x/plugin.hpi"] = b"data"

    def tearDown(self):
        super(PluginsTest, self).tearDown()
        hookenv.config()["plugins-site"] = self.orig_plugins_site

    @mock.patch("test_plugins.Plugins._get_plugin_version")
    def test_install(self, mock_get_plugin_version, mock_restart_jenkins):
        """
        The given plugins are downloaded from the Jenkins site.
        """
        mock_get_plugin_version.return_value = False
        plugin_name = "ansicolor"
        installed_plugin = ""
        installed_plugin.join(self.plugins.install(plugin_name))
        plugin_path = os.path.join(paths.PLUGINS, installed_plugin)
        self.assertTrue(
            os.path.exists(plugin_path),
            msg="Plugin not installed in the proper directory")

        mock_restart_jenkins.assert_called_with()

    @mock.patch("test_plugins.Plugins._remove_plugin")
    @mock.patch("test_plugins.Plugins._install_plugins")
    @mock.patch("test_plugins.Plugins._get_plugins_to_install")
    def test_install_do_remove_unlisted(self, mock_get_plugins_to_install, mock_install_plugins, mock_remove_plugin, mock_restart_jenkins):
        """
        If remove-unlisted-plugins is set to 'yes', then unlisted plugins
        are removed from disk.
        """
        plugin_name = "plugin"
        plugin_path = os.path.join(paths.PLUGINS, "{}-1.jpi".format(plugin_name))
        mock_get_plugins_to_install.return_value = {plugin_name}
        mock_install_plugins.return_value = {plugin_path}
        orig_remove_unlisted_plugins = hookenv.config()["remove-unlisted-plugins"]
        try:
            hookenv.config()["remove-unlisted-plugins"] = "yes"
            unlisted_plugin = os.path.join(paths.PLUGINS, "unlisted.jpi")
            with open(unlisted_plugin, "w"):
                pass
            self.plugins.install(plugin_name)
            # we can't use os.path.join() as paths.PLUGINS is an absolute path
            unlisted_plugin_path = "{}{}".format(
                self.fakes.fs.root.path, os.path.join(paths.PLUGINS, "unlisted.jpi"))
            mock_remove_plugin.assert_called_with(unlisted_plugin_path)

        finally:
            hookenv.config()["remove-unlisted-plugins"] = orig_remove_unlisted_plugins

    @mock.patch("test_plugins.Plugins._remove_plugin")
    @mock.patch("test_plugins.Plugins._install_plugins")
    @mock.patch("test_plugins.Plugins._get_plugins_to_install")
    def test_install_dont_remove_unlisted(self, mock_get_plugins_to_install, mock_install_plugins, mock_remove_plugin, mock_restart_jenkins):
        """
        If remove-unlisted-plugins is set to 'no', then unlisted plugins
        will be left on disk.
        """
        plugin_name = "plugin"
        plugin_path = os.path.join(paths.PLUGINS, "{}-1.jpi".format(plugin_name))
        mock_get_plugins_to_install.return_value = {plugin_name}
        mock_install_plugins.return_value = {plugin_path}
        self.plugins.install(plugin_name)
        mock_remove_plugin.assert_not_called()

    @mock.patch("test_plugins.Plugins._install_plugins")
    @mock.patch("test_plugins.Plugins._get_plugins_to_install")
    def test_install_skip_non_file_unlisted(self, mock_get_plugins_to_install, mock_install_plugins,  mock_restart_jenkins):
        """
        If an unlisted plugin is not actually a file, it's just skipped and
        doesn't get removed.
        """
        mock_get_plugins_to_install.return_value = {"plugin"}
        mock_install_plugins.return_value = {
            os.path.join(paths.PLUGINS, "plugin.jpi")}
        orig_remove_unlisted_plugins = hookenv.config()["remove-unlisted-plugins"]
        try:
            hookenv.config()["remove-unlisted-plugins"] = "yes"
            unlisted_plugin = os.path.join(paths.PLUGINS, "unlisted.hpi")
            os.mkdir(unlisted_plugin)
            self.plugins.install("plugin")
            self.assertThat(unlisted_plugin, PathExists())
        finally:
            hookenv.config()["remove-unlisted-plugins"] = orig_remove_unlisted_plugins

    @mock.patch("test_plugins.Plugins._download_plugin")
    @mock.patch("test_plugins.Plugins._get_plugin_version")
    @mock.patch("test_plugins.Plugins._get_plugins_to_install")
    def test_install_already_installed(self, mock_get_plugins_to_install, mock_get_plugin_version, mock_download_plugin, mock_restart_jenkins):
        """
        If a plugin is already installed, it doesn't get downloaded.
        """
        plugin_name = "plugin"
        mock_get_plugins_to_install.return_value = {plugin_name}
        mock_get_plugin_version.return_value = "1"
        orig_remove_unlisted_plugins = hookenv.config()["remove-unlisted-plugins"]
        try:
            hookenv.config()["remove-unlisted-plugins"] = "yes"
            hookenv.config()["plugins-force-reinstall"] = False
            hookenv.config()["plugins-auto-update"] = False
            self.plugins.install(plugin_name)
            mock_download_plugin.assert_not_called()
        finally:
            hookenv.config()["remove-unlisted-plugins"] = orig_remove_unlisted_plugins

    @mock.patch("test_plugins.Plugins._download_plugin")
    @mock.patch("test_plugins.Plugins._get_plugin_version")
    @mock.patch("test_plugins.Plugins._get_plugins_to_install")
    def test_install_force_reinstall(self, mock_get_plugins_to_install, mock_get_plugin_version, mock_download_plugin, mock_restart_jenkins):
        """
        If a plugin is already installed and plugin-force-reinstall is yes it
        should get downloaded.
        """
        plugin_name = "plugin"
        mock_get_plugins_to_install.return_value = {plugin_name}
        mock_get_plugin_version.return_value = "1"
        orig_remove_unlisted_plugins = hookenv.config()["remove-unlisted-plugins"]
        try:
            hookenv.config()["remove-unlisted-plugins"] = "yes"
            hookenv.config()["plugins-force-reinstall"] = True
            self.plugins.install(plugin_name)
            mock_download_plugin.assert_called_with(plugin_name, mock.ANY)
        finally:
            hookenv.config()["remove-unlisted-plugins"] = orig_remove_unlisted_plugins

    def test_install_bad_plugin(self, mock_restart_jenkins):
        """
        If plugin can't be downloaded we expect error message in the logs
        """
        orig_remove_unlisted_plugins = hookenv.config()["remove-unlisted-plugins"]
        try:
            hookenv.config()["remove-unlisted-plugins"] = "yes"
            plugin_path = os.path.join(paths.PLUGINS, "bad_plugin.hpi")
            with open(plugin_path, "w"):
                pass
            self.assertRaises(Exception,
                              self.plugins.install, "bad_plugin")
        finally:
            hookenv.config()["remove-unlisted-plugins"] = orig_remove_unlisted_plugins

    def test_update(self, mock_restart_jenkins):
        """
        The given plugins are downloaded from the Jenkins site if newer
        versions are available
        """
        hookenv.config()["plugins-auto-update"] = True
        plugin_path = os.path.join(paths.PLUGINS, "plugin.hpi")
        orig_plugins_site = hookenv.config()["plugins-site"]
        try:
            hookenv.config()["plugins-site"] = "http://x/"
            with open(plugin_path, "w"):
                pass
            self.plugins.update("plugin")
            commands = [proc.args[0] for proc in self.fakes.processes.procs]
            self.assertIn("wget", commands)
        finally:
            hookenv.config()["plugins-site"] = orig_plugins_site

    def test_update_bad_plugin(self, mock_restart_jenkins):
        """
        If plugin can't be downloaded we expect error message in the logs
        """
        def broken_download(*args, **kwargs):
            raise Exception("error")

        self.plugins._install_plugin = broken_download
        plugin_path = os.path.join(paths.PLUGINS, "bad_plugin.hpi")
        with open(plugin_path, "w"):
            pass
        self.assertRaises(Exception,
                          self.plugins.update, "bad_plugin")
