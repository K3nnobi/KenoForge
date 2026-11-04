import QtQuick

Item {
    id: visual

    property color accent: "#78a9ff"
    property var levels: []

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

    property real lowValue: average(0, 11)
    property real highValue: average(11, 28)

    function requestFrame() {
        if (visible)
            vuCanvas.requestPaint()
    }

    onLevelsChanged: requestFrame()
    onWidthChanged: requestFrame()
    onHeightChanged: requestFrame()

    Canvas {
        id: vuCanvas
        anchors.fill: parent
        renderTarget: Canvas.Image

        function drawGauge(ctx, cx, cy, radius, value, label) {
            var start = Math.PI * 1.15
            var end = Math.PI * 1.85

            ctx.beginPath()
            ctx.arc(cx, cy, radius, start, end)
            ctx.strokeStyle = Qt.rgba(1, 1, 1, 0.18)
            ctx.lineWidth = Math.max(3, radius * 0.025)
            ctx.stroke()

            for (var i = 0; i <= 10; ++i) {
                var p = i / 10
                var a = start + (end - start) * p

                var r1 = radius * 0.86
                var r2 = radius * (i % 5 === 0 ? 1.0 : 0.95)

                ctx.beginPath()
                ctx.moveTo(
                    cx + Math.cos(a) * r1,
                    cy + Math.sin(a) * r1
                )
                ctx.lineTo(
                    cx + Math.cos(a) * r2,
                    cy + Math.sin(a) * r2
                )

                ctx.strokeStyle =
                    p > 0.78
                    ? Qt.rgba(1.0, 0.42, 0.48, 0.82)
                    : Qt.rgba(
                          visual.accent.r,
                          visual.accent.g,
                          visual.accent.b,
                          0.62
                      )

                ctx.lineWidth = Math.max(2, radius * 0.014)
                ctx.stroke()
            }

            var clamped = Math.max(0, Math.min(1, value))
            var needleAngle = start + (end - start) * clamped

            ctx.beginPath()
            ctx.moveTo(cx, cy)
            ctx.lineTo(
                cx + Math.cos(needleAngle) * radius * 0.78,
                cy + Math.sin(needleAngle) * radius * 0.78
            )
            ctx.strokeStyle = visual.accent
            ctx.lineWidth = Math.max(3, radius * 0.022)
            ctx.stroke()

            ctx.beginPath()
            ctx.arc(cx, cy, radius * 0.055, 0, Math.PI * 2)
            ctx.fillStyle = "#f5f7fb"
            ctx.fill()

            ctx.fillStyle = Qt.rgba(1, 1, 1, 0.78)
            ctx.font = Math.max(15, radius * 0.11) + "px sans-serif"
            ctx.textAlign = "center"
            ctx.fillText(
                label,
                cx,
                cy + radius * 0.24
            )
        }

        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)

            var radius = Math.min(
                width * 0.27,
                height * 0.45
            )

            var cy = height * 0.57

            drawGauge(
                ctx,
                width * 0.29,
                cy,
                radius,
                visual.lowValue,
                "LOW"
            )

            drawGauge(
                ctx,
                width * 0.71,
                cy,
                radius,
                visual.highValue,
                "HIGH"
            )
        }
    }
}
