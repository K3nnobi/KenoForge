import QtQuick
import QtQuick.Layouts

Rectangle {
    id: row

    property string title: ""
    property string subtitle: ""
    property string durationText: ""
    property url coverUrl
    property bool favorite: false
    property bool active: false
    property bool playing: false
    property bool selected: false
    property string path: ""

    property color accent: "#78a9ff"
    property color nowPlayingAccent: "#a970ff"
    property color primaryText: "#f5f7fb"
    property color secondaryText: "#9da7b6"

    readonly property bool hovered:
        row.selected
        || rowHover.hovered
        || mainHover.hovered
        || playHover.hovered
        || playlistHover.hovered
        || queueHover.hovered
        || favoriteHover.hovered

    signal activated()
    signal favoriteRequested()
    signal queueRequested()
    signal playlistRequested()

    height: 74
    radius: 17

    // Navigation focus and the currently playing track are intentionally
    // different visual states. Only the focus gets the strong blue outline;
    // playback is a quieter violet marker/background.
    color: {
        if (row.selected)
            return Qt.rgba(accent.r, accent.g, accent.b, 0.18)
        if (row.active)
            return Qt.rgba(nowPlayingAccent.r, nowPlayingAccent.g, nowPlayingAccent.b, 0.14)
        return row.hovered
               ? Qt.rgba(accent.r, accent.g, accent.b, 0.09)
               : "#151a22"
    }

    border.color:
        row.selected ? accent
        : (row.active ? nowPlayingAccent
        : (row.hovered ? accent : "#24303d"))

    border.width:
        row.selected ? 3 : (row.active ? 2 : (row.hovered ? 2 : 1))

    Behavior on color {
        ColorAnimation { duration: 110 }
    }

    Behavior on border.color {
        ColorAnimation { duration: 110 }
    }

    Behavior on border.width {
        NumberAnimation { duration: 90 }
    }

    // Sem filtro de dispositivo: funciona com mouse e touchpad.
    HoverHandler {
        id: rowHover
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        spacing: 8

        // Área informativa da faixa. Não reproduz ao clicar/tocar.
        Rectangle {
            id: mainArea

            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 14

            color:
                mainHover.hovered
                ? Qt.rgba(
                      row.accent.r,
                      row.accent.g,
                      row.accent.b,
                      0.055
                  )
                : "transparent"

            Behavior on color {
                ColorAnimation { duration: 100 }
            }

            HoverHandler {
                id: mainHover
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 5
                anchors.rightMargin: 8
                spacing: 12

                Rectangle {
                    Layout.preferredWidth: 50
                    Layout.preferredHeight: 50
                    radius: 13

                    color:
                        row.active
                        ? Qt.rgba(
                              row.nowPlayingAccent.r,
                              row.nowPlayingAccent.g,
                              row.nowPlayingAccent.b,
                              0.22
                          )
                        : "#202732"

                    clip: true

                    Image {
                        anchors.fill: parent
                        source: row.coverUrl
                        fillMode: Image.PreserveAspectCrop
                        visible: String(row.coverUrl).length > 0
                    }

                    Text {
                        anchors.centerIn: parent
                        visible: String(row.coverUrl).length === 0
                        text: "♫"
                        color: row.active ? row.nowPlayingAccent : row.accent
                        font.pixelSize: 19
                    }

                    Rectangle {
                        visible: row.active
                        width: 19
                        height: 19
                        radius: 10
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: 3
                        color: row.nowPlayingAccent
                        border.color: "#ddffffff"
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: row.playing ? "▶" : "Ⅱ"
                            color: "white"
                            font.pixelSize: 9
                            font.weight: Font.Bold
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        Layout.fillWidth: true
                        text: row.title
                        color: row.primaryText
                        font.pixelSize: 16
                        font.weight:
                            row.active
                            ? Font.DemiBold
                            : Font.Medium
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: row.subtitle
                        color: row.secondaryText
                        font.pixelSize: 13
                        elide: Text.ElideRight
                    }
                }

                Text {
                    text: row.durationText
                    color: row.secondaryText
                    font.pixelSize: 12
                }
            }
        }

        // ÚNICO controle que inicia a música.
        Rectangle {
            id: playButton

            Layout.preferredWidth: 44
            Layout.preferredHeight: 44
            radius: 14

            color:
                playTap.pressed
                ? Qt.rgba(row.accent.r, row.accent.g, row.accent.b, 0.32)
                : (
                    playHover.hovered
                    ? Qt.rgba(row.accent.r, row.accent.g, row.accent.b, 0.22)
                    : (
                        row.active
                        ? Qt.rgba(row.nowPlayingAccent.r, row.nowPlayingAccent.g, row.nowPlayingAccent.b, 0.14)
                        : "#171d27"
                    )
                )

            border.color:
                playHover.hovered
                ? row.accent
                : row.active
                ? row.nowPlayingAccent
                : "#354153"

            border.width:
                playHover.hovered ? 2 : 1

            Behavior on color {
                ColorAnimation { duration: 100 }
            }

            Behavior on border.color {
                ColorAnimation { duration: 100 }
            }

            Behavior on border.width {
                NumberAnimation { duration: 80 }
            }

            HoverHandler {
                id: playHover
            }

            Text {
                anchors.centerIn: parent
                text: "▶"

                color:
                    playHover.hovered
                    ? row.accent
                    : row.active
                    ? row.nowPlayingAccent
                    : row.primaryText

                font.pixelSize: 18
                leftPadding: 2

                Behavior on color {
                    ColorAnimation { duration: 100 }
                }
            }

            TapHandler {
                id: playTap
                onTapped: row.activated()
            }
        }

        // + = playlist
        Rectangle {
            id: playlistButton

            Layout.preferredWidth: 42
            Layout.preferredHeight: 42
            radius: 13

            color:
                playlistTap.pressed
                ? "#293b57"
                : (
                    playlistHover.hovered
                    ? Qt.rgba(row.accent.r, row.accent.g, row.accent.b, 0.20)
                    : "#172130"
                )

            border.color:
                playlistHover.hovered
                ? Qt.lighter(row.accent, 1.35)
                : row.accent

            border.width:
                playlistHover.hovered ? 2 : 1

            Behavior on color {
                ColorAnimation { duration: 100 }
            }

            Behavior on border.color {
                ColorAnimation { duration: 100 }
            }

            Behavior on border.width {
                NumberAnimation { duration: 80 }
            }

            HoverHandler {
                id: playlistHover
            }

            Text {
                anchors.centerIn: parent
                text: "+"
                color: row.accent
                font.pixelSize: 23
                font.weight: Font.Bold
            }

            TapHandler {
                id: playlistTap
                onTapped: row.playlistRequested()
            }
        }

        // ≡ = fila
        Rectangle {
            id: queueButton

            Layout.preferredWidth: 42
            Layout.preferredHeight: 42
            radius: 13

            color:
                queueTap.pressed
                ? "#29313d"
                : (
                    queueHover.hovered
                    ? Qt.rgba(row.accent.r, row.accent.g, row.accent.b, 0.16)
                    : "#171d27"
                )

            border.color:
                queueHover.hovered
                ? row.accent
                : "#354153"

            border.width:
                queueHover.hovered ? 2 : 1

            Behavior on color {
                ColorAnimation { duration: 100 }
            }

            Behavior on border.color {
                ColorAnimation { duration: 100 }
            }

            Behavior on border.width {
                NumberAnimation { duration: 80 }
            }

            HoverHandler {
                id: queueHover
            }

            Text {
                anchors.centerIn: parent
                text: "≡"

                color:
                    queueHover.hovered
                    ? row.accent
                    : row.secondaryText

                font.pixelSize: 20

                Behavior on color {
                    ColorAnimation { duration: 100 }
                }
            }

            TapHandler {
                id: queueTap
                onTapped: row.queueRequested()
            }
        }

        // ♡ / ♥ = favorito
        Rectangle {
            id: favoriteButton

            Layout.preferredWidth: 42
            Layout.preferredHeight: 42
            radius: 13

            color:
                favoriteTap.pressed
                ? "#35252c"
                : (
                    favoriteHover.hovered
                    ? Qt.rgba(1.0, 0.48, 0.54, 0.14)
                    : "#171d27"
                )

            border.color:
                favoriteHover.hovered
                ? "#ff7b8a"
                : (
                    row.favorite
                    ? "#8a4450"
                    : "#354153"
                )

            border.width:
                favoriteHover.hovered ? 2 : 1

            Behavior on color {
                ColorAnimation { duration: 100 }
            }

            Behavior on border.color {
                ColorAnimation { duration: 100 }
            }

            Behavior on border.width {
                NumberAnimation { duration: 80 }
            }

            HoverHandler {
                id: favoriteHover
            }

            Text {
                anchors.centerIn: parent
                text: row.favorite ? "♥" : "♡"

                color:
                    row.favorite || favoriteHover.hovered
                    ? "#ff7b8a"
                    : row.secondaryText

                font.pixelSize: 20

                Behavior on color {
                    ColorAnimation { duration: 100 }
                }
            }

            TapHandler {
                id: favoriteTap
                onTapped: row.favoriteRequested()
            }
        }
    }
}
