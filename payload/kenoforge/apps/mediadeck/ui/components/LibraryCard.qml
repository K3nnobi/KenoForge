import QtQuick
import QtQuick.Controls

Rectangle {
    id: card

    property string title: ""
    property string subtitle: ""
    property url coverUrl
    property bool roundCover: false
    property bool selected: false

    property color accent: "#78a9ff"
    property color primaryText: "#f5f7fb"
    property color secondaryText: "#9da7b6"

    signal activated()

    radius: 22
    color: touch.pressed ? "#222a36" : (card.selected ? "#202938" : "#161b23")
    border.color: touch.containsMouse || card.selected ? accent : "#293340"
    border.width: card.selected ? 3 : 1

    Column {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        Rectangle {
            width: parent.width
            height: parent.width
            radius: card.roundCover ? width / 2 : 18
            color: "#11161e"
            border.color: "#293545"
            clip: true

            Image {
                anchors.fill: parent
                source: card.coverUrl
                fillMode: Image.PreserveAspectCrop
                visible: String(card.coverUrl).length > 0
            }

            Text {
                anchors.centerIn: parent
                visible: String(card.coverUrl).length === 0
                text: card.roundCover ? "♪" : "♫"
                color: card.accent
                font.pixelSize: 54
            }
        }

        Text {
            width: parent.width
            text: card.title
            color: card.primaryText
            font.pixelSize: 16
            font.weight: Font.DemiBold
            elide: Text.ElideRight
            horizontalAlignment: card.roundCover
                                 ? Text.AlignHCenter
                                 : Text.AlignLeft
        }

        Text {
            width: parent.width
            text: card.subtitle
            color: card.secondaryText
            font.pixelSize: 12
            elide: Text.ElideRight
            horizontalAlignment: card.roundCover
                                 ? Text.AlignHCenter
                                 : Text.AlignLeft
        }
    }

    MouseArea {
        id: touch
        anchors.fill: parent
        hoverEnabled: true
        onClicked: card.activated()
    }
}
