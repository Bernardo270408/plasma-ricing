import QtQuick
import QtQuick.Layouts

import Quickshell

import qs.Commons
import qs.Widgets

RowLayout {
    id: root
    Layout.fillWidth: true

    
    /********************************
    * PROPERTIES
    ********************************/
    // Required properties
    required property var pluginApi

    required property string screenName

    // Optional properties
    property bool enabled:        true
    property var monitorSpecific: undefined

    // Monitor specific properties
    readonly property bool isPlaying: pluginApi?.pluginSettings?.[screenName]?.isPlaying || false
    readonly property bool isMuted:   pluginApi?.pluginSettings?.[screenName]?.isMuted   || false

    // Global properties
    readonly property bool globalMonitorSpecific: pluginApi?.pluginSettings?.monitorSpecific || false

    // Local properties
    readonly property bool _monitorSpecific: monitorSpecific === undefined ? globalMonitorSpecific : (typeof monitorSpecific === "boolean" ? monitorSpecific : false);


    /********************************
    * FUNCTIONS
    ********************************/
    function random() {
        if(pluginApi?.mainInstance == null) {
            Logger.e("video-wallpaper", "Main instance isn't loaded");
            return;
        }

        pluginApi.mainInstance.random(screenName);
    }

    function clear() {
        if(pluginApi?.mainInstance == null) {
            Logger.e("video-wallpaper", "Main instance isn't loaded");
            return;
        }

        pluginApi.mainInstance.clear(screenName);
    }

    function togglePlaying() {
        if (pluginApi == null) return;

        saveSetting("isPlaying", !isPlaying);
    }

    function toggleMute() {
        if(pluginApi == null) return;

        saveSetting("isMuted", !isMuted);
    }

    function saveSetting(key: string, value: var) {
        if (!_monitorSpecific) {
            for (const screen of Quickshell.screens) {
                if (pluginApi?.pluginSettings?.[screen.name] === undefined) {
                    pluginApi.pluginSettings[screen.name] = {};
                }

                pluginApi.pluginSettings[screen.name][key] = value;
            }
        } else {
            if (pluginApi?.pluginSettings?.[screenName] === undefined) {
                pluginApi.pluginSettings[screenName] = {};
            }

            pluginApi.pluginSettings[screenName][key] = value;
        }

        pluginApi.saveSettings();
    }


    /********************************
    * COMPONENTS
    ********************************/
    NButton {
        icon: "dice"
        enabled:     root.enabled
        text:        root.pluginApi?.tr("common.tool_row.random.text")    || "Random"
        tooltipText: root.pluginApi?.tr("common.tool_row.random.tooltip") || "Choose a random wallpaper from the wallpapers folder."
        onClicked:   root.random()
    }

    NButton {
        icon: "clear-all"
        enabled:     root.enabled
        text:        root.pluginApi?.tr("common.tool_row.clear.text")    || "Clear"
        tooltipText: root.pluginApi?.tr("common.tool_row.clear.tooltip") || "Clear the current wallpaper."
        onClicked:   root.clear()
    }

    NButton {
        enabled:     root.enabled
        icon:        root.isPlaying ? "media-pause" : "media-play"
        text:        root.isPlaying ? root.pluginApi?.tr("common.tool_row.pause.text")    || "Pause"                      : root.pluginApi?.tr("common.tool_row.play.text")    || "Play";
        tooltipText: root.isPlaying ? root.pluginApi?.tr("common.tool_row.pause.tooltip") || "Pause the video wallpaper." : root.pluginApi?.tr("common.tool_row.play.tooltip") || "Resume the video wallpaper.";
        onClicked:   root.togglePlaying();
    }

    NButton {
        enabled:     root.enabled
        icon:        root.isMuted ? "volume-high" : "volume-mute"
        text:        root.isMuted ? root.pluginApi?.tr("common.tool_row.unmute.text")    || "Unmute" :                      root.pluginApi?.tr("common.tool_row.mute.text")    || "Mute";
        tooltipText: root.isMuted ? root.pluginApi?.tr("common.tool_row.unmute.tooltip") || "Unmute the video wallpaper." : root.pluginApi?.tr("common.tool_row.mute.tooltip") || "Mute the video wallpaper.";
        onClicked:   root.toggleMute()
    }
}
