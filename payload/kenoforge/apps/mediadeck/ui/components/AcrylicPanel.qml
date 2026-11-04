import QtQuick

Rectangle {
    id: panel

    property color panelColor: "#d6141820"
    property color borderColor: "#28ffffff"

    radius: 26
    color: panelColor
    border.color: borderColor
    border.width: 1

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: parent.radius - 1
        color: "transparent"
        border.color: "#0cffffff"
        border.width: 1
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 14
        height: 1
        color: "#22ffffff"
    }
}
