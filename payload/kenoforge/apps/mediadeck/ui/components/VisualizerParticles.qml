import QtQuick

Item {
    id: visual

    property color accent: "#78a9ff"
    property var levels: []
    property real phase: 0

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
    property real mids: average(7, 18)
    property real highs: average(18, 28)
    property real energy: (bass * 0.46 + mids * 0.34 + highs * 0.20)

    Timer {
        interval: 50
        running: visual.visible
        repeat: true

        onTriggered: {
            visual.phase += 0.010 + visual.energy * 0.042

            if (visual.phase > 10000)
                visual.phase = 0
        }
    }

    Repeater {
        model: 28

        delegate: Rectangle {
            required property int index

            property real seedA: ((index * 73 + 19) % 101) / 101
            property real seedB: ((index * 47 + 37) % 103) / 103
            property real seedC: ((index * 29 + 11) % 97) / 97

            property real bandValue:
                visual.levels.length > 0
                ? visual.levels[
                      index % visual.levels.length
                  ]
                : 0

            width: 4 + seedC * 8 + bandValue * 10
            height: width
            radius: width / 2

            x: (
                seedA * visual.width
                + Math.sin(
                    visual.phase * (1.0 + seedC)
                    + index * 0.83
                  ) * visual.width * 0.07
            ) % Math.max(1, visual.width)

            y: (
                visual.height
                - (
                    (
                        seedB * visual.height
                        + visual.phase
                          * (
                              45
                              + seedC * 95
                              + visual.energy * 150
                            )
                    ) % Math.max(1, visual.height)
                  )
            )

            color: visual.accent

            opacity:
                0.12
                + seedC * 0.34
                + bandValue * 0.48

            scale:
                0.72
                + bandValue * 0.9

            Behavior on scale {
                NumberAnimation {
                    duration: 80
                }
            }
        }
    }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height) * (0.12 + visual.bass * 0.10)
        height: width
        radius: width / 2
        color: "transparent"
        border.color: visual.accent
        border.width: 2
        opacity: 0.16 + visual.energy * 0.34
    }
}
