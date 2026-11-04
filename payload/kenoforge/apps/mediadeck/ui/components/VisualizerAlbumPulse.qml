import QtQuick

Item {
    id: visual

    property color accent: "#78a9ff"
    property var levels: []
    property url coverUrl: ""

    function average(fromIndex, toIndex) {
        if (!levels || levels.length === 0)
            return 0

        var start = Math.max(0, fromIndex)
        var end = Math.min(levels.length, toIndex)
        var sum = 0
        var count = 0

        for (var i = start; i < end; ++i) {
            sum += levels[i]
            count++
        }

        return count > 0 ? sum / count : 0
    }

    property real bass: average(0, 7)
    property real energy: average(0, 28)

    Repeater {
        model: 3

        delegate: Rectangle {
            required property int index

            anchors.centerIn: parent

            width:
                Math.min(visual.width, visual.height)
                * (
                    0.35
                    + index * 0.105
                    + visual.bass * 0.09
                  )

            height: width
            radius: width / 2

            color: "transparent"
            border.color: visual.accent
            border.width: Math.max(1, 4 - index * 0.6)

            opacity:
                Math.max(
                    0.04,
                    0.26
                    - index * 0.045
                    + visual.energy * 0.12
                )

            Behavior on width {
                NumberAnimation {
                    duration: 110
                }
            }
        }
    }

    Rectangle {
        id: coverFrame

        anchors.centerIn: parent

        width:
            Math.min(parent.width, parent.height)
            * (
                0.31
                + visual.bass * 0.035
              )

        height: width
        radius: width * 0.10

        color: "#10151d"
        border.color: visual.accent
        border.width: 2
        clip: true

        Behavior on width {
            NumberAnimation {
                duration: 100
            }
        }

        Image {
            anchors.fill: parent
            source: visual.coverUrl
            fillMode: Image.PreserveAspectCrop
            visible: String(visual.coverUrl).length > 0
        }

        Text {
            anchors.centerIn: parent
            visible: String(visual.coverUrl).length === 0
            text: "♫"
            color: visual.accent
            font.pixelSize: Math.max(54, parent.width * 0.30)
        }
    }

    Rectangle {
        anchors.centerIn: parent
        width: coverFrame.width * (1.08 + visual.bass * 0.09)
        height: width
        radius: coverFrame.radius * 1.18
        color: "transparent"
        border.color: visual.accent
        border.width: 4
        opacity: 0.10 + visual.bass * 0.30
        z: -1
    }
}
