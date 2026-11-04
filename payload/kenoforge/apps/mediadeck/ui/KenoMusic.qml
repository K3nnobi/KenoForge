import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    width: 1440
    height: 850
    minimumWidth: 1100
    minimumHeight: 650
    title: "KenoForge Music · MediaDeck"
    color: "#0b1018"
    palette.window: "#0b1018"
    palette.windowText: "#edf3fc"
    palette.text: "#edf3fc"
    palette.button: "#172131"
    palette.buttonText: "#edf3fc"
    palette.base: "#111925"
    palette.highlight: "#78a9ff"
    palette.highlightedText: "#0b1018"
    property bool visualization: false
    property color accent: "#78a9ff"

    function toggleFullScreen() {
        if (window.visibility === Window.FullScreen)
            window.showNormal()
        else
            window.showFullScreen()
    }

    function endVisualization() {
        visualPage.end()
        visualization = false
    }

    Shortcut {
        sequence: "Escape"
        enabled: window.visualization
        onActivated: window.endVisualization()
    }
    Shortcut {
        sequence: "F11"
        onActivated: window.toggleFullScreen()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 42
            Label {
                text: "KENOFORGE  /  MUSIC"
                color: window.accent
                font.pixelSize: 18
                font.bold: true
            }
            Item { Layout.fillWidth: true }
            CheckBox {
                text: "Visualizador"
                checked: visualizerService.enabled
                onToggled: visualizerService.setEnabled(checked)
                contentItem: Text {
                    text: parent.text
                    leftPadding: parent.indicator.width + parent.spacing
                    verticalAlignment: Text.AlignVCenter
                    color: "#edf3fc"
                }
            }
            Label { text: "Volume"; color: "#a2b1c8" }
            Slider {
                Layout.preferredWidth: 130
                from: 0
                to: 100
                value: audioService.volume
                onMoved: audioService.setVolume(Math.round(value))
            }
            Label {
                text: audioService.volume + "%"
                color: "#a2b1c8"
                Layout.preferredWidth: 42
            }
            Button {
                objectName: "fullscreenButton"
                text: window.visibility === Window.FullScreen ? "Sair da tela inteira" : "Tela inteira"
                onClicked: window.toggleFullScreen()
                ToolTip.visible: hovered
                ToolTip.text: "Alternar tela inteira (F11)"
                background: Rectangle {
                    radius: 10
                    color: parent.down ? "#293950" : "#172131"
                    border.color: parent.hovered ? window.accent : "#293950"
                }
                contentItem: Text {
                    text: parent.text
                    color: "#edf3fc"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
            Button {
                text: "Fechar player"
                onClicked: window.close()
                background: Rectangle {
                    radius: 10
                    color: parent.down ? "#293950" : "#172131"
                    border.color: parent.hovered ? window.accent : "#293950"
                }
                contentItem: Text {
                    text: parent.text
                    color: "#edf3fc"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        MusicPage {
            id: musicPage
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: !window.visualization
            accent: window.accent
            panel: "#111925"
            panelAlt: "#172131"
            line: "#293950"
            primaryText: "#edf3fc"
            secondaryText: "#a2b1c8"
            onVisualizerRequested: {
                window.visualization = true
                visualPage.begin()
            }
        }
        MusicVisualizerPage {
            id: visualPage
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: window.visualization
            accent: window.accent
            onExitRequested: window.endVisualization()
        }
        Label {
            Layout.fillWidth: true
            visible: musicService.errorText.length > 0
            text: musicService.errorText
            color: "#ffb5a8"
            wrapMode: Text.WordWrap
        }
    }
}
