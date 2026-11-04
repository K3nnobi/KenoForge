import QtQuick
import QtQuick.Controls

HoverButton {
    id: button


    hoverAccent: accent
    property color accent: "#78a9ff"
    property color primaryText: "#f5f7fb"
    property bool emphasized: false

    implicitWidth: emphasized ? 58 : 48
    implicitHeight: emphasized ? 48 : 44

    background: Rectangle {
        radius: 16
        color: button.emphasized || button.gamepadSelected
               ? Qt.rgba(button.accent.r, button.accent.g, button.accent.b, 0.22)
               : "#171d27"

        border.color: button.emphasized || button.gamepadSelected
                      ? button.accent
                      : "#2a3342"

        opacity: button.enabled ? 1.0 : 0.45
    }

    contentItem: Text {
        text: button.text
        color: button.primaryText
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pixelSize: button.emphasized ? 17 : 14
        font.weight: Font.DemiBold
    }
}
