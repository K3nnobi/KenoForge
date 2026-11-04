import QtQuick
import QtQuick.Controls

HoverButton {
    id: button


    hoverAccent: accent
    property color accent: "#78a9ff"
    property color primaryText: "#f5f7fb"

    implicitHeight: 46
    implicitWidth: Math.max(110, contentItem.implicitWidth + 30)

    background: Rectangle {
        radius: 15
        color: button.down ? "#243048" : (button.gamepadSelected ? "#1d2b40" : "#171d27")
        border.color: (button.hovered || button.gamepadSelected) ? button.accent : "#2a3342"
    }

    contentItem: Text {
        text: button.text
        color: button.primaryText
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pixelSize: 15
        font.weight: Font.Medium
    }
}
