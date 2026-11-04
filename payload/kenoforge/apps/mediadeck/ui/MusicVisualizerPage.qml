import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

Item {
    id: page

    property color accent: "#78a9ff"
    property color primaryText: "#f5f7fb"
    property color secondaryText: "#9da7b6"

    property int modeIndex: 0
    property bool controlsVisible: true

    // A visualização é renderizada internamente em 55% da resolução
    // da tela e ampliada pelo Qt Quick. É o maior ganho de GPU desta
    // versão sem alterar a resolução da interface/controles.
    property real renderScale: 0.55

    readonly property var modeNames: [
        "Spectrum",
        "Wave",
        "Radial",
        "Particles",
        "VU Meter",
        "Album Pulse"
    ]

    signal exitRequested()

    function showControls() {
        controlsVisible = true
        controlsTimer.restart()
    }

    function begin() {
        visible = true
        enabled = true
        controlsVisible = true

        visualizerService.setEcoMode(true)

        forceActiveFocus()
        controlsTimer.restart()
    }

    function end() {
        controlsTimer.stop()
        controlsVisible = false

        visualizerService.setEcoMode(false)
    }

    function nextMode() {
        modeIndex = (modeIndex + 1) % modeNames.length
        showControls()
    }

    function previousMode() {
        modeIndex = (
            modeIndex - 1 + modeNames.length
        ) % modeNames.length
        showControls()
    }

    function gamepadLeft() { previousMode() }
    function gamepadRight() { nextMode() }
    function gamepadUp() { audioService.setVolume(Math.min(100, audioService.volume + 5)); showControls() }
    function gamepadDown() { audioService.setVolume(Math.max(0, audioService.volume - 5)); showControls() }
    function gamepadConfirm() { musicService.playPause(); showControls() }
    function gamepadSecondary() { musicService.previous(); showControls() }
    function gamepadFavorite() { musicService.toggleCurrentFavorite(); showControls() }
    function gamepadSelect() { musicService.next(); showControls() }
    function gamepadMenu() { musicService.playPause(); showControls() }
    function gamepadBack() { return false }

    focus: true

    Keys.onLeftPressed: previousMode()
    Keys.onRightPressed: nextMode()

    Rectangle {
        anchors.fill: parent
        color: "#05070a"
    }

    Rectangle {
        width: parent.width * 0.70
        height: parent.height * 0.95
        x: -width * 0.25
        y: -height * 0.24
        radius: width / 2
        color: Qt.rgba(
            page.accent.r,
            page.accent.g,
            page.accent.b,
            0.055
        )
    }

    Rectangle {
        width: parent.width * 0.55
        height: parent.height * 0.80
        x: parent.width - width * 0.72
        y: parent.height - height * 0.68
        radius: width / 2
        color: Qt.rgba(
            page.accent.r,
            page.accent.g,
            page.accent.b,
            0.035
        )
    }

    Item {
        id: visualizationArea

        anchors.fill: parent

        // Renderiza todos os efeitos em uma textura menor.
        // Os controles não fazem parte desta layer e continuam nítidos.
        layer.enabled: true
        layer.smooth: true
        layer.textureSize: Qt.size(
            Math.max(
                320,
                Math.round(width * page.renderScale)
            ),
            Math.max(
                180,
                Math.round(height * page.renderScale)
            )
        )

        VisualizerSpectrum {
            anchors.fill: parent
            visible: page.modeIndex === 0
            accent: page.accent
            levels: visualizerService.levels
            peaks: visualizerService.peaks
        }

        VisualizerWave {
            anchors.fill: parent
            visible: page.modeIndex === 1
            accent: page.accent
            levels: visualizerService.levels
        }

        VisualizerRadial {
            anchors.fill: parent
            visible: page.modeIndex === 2
            accent: page.accent
            levels: visualizerService.levels
            coverUrl: musicService.currentCoverUrl
        }

        VisualizerParticles {
            anchors.fill: parent
            visible: page.modeIndex === 3
            accent: page.accent
            levels: visualizerService.levels
        }

        VisualizerVUMeter {
            anchors.fill: parent
            visible: page.modeIndex === 4
            accent: page.accent
            levels: visualizerService.levels
        }

        VisualizerAlbumPulse {
            anchors.fill: parent
            visible: page.modeIndex === 5
            accent: page.accent
            levels: visualizerService.levels
            coverUrl: musicService.currentCoverUrl
        }
    }

    MouseArea {
        anchors.fill: parent
        z: 5

        hoverEnabled: true

        onPositionChanged: {
            page.showControls()
        }

        onClicked: {
            page.controlsVisible = !page.controlsVisible

            if (page.controlsVisible)
                controlsTimer.restart()
            else
                controlsTimer.stop()
        }
    }

    Rectangle {
        id: topPanel

        z: 20

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top

        height: 108

        opacity:
            page.controlsVisible
            ? 1.0
            : 0.0

        visible: opacity > 0.01

        color: "#d90a0d12"

        Behavior on opacity {
            NumberAnimation {
                duration: 150
            }
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 24
            anchors.rightMargin: 24
            spacing: 16

            HoverButton {
                implicitWidth: 58
                implicitHeight: 54
                hoverAccent: page.accent
                hoverRadius: 16

                background: Rectangle {
                    radius: 16
                    color: parent.down ? "#263447" : "#171e29"
                    border.color: "#3c4b5e"
                }

                contentItem: Text {
                    text: "←"
                    color: page.primaryText
                    font.pixelSize: 25
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                onClicked: {
                    page.end()
                    page.exitRequested()
                }
            }

            Rectangle {
                implicitWidth: 58
                implicitHeight: 58
                radius: 12
                color: "#11161e"
                border.color: "#2d3949"
                clip: true

                Image {
                    anchors.fill: parent
                    source: musicService.currentCoverUrl
                    fillMode: Image.PreserveAspectCrop
                    visible: musicService.currentCoverUrl.length > 0
                }

                Text {
                    anchors.centerIn: parent
                    visible: musicService.currentCoverUrl.length === 0
                    text: "♫"
                    color: page.accent
                    font.pixelSize: 27
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    Layout.fillWidth: true
                    text: musicService.currentTitle
                    color: page.primaryText
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text:
                        musicService.currentArtist.length > 0
                        ? musicService.currentArtist
                        : "MediaDeck Music"

                    color: page.secondaryText
                    font.pixelSize: 13
                    elide: Text.ElideRight
                }
            }

            Rectangle {
                implicitWidth: modeLabel.implicitWidth + 28
                implicitHeight: 38
                radius: 19
                color: Qt.rgba(
                    page.accent.r,
                    page.accent.g,
                    page.accent.b,
                    0.13
                )
                border.color: page.accent

                Text {
                    id: modeLabel
                    anchors.centerIn: parent
                    text: page.modeNames[page.modeIndex]
                    color: page.accent
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                }
            }
        }
    }

    Rectangle {
        id: bottomPanel

        z: 20

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom

        height: 174

        opacity:
            page.controlsVisible
            ? 1.0
            : 0.0

        visible: opacity > 0.01

        color: "#df090c11"

        Behavior on opacity {
            NumberAnimation {
                duration: 150
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: 24
            anchors.rightMargin: 24
            anchors.topMargin: 14
            anchors.bottomMargin: 16
            spacing: 11

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Item {
                    Layout.fillWidth: true
                }

                MediaButton {
                    text: "|◀"
                    enabled: musicService.songCount > 0
                    accent: page.accent
                    primaryText: page.primaryText

                    onClicked: {
                        musicService.previous()
                        page.showControls()
                    }
                }

                MediaButton {
                    text: musicService.playing ? "Ⅱ" : "▶"
                    enabled: musicService.songCount > 0
                    emphasized: true
                    accent: page.accent
                    primaryText: page.primaryText

                    onClicked: {
                        musicService.playPause()
                        page.showControls()
                    }
                }

                MediaButton {
                    text: "▶|"
                    enabled: musicService.songCount > 0
                    accent: page.accent
                    primaryText: page.primaryText

                    onClicked: {
                        musicService.next()
                        page.showControls()
                    }
                }

                Item {
                    Layout.fillWidth: true
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Repeater {
                    model: page.modeNames.length

                    delegate: HoverButton {
                        required property int index

                        Layout.fillWidth: true
                        implicitHeight: 48

                        hoverAccent: page.accent
                        hoverRadius: 15

                        background: Rectangle {
                            radius: 15

                            color:
                                page.modeIndex === index
                                ? Qt.rgba(
                                      page.accent.r,
                                      page.accent.g,
                                      page.accent.b,
                                      0.22
                                  )
                                : "#151b24"

                            border.color:
                                page.modeIndex === index
                                ? page.accent
                                : "#344052"

                            border.width:
                                page.modeIndex === index
                                ? 2
                                : 1
                        }

                        contentItem: Text {
                            text: page.modeNames[index]
                            color:
                                page.modeIndex === index
                                ? page.accent
                                : page.primaryText

                            font.pixelSize: 12
                            font.weight: Font.DemiBold

                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }

                        onClicked: {
                            page.modeIndex = index
                            page.showControls()
                        }
                    }
                }
            }
        }
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: bottomPanel.top
        anchors.bottomMargin: 14

        z: 18

        visible:
            page.controlsVisible
            && !visualizerService.active

        text:
            visualizerService.enabled
            ? (
                visualizerService.status
                + " • render "
                + Math.round(page.renderScale * 100)
                + "%"
              )
            : "Visualizador desativado nas Configurações"

        color: page.secondaryText
        font.pixelSize: 12
    }

    Timer {
        id: controlsTimer
        interval: 3600
        repeat: false

        onTriggered: {
            if (musicService.playing)
                page.controlsVisible = false
        }
    }
}
