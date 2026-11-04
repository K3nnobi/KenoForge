import QtQuick

Item {
    id: visual

    property color accent: "#78a9ff"
    property var levels: []

    function requestFrame() {
        if (visible)
            waveCanvas.requestPaint()
    }

    onLevelsChanged: requestFrame()
    onWidthChanged: requestFrame()
    onHeightChanged: requestFrame()

    Canvas {
        id: waveCanvas
        anchors.fill: parent
        renderTarget: Canvas.Image

        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)

            if (!visual.levels || visual.levels.length < 2)
                return

            var center = height * 0.50
            var left = width * 0.06
            var usable = width * 0.88
            var maxAmp = height * 0.28
            var n = visual.levels.length

            ctx.lineCap = "round"
            ctx.lineJoin = "round"

            // Halo externo.
            ctx.beginPath()
            for (var i = 0; i < n; ++i) {
                var x = left + usable * i / (n - 1)
                var a = Math.max(0.01, visual.levels[i])
                var y = center - a * maxAmp

                if (i === 0)
                    ctx.moveTo(x, y)
                else
                    ctx.lineTo(x, y)
            }

            for (var j = n - 1; j >= 0; --j) {
                var x2 = left + usable * j / (n - 1)
                var a2 = Math.max(0.01, visual.levels[j])
                var y2 = center + a2 * maxAmp
                ctx.lineTo(x2, y2)
            }

            ctx.closePath()
            ctx.fillStyle = Qt.rgba(
                visual.accent.r,
                visual.accent.g,
                visual.accent.b,
                0.11
            )
            ctx.fill()

            // Linha superior.
            ctx.beginPath()
            for (var k = 0; k < n; ++k) {
                var x3 = left + usable * k / (n - 1)
                var a3 = Math.max(0.01, visual.levels[k])
                var y3 = center - a3 * maxAmp

                if (k === 0)
                    ctx.moveTo(x3, y3)
                else
                    ctx.lineTo(x3, y3)
            }

            ctx.strokeStyle = visual.accent
            ctx.lineWidth = Math.max(3, width * 0.003)
            ctx.stroke()

            // Linha inferior espelhada.
            ctx.beginPath()
            for (var m = 0; m < n; ++m) {
                var x4 = left + usable * m / (n - 1)
                var a4 = Math.max(0.01, visual.levels[m])
                var y4 = center + a4 * maxAmp

                if (m === 0)
                    ctx.moveTo(x4, y4)
                else
                    ctx.lineTo(x4, y4)
            }

            ctx.strokeStyle = Qt.rgba(
                visual.accent.r,
                visual.accent.g,
                visual.accent.b,
                0.56
            )
            ctx.lineWidth = Math.max(2, width * 0.002)
            ctx.stroke()

            // Linha central.
            ctx.beginPath()
            ctx.moveTo(left, center)
            ctx.lineTo(left + usable, center)
            ctx.strokeStyle = Qt.rgba(1, 1, 1, 0.13)
            ctx.lineWidth = 1
            ctx.stroke()
        }
    }
}
