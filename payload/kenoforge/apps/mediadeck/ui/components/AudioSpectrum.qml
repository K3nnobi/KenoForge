import QtQuick

Rectangle {
    id: spectrum

    property color accent: "#78a9ff"
    property color secondaryText: "#9da7b6"
    property var levels: []
    property var peaks: []
    property bool active: false
    property string statusText: ""

    radius: 18
    color: "#11161d"
    border.color: "#26313e"
    border.width: 1
    clip: true

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 12
        height: 1
        color: "#22ffffff"
    }

    Row {
        id: barsRow

        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        anchors.topMargin: 13
        anchors.bottomMargin: 13

        spacing: 3

        Repeater {
            model: spectrum.levels.length

            delegate: Item {
                required property int index

                width: (
                    barsRow.width -
                    barsRow.spacing *
                    Math.max(0, spectrum.levels.length - 1)
                ) / Math.max(1, spectrum.levels.length)

                height: barsRow.height

                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.horizontalCenter: parent.horizontalCenter

                    width: Math.max(3, parent.width)

                    height: Math.max(
                        2,
                        parent.height *
                        Math.max(
                            0.015,
                            spectrum.levels[index]
                        )
                    )

                    radius: Math.min(
                        width / 2,
                        4
                    )

                    color: spectrum.accent
                    opacity: 0.88
                }

                Rectangle {
                    visible:
                        spectrum.peaks.length > index

                    width: Math.max(
                        3,
                        parent.width
                    )

                    height: 2
                    radius: 1

                    anchors.horizontalCenter:
                        parent.horizontalCenter

                    y: Math.max(
                        0,
                        parent.height -
                        parent.height *
                        spectrum.peaks[index] -
                        2
                    )

                    color: "#e8f1ff"
                    opacity: 0.68
                }
            }
        }
    }

    Text {
        anchors.centerIn: parent
        visible: !spectrum.active

        text: spectrum.statusText

        color: spectrum.secondaryText
        font.pixelSize: 11

        horizontalAlignment:
            Text.AlignHCenter

        wrapMode: Text.WordWrap
        width: parent.width - 30
    }
}
