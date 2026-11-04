import QtQuick
import QtQuick.Controls

Button {
    id: control

    property color hoverAccent: "#78a9ff"
    property real hoverRadius: 15
    property bool hoverGlowEnabled: true
    property bool gamepadSelected: false

    hoverEnabled: true

    // Camada independente do background/contentItem do botão.
    // Assim o efeito continua funcionando mesmo nos botões que
    // possuem desenho customizado em cada página.
    Rectangle {
        anchors.fill: parent
        radius: control.hoverRadius
        color:
            (control.hovered || control.gamepadSelected) && control.hoverGlowEnabled
            ? Qt.rgba(
                  control.hoverAccent.r,
                  control.hoverAccent.g,
                  control.hoverAccent.b,
                  0.07
              )
            : "transparent"

        border.width:
            (control.hovered || control.gamepadSelected)
            ? 2
            : 0

        border.color:
            (control.hovered || control.gamepadSelected)
            ? control.hoverAccent
            : "transparent"

        opacity:
            control.enabled
            ? 1.0
            : 0.45

        z: 1000

        Behavior on border.color {
            ColorAnimation {
                duration: 110
            }
        }

        Behavior on color {
            ColorAnimation {
                duration: 110
            }
        }

        Behavior on border.width {
            NumberAnimation {
                duration: 90
            }
        }
    }
}
