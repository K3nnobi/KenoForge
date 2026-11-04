import QtQuick

Item {
    id: visual

    property color accent: "#78a9ff"
    property var levels: []
    property var peaks: []

    Rectangle {
        anchors.fill: parent
        color: "transparent"
    }

    Row {
        id: bars

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.top: parent.top

        anchors.leftMargin: Math.max(24, parent.width * 0.05)
        anchors.rightMargin: anchors.leftMargin
        anchors.topMargin: Math.max(40, parent.height * 0.12)
        anchors.bottomMargin: Math.max(40, parent.height * 0.10)

        spacing: Math.max(3, width * 0.003)

        Repeater {
            model: visual.levels.length

            delegate: Item {
                required property int index

                width: (
                    bars.width
                    - bars.spacing
                      * Math.max(0, visual.levels.length - 1)
                ) / Math.max(1, visual.levels.length)

                height: bars.height

                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom

                    width: Math.max(5, parent.width * 0.86)

                    height: Math.max(
                        4,
                        parent.height
                        * Math.max(
                            0.015,
                            visual.levels[index]
                        )
                    )

                    radius: Math.min(
                        width / 2,
                        8
                    )

                    color: visual.accent
                    opacity: 0.84
                }

                Rectangle {
                    visible:
                        visual.peaks.length > index

                    anchors.horizontalCenter: parent.horizontalCenter

                    width: Math.max(5, parent.width * 0.88)
                    height: 3
                    radius: 2

                    y: Math.max(
                        0,
                        parent.height
                        - parent.height
                          * visual.peaks[index]
                        - 3
                    )

                    color: "#f2f7ff"
                    opacity: 0.72
                }

                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom

                    width: Math.max(4, parent.width * 0.78)
                    height: Math.max(
                        2,
                        parent.height
                        * Math.max(
                            0.01,
                            visual.levels[index]
                        )
                        * 0.18
                    )

                    radius: width / 2
                    color: visual.accent
                    opacity: 0.18

                    transform: Scale {
                        yScale: -1
                        origin.y: 0
                    }
                }
            }
        }
    }
}
