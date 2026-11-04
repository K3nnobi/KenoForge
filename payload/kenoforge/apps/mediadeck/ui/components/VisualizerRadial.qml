import QtQuick

Item {
    id: visual

    property color accent: "#78a9ff"
    property var levels: []
    property url coverUrl: ""

    function requestFrame() {
        if (visible)
            radialCanvas.requestPaint()
    }

    onLevelsChanged: requestFrame()
    onWidthChanged: requestFrame()
    onHeightChanged: requestFrame()

    Canvas {
        id: radialCanvas
        anchors.fill: parent
        renderTarget: Canvas.Image

        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)

            if (!visual.levels || visual.levels.length === 0)
                return

            var cx = width / 2
            var cy = height / 2
            var minSide = Math.min(width, height)
            var baseRadius = minSide * 0.19
            var maxBar = minSide * 0.20
            var n = visual.levels.length

            ctx.lineCap = "round"

            // Círculos guias.
            for (var ring = 0; ring < 3; ++ring) {
                ctx.beginPath()
                ctx.arc(
                    cx,
                    cy,
                    baseRadius + ring * minSide * 0.055,
                    0,
                    Math.PI * 2
                )
                ctx.strokeStyle = Qt.rgba(
                    visual.accent.r,
                    visual.accent.g,
                    visual.accent.b,
                    0.08 + ring * 0.025
                )
                ctx.lineWidth = 1
                ctx.stroke()
            }

            for (var i = 0; i < n; ++i) {
                var angle = -Math.PI / 2 + (Math.PI * 2 * i / n)
                var level = Math.max(0.02, visual.levels[i])

                var inner = baseRadius
                var outer = baseRadius + maxBar * level

                var x1 = cx + Math.cos(angle) * inner
                var y1 = cy + Math.sin(angle) * inner
                var x2 = cx + Math.cos(angle) * outer
                var y2 = cy + Math.sin(angle) * outer

                ctx.beginPath()
                ctx.moveTo(x1, y1)
                ctx.lineTo(x2, y2)
                ctx.strokeStyle = visual.accent
                ctx.lineWidth = Math.max(4, minSide * 0.006)
                ctx.stroke()
            }
        }
    }

    Rectangle {
        anchors.centerIn: parent

        width: Math.min(parent.width, parent.height) * 0.30
        height: width
        radius: width / 2

        color: "#10151d"
        border.color: visual.accent
        border.width: 2
        clip: true

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
            font.pixelSize: Math.max(42, parent.width * 0.28)
        }
    }
}
