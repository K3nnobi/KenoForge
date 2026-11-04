import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "components"

Item {
    id: page

    property color accent
    property color panel
    property color panelAlt
    property color line
    property color primaryText
    property color secondaryText

    // The KenoForge desktop host uses mouse and standard Qt keyboard focus.
    property bool controllerNavigation: false

    property string searchText: ""
    property int currentSection: 0
    property string pendingPlaylistPath: ""
    property string selectedPlaylist: ""
    readonly property bool compactLayout: page.height <= 650 || page.width <= 1450
    readonly property color nowPlayingAccent: "#a970ff"


    // 0 = abas da biblioteca, 1 = conteúdo da aba atual, 2 = player lateral
    property int gamepadZone: 0
    // 0 shuffle, 1 anterior, 2 play/pause, 3 próxima, 4 repetir, 5 visualização
    property int playerControlIndex: 2

    function contentLength() {
        if (currentSection === 0) return musicService.songs.length
        if (currentSection === 1) return musicService.albums.length
        if (currentSection === 2) return musicService.artists.length
        if (currentSection === 3) return musicService.favoriteSongs.length
        if (currentSection === 4) return musicService.recentSongs.length
        if (currentSection === 5) return musicService.playlists.length
        return musicService.queueSongs.length
    }

    function contentColumns() {
        if (currentSection === 1) return albumsGrid.columns
        if (currentSection === 2) return artistsGrid.columns
        if (currentSection === 5) return playlistsGrid.columns
        return 1
    }

    function contentIndex() {
        if (currentSection === 0) return songList.currentIndex
        if (currentSection === 1) return albumsGrid.currentIndex
        if (currentSection === 2) return artistsGrid.currentIndex
        if (currentSection === 3) return favoritesList.currentIndex
        if (currentSection === 4) return recentList.currentIndex
        if (currentSection === 5) return playlistsGrid.currentIndex
        return queueList.currentIndex
    }

    function setContentIndex(value) {
        var n = contentLength()
        var v = n > 0 ? Math.max(0, Math.min(n - 1, value)) : -1
        if (currentSection === 0) { songList.currentIndex = v; if (v >= 0) songList.positionViewAtIndex(v, ListView.Contain) }
        else if (currentSection === 1) { albumsGrid.currentIndex = v; if (v >= 0) albumsGrid.positionViewAtIndex(v, GridView.Contain) }
        else if (currentSection === 2) { artistsGrid.currentIndex = v; if (v >= 0) artistsGrid.positionViewAtIndex(v, GridView.Contain) }
        else if (currentSection === 3) { favoritesList.currentIndex = v; if (v >= 0) favoritesList.positionViewAtIndex(v, ListView.Contain) }
        else if (currentSection === 4) { recentList.currentIndex = v; if (v >= 0) recentList.positionViewAtIndex(v, ListView.Contain) }
        else if (currentSection === 5) { playlistsGrid.currentIndex = v; if (v >= 0) playlistsGrid.positionViewAtIndex(v, GridView.Contain) }
        else { queueList.currentIndex = v; if (v >= 0) queueList.positionViewAtIndex(v, ListView.Contain) }
    }

    function revealCurrentTrack() {
        if (page.currentSection !== 0 || page.searchText.trim().length > 0)
            return
        var idx = musicService.currentIndex
        if (idx < 0 || idx >= musicService.songs.length)
            return
        songList.currentIndex = idx
        Qt.callLater(function() {
            songList.positionViewAtIndex(idx, ListView.Center)
        })
    }

    function currentContentItem() {
        var i = contentIndex()
        if (i < 0 || i >= contentLength()) return null
        if (currentSection === 0) return musicService.songs[i]
        if (currentSection === 1) return musicService.albums[i]
        if (currentSection === 2) return musicService.artists[i]
        if (currentSection === 3) return musicService.favoriteSongs[i]
        if (currentSection === 4) return musicService.recentSongs[i]
        if (currentSection === 5) return musicService.playlists[i]
        return musicService.queueSongs[i]
    }

    function selectSection(delta) {
        currentSection = (currentSection + delta + 7) % 7
        setContentIndex(contentLength() > 0 ? 0 : -1)
    }

    function enterPlayerZone() {
        gamepadZone = 2
        // Play/Pause é o foco inicial mais previsível ao entrar no player.
        playerControlIndex = 2
    }

    function activatePlayerControl() {
        if (playerControlIndex === 0) musicService.toggleShuffle()
        else if (playerControlIndex === 1) musicService.previous()
        else if (playerControlIndex === 2) musicService.playPause()
        else if (playerControlIndex === 3) musicService.next()
        else if (playerControlIndex === 4) musicService.toggleRepeat()
        else if (playerControlIndex === 5) {
            if (!visualizerService.enabled) {
                page.showToast("Ative o visualizador nas Configurações.")
                return
            }
            if (musicService.hasCurrent)
                page.visualizerRequested()
        }
    }

    function gamepadLeft() {
        if (playlistPicker.opened || newPlaylistDialog.opened) return
        if (gamepadZone === 0) { selectSection(-1); return }
        if (gamepadZone === 2) {
            if (playerControlIndex > 0) playerControlIndex--
            else gamepadZone = 1
            return
        }
        if (contentColumns() > 1)
            setContentIndex(contentIndex() - 1)
    }

    function gamepadRight() {
        if (playlistPicker.opened || newPlaylistDialog.opened) return
        if (gamepadZone === 0) { selectSection(1); return }
        if (gamepadZone === 2) {
            playerControlIndex = Math.min(5, playerControlIndex + 1)
            return
        }
        if (contentColumns() > 1) {
            var next = contentIndex() + 1
            var cols = contentColumns()
            if (contentIndex() >= 0 && (contentIndex() % cols) < cols - 1 && next < contentLength())
                setContentIndex(next)
            else
                enterPlayerZone()
        } else {
            enterPlayerZone()
        }
    }

    function gamepadUp() {
        if (playlistPicker.opened) { playlistPicker.moveGamepad(-1); return }
        if (newPlaylistDialog.opened) return
        if (gamepadZone === 2) return
        if (gamepadZone === 0) return
        var next = contentIndex() - contentColumns()
        if (next < 0) gamepadZone = 0
        else setContentIndex(next)
    }

    function gamepadDown() {
        if (playlistPicker.opened) { playlistPicker.moveGamepad(1); return }
        if (newPlaylistDialog.opened) return
        if (gamepadZone === 2) return
        if (gamepadZone === 0) {
            if (contentLength() > 0) { gamepadZone = 1; if (contentIndex() < 0) setContentIndex(0) }
            return
        }
        setContentIndex(contentIndex() + contentColumns())
    }

    function gamepadConfirm() {
        if (playlistPicker.opened) { playlistPicker.activateGamepad(); return }
        if (newPlaylistDialog.opened) { if (playlistNameField.text.trim().length > 0) createPlaylistFromDialog(); return }
        if (gamepadZone === 0) { gamepadDown(); return }
        if (gamepadZone === 2) { activatePlayerControl(); return }
        var item = currentContentItem()
        if (!item) return
        if (currentSection === 0) musicService.playIndex(contentIndex())
        else if (currentSection === 1) musicService.playAlbum(item.name)
        else if (currentSection === 2) musicService.playArtist(item.name)
        else if (currentSection === 3 || currentSection === 4 || currentSection === 6) musicService.playPath(item.path)
        else if (currentSection === 5) musicService.playPlaylist(item.name)
    }

    function gamepadSecondary() {
        var item = currentContentItem()
        if (gamepadZone !== 1 || !item) return
        if (currentSection === 0 || currentSection === 3 || currentSection === 4)
            musicService.addToQueue(item.path)
        else if (currentSection === 6)
            musicService.removeQueueIndex(contentIndex())
    }

    function gamepadFavorite() {
        var item = currentContentItem()
        if (gamepadZone === 1 && item && (currentSection === 0 || currentSection === 3 || currentSection === 4))
            musicService.toggleFavoritePath(item.path)
        else if (musicService.hasCurrent)
            musicService.toggleCurrentFavorite()
    }

    function gamepadSelect() {
        var item = currentContentItem()
        if (gamepadZone === 1 && item && (currentSection === 0 || currentSection === 3 || currentSection === 4))
            requestPlaylistFor(item.path)
        else if (musicService.hasCurrent && visualizerService.enabled)
            page.visualizerRequested()
    }

    function gamepadMenu() { musicService.playPause() }

    function gamepadBack() {
        if (newPlaylistDialog.opened) { newPlaylistDialog.close(); return true }
        if (playlistPicker.opened) { page.pendingPlaylistPath = ""; playlistPicker.close(); return true }
        if (gamepadZone === 2) { gamepadZone = 1; return true }
        if (gamepadZone === 1) { gamepadZone = 0; return true }
        return false
    }

    signal visualizerRequested()

    onCurrentSectionChanged: {
        if (currentSection === 0)
            revealCurrentTrack()
    }

    Connections {
        target: musicService
        function onCurrentChanged() { page.revealCurrentTrack() }
    }

    Component.onCompleted: Qt.callLater(function() { page.revealCurrentTrack() })

    function normalized(text) {
        return String(text || "").toLowerCase()
    }

    function requestPlaylistFor(path) {
        page.pendingPlaylistPath = String(path || "")

        if (page.pendingPlaylistPath.length === 0) {
            showToast("Não foi possível identificar esta música.")
            return
        }

        // Fluxo único e previsível: o + SEMPRE abre este seletor.
        playlistPicker.open()
    }

    function showToast(message) {
        toastText.text = message
        toast.open()
        toastTimer.restart()
    }

    function createPlaylistFromDialog() {
        var name = playlistNameField.text.trim()

        if (name.length === 0)
            return

        if (!musicService.createPlaylist(name)) {
            showToast("Não foi possível criar a playlist.")
            return
        }

        var added = false

        if (page.pendingPlaylistPath.length > 0) {
            added = musicService.addPathToPlaylist(
                name,
                page.pendingPlaylistPath
            )
        }

        page.pendingPlaylistPath = ""
        playlistNameField.text = ""
        newPlaylistDialog.close()

        if (added)
            showToast("Música adicionada à playlist “" + name + "”.")
        else
            showToast("Playlist “" + name + "” criada.")
    }

    FolderDialog {
        id: folderDialog
        title: "Escolha a pasta da biblioteca de músicas"
        onAccepted: musicService.setMusicFolder(selectedFolder.toString())
    }

    Popup {
        id: newPlaylistDialog

        modal: true
        focus: true

        width: Math.min(440, page.width - 40)
        height: 270

        anchors.centerIn: Overlay.overlay
        closePolicy: Popup.CloseOnEscape


        background: Rectangle {
            radius: 24
            color: "#f0181e28"
            border.color: "#3cffffff"
            border.width: 1
        }

        Overlay.modal: Rectangle {
            color: "#98000000"

            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.AllButtons
                onPressed: function(mouse) {
                    mouse.accepted = true
                }
                onReleased: function(mouse) {
                    mouse.accepted = true
                }
                onClicked: function(mouse) {
                    mouse.accepted = true
                }
            }
        }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 22
            spacing: 13

            Text {
                text: "Nova playlist"
                color: page.primaryText
                font.pixelSize: 22
                font.weight: Font.DemiBold
            }

            Text {
                text: page.pendingPlaylistPath.length > 0
                      ? "Crie a playlist e esta música será adicionada automaticamente."
                      : "Digite um nome para a nova playlist."
                color: page.secondaryText
                font.pixelSize: 13
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            TextField {
                id: playlistNameField

                Layout.fillWidth: true
                implicitHeight: 54

                placeholderText: "Ex.: Favoritas, Rock, Viagem..."
                color: "#f5f7fb"
                placeholderTextColor: "#738093"
                selectionColor: page.accent
                selectedTextColor: "#07101b"

                font.pixelSize: 16
                selectByMouse: true

                leftPadding: 15
                rightPadding: 15

                background: Rectangle {
                    radius: 15
                    color: "#0b1017"
                    border.color: playlistNameField.activeFocus
                                  ? page.accent
                                  : "#334052"
                    border.width: playlistNameField.activeFocus ? 2 : 1
                }

                Keys.onReturnPressed: page.createPlaylistFromDialog()
                Keys.onEnterPressed: page.createPlaylistFromDialog()
            }

            Item {
                Layout.fillHeight: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                HoverButton {
                    hoverAccent: page.accent
                    hoverRadius: 15
                    Layout.fillWidth: true
                    implicitHeight: 50

                    background: Rectangle {
                        radius: 15
                        color: parent.down ? "#252d38" : "#141a22"
                        border.color: "#334052"
                        border.width: 1
                    }

                    contentItem: Text {
                        text: "Cancelar"
                        color: page.secondaryText
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: 15
                        font.weight: Font.Medium
                    }

                    onClicked: {
                        playlistNameField.text = ""
                        page.pendingPlaylistPath = ""
                        newPlaylistDialog.close()
                    }
                }

                HoverButton {
                    hoverAccent: page.accent
                    hoverRadius: 15
                    Layout.fillWidth: true
                    implicitHeight: 50
                    enabled: playlistNameField.text.trim().length > 0

                    background: Rectangle {
                        radius: 15
                        color: parent.enabled
                               ? (parent.down ? "#31547f" : "#223c5d")
                               : "#151b23"
                        border.color: parent.enabled
                                      ? page.accent
                                      : "#293440"
                        border.width: 1
                    }

                    contentItem: Text {
                        text: "Criar"
                        color: parent.enabled
                               ? page.primaryText
                               : "#738093"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }

                    onClicked: page.createPlaylistFromDialog()
                }
            }
        }

        onOpened: {
            playlistNameField.forceActiveFocus()
        }

        onClosed: {
            playlistNameField.text = ""
        }
    }

    Popup {
        id: playlistPicker

        modal: true
        focus: true

        property int visibleRows: Math.min(
            5,
            Math.max(1, musicService.playlists.length)
        )

        property int gamepadIndex: 0

        function maxGamepadIndex() { return musicService.playlists.length + 1 }
        function moveGamepad(delta) {
            var max = maxGamepadIndex()
            gamepadIndex = (gamepadIndex + delta + max + 1) % (max + 1)
            if (gamepadIndex >= 1 && gamepadIndex <= musicService.playlists.length) {
                playlistList.currentIndex = gamepadIndex - 1
                playlistList.positionViewAtIndex(playlistList.currentIndex, ListView.Contain)
            }
        }
        function activateGamepad() {
            if (gamepadIndex === 0) {
                close()
                newPlaylistDialog.open()
                return
            }
            if (gamepadIndex === maxGamepadIndex()) {
                page.pendingPlaylistPath = ""
                close()
                return
            }
            var item = musicService.playlists[gamepadIndex - 1]
            var ok = musicService.addPathToPlaylist(item.name, page.pendingPlaylistPath)
            page.pendingPlaylistPath = ""
            close()
            page.showToast(ok ? "Música adicionada à playlist “" + item.name + "”." : "Não foi possível adicionar à playlist.")
        }

        width: Math.min(460, page.width - 40)
        height: 238 + (visibleRows * 60)

        anchors.centerIn: Overlay.overlay
        closePolicy: Popup.CloseOnEscape

        onOpened: gamepadIndex = 0

        background: Rectangle {
            radius: 24
            color: "#f0181e28"
            border.color: "#3cffffff"
            border.width: 1
        }

        Overlay.modal: Rectangle {
            color: "#98000000"

            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.AllButtons

                onPressed: function(mouse) {
                    mouse.accepted = true
                }

                onReleased: function(mouse) {
                    mouse.accepted = true
                }

                onClicked: function(mouse) {
                    mouse.accepted = true
                }
            }
        }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 12

            Text {
                text: "Adicionar à playlist"
                color: page.primaryText
                font.pixelSize: 21
                font.weight: Font.DemiBold
            }

            Text {
                text: musicService.playlists.length > 0
                      ? "Escolha uma playlist para esta música."
                      : "Você ainda não criou nenhuma playlist."
                color: page.secondaryText
                font.pixelSize: 13
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            HoverButton {
                hoverAccent: page.accent
                hoverRadius: 15
                Layout.fillWidth: true
                implicitHeight: 52
                gamepadSelected: page.controllerNavigation && playlistPicker.gamepadIndex === 0

                background: Rectangle {
                    radius: 15
                    color: parent.down ? "#29405f" : "#1d2b40"
                    border.color: page.accent
                    border.width: 1
                }

                contentItem: Row {
                    anchors.centerIn: parent
                    spacing: 9

                    Text {
                        text: "+"
                        color: page.accent
                        font.pixelSize: 22
                        font.weight: Font.Bold
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        text: "Criar nova playlist"
                        color: page.primaryText
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                onClicked: {
                    playlistPicker.close()
                    newPlaylistDialog.open()
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: "#24ffffff"
            }

            ListView {
                id: playlistList

                Layout.fillWidth: true
                Layout.preferredHeight: playlistPicker.visibleRows * 60

                model: musicService.playlists
                currentIndex: musicService.playlists.length > 0 ? 0 : -1
                spacing: 8
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                ScrollBar.vertical: ScrollBar {
                    policy: musicService.playlists.length > 5
                            ? ScrollBar.AlwaysOn
                            : ScrollBar.AlwaysOff
                }

                delegate: HoverButton {
                    required property int index
                    required property var modelData
                    gamepadSelected: page.controllerNavigation && playlistPicker.gamepadIndex === index + 1

                    width: playlistList.width
                    height: 52

                    background: Rectangle {
                        radius: 15
                        color: parent.down ? "#27364a" : "#151b24"
                        border.color: parent.hovered
                                      ? page.accent
                                      : "#334052"
                        border.width: 1
                    }

                    contentItem: RowLayout {
                        spacing: 10

                        Text {
                            text: "♫"
                            color: page.accent
                            font.pixelSize: 17
                        }

                        Text {
                            text: modelData.name
                            color: page.primaryText
                            font.pixelSize: 15
                            font.weight: Font.Medium
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }

                        Text {
                            text: modelData.count + " faixas"
                            color: page.secondaryText
                            font.pixelSize: 12
                        }
                    }

                    onClicked: {
                        var playlistName = modelData.name
                        var ok = musicService.addPathToPlaylist(
                            playlistName,
                            page.pendingPlaylistPath
                        )

                        page.pendingPlaylistPath = ""
                        playlistPicker.close()

                        if (ok) {
                            page.showToast(
                                "Música adicionada à playlist “" +
                                playlistName + "”."
                            )
                        } else {
                            page.showToast(
                                "Não foi possível adicionar à playlist."
                            )
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: musicService.playlists.length === 0
                    text: "Nenhuma playlist criada"
                    color: page.secondaryText
                    font.pixelSize: 14
                }
            }

            Item {
                Layout.fillHeight: true
            }

            HoverButton {
                hoverAccent: page.accent
                hoverRadius: 15
                Layout.fillWidth: true
                implicitHeight: 48
                gamepadSelected: page.controllerNavigation && playlistPicker.gamepadIndex === playlistPicker.maxGamepadIndex()

                background: Rectangle {
                    radius: 14
                    color: parent.down ? "#252c36" : "#12171f"
                    border.color: "#303b49"
                    border.width: 1
                }

                contentItem: Text {
                    text: "Cancelar"
                    color: page.secondaryText
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: 14
                    font.weight: Font.Medium
                }

                onClicked: {
                    page.pendingPlaylistPath = ""
                    playlistPicker.close()
                }
            }
        }
    }

    Popup {
        id: toast
        modal: false
        focus: false
        width: Math.min(430, page.width - 40)
        height: 58
        x: (page.width - width) / 2
        y: page.height - height - 18
        closePolicy: Popup.NoAutoClose
        z: 1000

        background: Rectangle {
            radius: 18
            color: "#f01b2430"
            border.color: page.accent
            border.width: 1
        }

        contentItem: Text {
            id: toastText
            color: page.primaryText
            font.pixelSize: 14
            font.weight: Font.Medium
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
    }

    Timer {
        id: toastTimer
        interval: 2200
        repeat: false
        onTriggered: toast.close()
    }

    RowLayout {
        anchors.fill: parent
        spacing: page.compactLayout ? 10 : 16

        AcrylicPanel {
            Layout.fillHeight: true
            Layout.fillWidth: true
            Layout.minimumWidth: page.width * 0.58

            panelColor: page.panel
            borderColor: page.line

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: page.compactLayout ? 12 : 18
                spacing: page.compactLayout ? 8 : 12

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: page.compactLayout ? 46 : 56
                    spacing: 12

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1

                        Text {
                            text: "Biblioteca"
                            color: page.primaryText
                            font.pixelSize: page.compactLayout ? 23 : 28
                            font.weight: Font.DemiBold
                        }

                        Text {
                            text: musicService.songCount + " faixas • " +
                                  (musicService.musicFolder.length > 0
                                   ? musicService.musicFolder
                                   : "nenhuma pasta selecionada")
                            color: page.secondaryText
                            font.pixelSize: 12
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                    }

                    TouchButton {
                        text: "Escolher pasta"
                        accent: page.accent
                        primaryText: page.primaryText
                        onClicked: folderDialog.open()
                    }

                    TouchButton {
                        text: "Atualizar"
                        accent: page.accent
                        primaryText: page.primaryText
                        onClicked: musicService.scanLibrary()
                    }

                    HoverButton {
                        hoverAccent: page.accent
                        hoverRadius: 16

                        implicitWidth: 126
                        implicitHeight: 48

                        enabled: musicService.songCount > 0

                        background: Rectangle {
                            radius: 16

                            color: musicService.shuffle
                                   ? Qt.rgba(page.accent.r,
                                             page.accent.g,
                                             page.accent.b,
                                             0.22)
                                   : "#171d27"

                            border.color: musicService.shuffle
                                          ? page.accent
                                          : "#334052"

                            border.width: musicService.shuffle ? 2 : 1
                        }

                        contentItem: Row {
                            anchors.centerIn: parent
                            spacing: 8

                            Text {
                                text: "⤨"
                                color: musicService.shuffle
                                       ? page.accent
                                       : page.primaryText
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                text: "Aleatório"
                                color: musicService.shuffle
                                       ? page.accent
                                       : page.primaryText
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        ToolTip.visible: hovered
                        ToolTip.text: musicService.shuffle
                                      ? "Modo aleatório ativo — tocar outra faixa aleatória"
                                      : "Ativar modo aleatório e tocar uma faixa"

                        onClicked: musicService.playRandom()
                    }
                }

                Flickable {
                    Layout.fillWidth: true
                    Layout.preferredHeight: page.compactLayout ? 42 : 48
                    contentWidth: sectionRow.width
                    clip: true

                    Row {
                        id: sectionRow
                        spacing: 8

                        Repeater {
                            model: [
                                "Faixas", "Álbuns", "Artistas",
                                "Favoritos", "Recentes", "Playlists", "Fila"
                            ]

                            delegate: HoverButton {
                                required property string modelData
                                required property int index

                                width: page.compactLayout ? 104 : 112
                                height: page.compactLayout ? 38 : 42
                                gamepadSelected: page.controllerNavigation && page.gamepadZone === 0 && page.currentSection === index

                                background: Rectangle {
                                    radius: 14
                                    color: page.currentSection === index
                                           ? "#25354d"
                                           : "#151a22"
                                    border.color: page.currentSection === index
                                                  ? page.accent
                                                  : "#283240"
                                }

                                contentItem: Text {
                                    text: modelData
                                    color: page.currentSection === index
                                           ? page.primaryText
                                           : page.secondaryText
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    font.pixelSize: page.compactLayout ? 11 : 13
                                    font.weight: page.currentSection === index
                                                 ? Font.DemiBold
                                                 : Font.Medium
                                }

                                onClicked: page.currentSection = index
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: page.currentSection === 0 ? (page.compactLayout ? 42 : 50) : 0
                    visible: page.currentSection === 0
                    radius: 16
                    color: "#141a23"
                    border.color: page.line

                    TextField {
                        anchors.fill: parent
                        anchors.leftMargin: 14
                        anchors.rightMargin: 14
                        placeholderText: "Buscar música, artista ou álbum..."
                        color: page.primaryText
                        placeholderTextColor: page.secondaryText
                        font.pixelSize: 15
                        background: Item {}
                        onTextChanged: page.searchText = text
                    }
                }

                StackLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    currentIndex: page.currentSection

                    // Faixas
                    ListView {
                        id: songList
                        model: musicService.songs
                        currentIndex: musicService.songs.length > 0 ? 0 : -1
                        clip: true
                        spacing: 7
                        boundsBehavior: Flickable.StopAtBounds

                        delegate: SongRow {
                            required property var modelData
                            required property int index

                            width: songList.width
                            path: modelData.path
                            title: modelData.title
                            subtitle: {
                                if (modelData.artist && modelData.album)
                                    return modelData.artist + " • " + modelData.album
                                if (modelData.artist)
                                    return modelData.artist
                                if (modelData.album)
                                    return modelData.album
                                return modelData.fileName
                            }
                            durationText: modelData.durationText
                            coverUrl: modelData.coverUrl
                            favorite: modelData.favorite
                            active: index === musicService.currentIndex
                            playing: active && musicService.playing
                            accent: page.accent
                            nowPlayingAccent: page.nowPlayingAccent
                            primaryText: page.primaryText
                            secondaryText: page.secondaryText
                            selected: page.controllerNavigation && page.gamepadZone === 1 && page.currentSection === 0 && index === songList.currentIndex

                            visible: {
                                var query = page.normalized(page.searchText)
                                if (query.length === 0)
                                    return true
                                var source =
                                    page.normalized(modelData.title) + " " +
                                    page.normalized(modelData.artist) + " " +
                                    page.normalized(modelData.album) + " " +
                                    page.normalized(modelData.fileName)
                                return source.indexOf(query) !== -1
                            }

                            height: visible ? 74 : 0

                            onActivated: musicService.playIndex(index)
                            onFavoriteRequested:
                                musicService.toggleFavoritePath(modelData.path)
                            onQueueRequested:
                                musicService.addToQueue(modelData.path)
                            onPlaylistRequested:
                                page.requestPlaylistFor(modelData.path)
                        }
                    }

                    // Álbuns
                    GridView {
                        id: albumsGrid
                        model: musicService.albums
                        currentIndex: musicService.albums.length > 0 ? 0 : -1
                        clip: true
                        property int columns: Math.max(2, Math.floor(width / 190))
                        cellWidth: width / columns
                        cellHeight: 220

                        delegate: LibraryCard {
                            required property int index
                            required property var modelData
                            width: albumsGrid.cellWidth - 10
                            height: 210
                            title: modelData.name
                            subtitle: modelData.artist + " • " + modelData.count + " faixas"
                            coverUrl: modelData.coverUrl
                            accent: page.accent
                            primaryText: page.primaryText
                            secondaryText: page.secondaryText
                            selected: page.controllerNavigation && page.gamepadZone === 1 && page.currentSection === 1 && index === albumsGrid.currentIndex
                            onActivated: musicService.playAlbum(modelData.name)
                        }
                    }

                    // Artistas
                    GridView {
                        id: artistsGrid
                        model: musicService.artists
                        currentIndex: musicService.artists.length > 0 ? 0 : -1
                        clip: true
                        property int columns: Math.max(2, Math.floor(width / 190))
                        cellWidth: width / columns
                        cellHeight: 220

                        delegate: LibraryCard {
                            required property int index
                            required property var modelData
                            width: artistsGrid.cellWidth - 10
                            height: 210
                            title: modelData.name
                            subtitle: modelData.count + " faixas"
                            coverUrl: modelData.coverUrl
                            roundCover: true
                            accent: page.accent
                            primaryText: page.primaryText
                            secondaryText: page.secondaryText
                            selected: page.controllerNavigation && page.gamepadZone === 1 && page.currentSection === 2 && index === artistsGrid.currentIndex
                            onActivated: musicService.playArtist(modelData.name)
                        }
                    }

                    // Favoritos
                    ListView {
                        id: favoritesList
                        model: musicService.favoriteSongs
                        currentIndex: musicService.favoriteSongs.length > 0 ? 0 : -1
                        clip: true
                        spacing: 7

                        delegate: SongRow {
                            required property int index
                            required property var modelData
                            width: favoritesList.width
                            path: modelData.path
                            title: modelData.title
                            subtitle: modelData.artist
                            durationText: modelData.durationText
                            coverUrl: modelData.coverUrl
                            favorite: true
                            active: modelData.path === musicService.currentPath
                            playing: active && musicService.playing
                            accent: page.accent
                            nowPlayingAccent: page.nowPlayingAccent
                            primaryText: page.primaryText
                            secondaryText: page.secondaryText
                            selected: page.controllerNavigation && page.gamepadZone === 1 && page.currentSection === 3 && index === favoritesList.currentIndex
                            onActivated: musicService.playPath(modelData.path)
                            onFavoriteRequested:
                                musicService.toggleFavoritePath(modelData.path)
                            onQueueRequested:
                                musicService.addToQueue(modelData.path)
                            onPlaylistRequested:
                                page.requestPlaylistFor(modelData.path)
                        }
                    }

                    // Recentes
                    ListView {
                        id: recentList
                        model: musicService.recentSongs
                        currentIndex: musicService.recentSongs.length > 0 ? 0 : -1
                        clip: true
                        spacing: 7

                        delegate: SongRow {
                            required property int index
                            required property var modelData
                            width: recentList.width
                            path: modelData.path
                            title: modelData.title
                            subtitle: modelData.artist
                            durationText: modelData.durationText
                            coverUrl: modelData.coverUrl
                            favorite: modelData.favorite
                            active: modelData.path === musicService.currentPath
                            playing: active && musicService.playing
                            accent: page.accent
                            nowPlayingAccent: page.nowPlayingAccent
                            primaryText: page.primaryText
                            secondaryText: page.secondaryText
                            selected: page.controllerNavigation && page.gamepadZone === 1 && page.currentSection === 4 && index === recentList.currentIndex
                            onActivated: musicService.playPath(modelData.path)
                            onFavoriteRequested:
                                musicService.toggleFavoritePath(modelData.path)
                            onQueueRequested:
                                musicService.addToQueue(modelData.path)
                            onPlaylistRequested:
                                page.requestPlaylistFor(modelData.path)
                        }
                    }

                    // Playlists
                    Item {
                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 10

                            RowLayout {
                                Layout.fillWidth: true
                                TouchButton {
                                    text: "Nova playlist"
                                    accent: page.accent
                                    primaryText: page.primaryText
                                    onClicked: {
                                        page.pendingPlaylistPath = ""
                                        newPlaylistDialog.open()
                                    }
                                }
                                Item { Layout.fillWidth: true }
                            }

                            GridView {
                                id: playlistsGrid
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                model: musicService.playlists
                                currentIndex: musicService.playlists.length > 0 ? 0 : -1
                                clip: true
                                property int columns: Math.max(2, Math.floor(width / 190))
                                cellWidth: width / columns
                                cellHeight: 220

                                delegate: LibraryCard {
                                    required property int index
                                    required property var modelData
                                    width: playlistsGrid.cellWidth - 10
                                    height: 210
                                    title: modelData.name
                                    subtitle: modelData.count + " faixas"
                                    coverUrl: modelData.coverUrl
                                    accent: page.accent
                                    primaryText: page.primaryText
                                    secondaryText: page.secondaryText
                                    selected: page.controllerNavigation && page.gamepadZone === 1 && page.currentSection === 5 && index === playlistsGrid.currentIndex
                                    onActivated:
                                        musicService.playPlaylist(modelData.name)
                                }
                            }
                        }
                    }

                    // Fila
                    Item {
                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 10

                            RowLayout {
                                Layout.fillWidth: true

                                Text {
                                    text: "Próximas • " + musicService.queueCount
                                    color: page.primaryText
                                    font.pixelSize: 18
                                    font.weight: Font.DemiBold
                                    Layout.fillWidth: true
                                }

                                TouchButton {
                                    text: "Limpar fila"
                                    enabled: musicService.queueCount > 0
                                    accent: page.accent
                                    primaryText: page.primaryText
                                    onClicked: musicService.clearQueue()
                                }
                            }

                            ListView {
                                id: queueList
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                model: musicService.queueSongs
                                currentIndex: musicService.queueSongs.length > 0 ? 0 : -1
                                clip: true
                                spacing: 7

                                delegate: Rectangle {
                                    required property var modelData
                                    required property int index

                                    width: queueList.width
                                    height: 70
                                    radius: 16
                                    color: page.controllerNavigation && page.gamepadZone === 1 && page.currentSection === 6 && index === queueList.currentIndex ? "#1d2735" : "#151a22"
                                    border.color: page.controllerNavigation && page.gamepadZone === 1 && page.currentSection === 6 && index === queueList.currentIndex ? page.accent : "#27313e"
                                    border.width: page.controllerNavigation && page.gamepadZone === 1 && page.currentSection === 6 && index === queueList.currentIndex ? 3 : 1

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: 10
                                        spacing: 12

                                        Text {
                                            text: (index + 1).toString()
                                            color: page.secondaryText
                                            font.pixelSize: 13
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            Text {
                                                Layout.fillWidth: true
                                                text: modelData.title
                                                color: page.primaryText
                                                font.pixelSize: 16
                                                font.weight: Font.Medium
                                                elide: Text.ElideRight
                                            }
                                            Text {
                                                Layout.fillWidth: true
                                                text: modelData.artist
                                                color: page.secondaryText
                                                font.pixelSize: 13
                                                elide: Text.ElideRight
                                            }
                                        }

                                        HoverButton {
                                            hoverAccent: page.accent
                                            hoverRadius: 15
                                            text: "↑"
                                            enabled: index > 0
                                            onClicked:
                                                musicService.moveQueueItem(index, index - 1)
                                        }

                                        HoverButton {
                                            hoverAccent: page.accent
                                            hoverRadius: 15
                                            text: "↓"
                                            enabled: index < musicService.queueCount - 1
                                            onClicked:
                                                musicService.moveQueueItem(index, index + 1)
                                        }

                                        HoverButton {
                                            hoverAccent: page.accent
                                            hoverRadius: 15
                                            text: "×"
                                            onClicked:
                                                musicService.removeQueueIndex(index)
                                        }
                                    }
                                }

                                Text {
                                    anchors.centerIn: parent
                                    visible: musicService.queueCount === 0
                                    text: "A fila está vazia."
                                    color: page.secondaryText
                                    font.pixelSize: page.compactLayout ? 13 : 15
                                }
                            }
                        }
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillHeight: true
            Layout.preferredWidth: Math.max(page.compactLayout ? 300 : 330, page.width * (page.compactLayout ? 0.30 : 0.32))
            Layout.maximumWidth: page.width * (page.compactLayout ? 0.35 : 0.38)
            spacing: page.compactLayout ? 8 : 16

            AcrylicPanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                panelColor: page.panelAlt
                borderColor: page.line

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: page.compactLayout ? 12 : 22
                    spacing: page.compactLayout ? 7 : 14

                    Item {
                        Layout.fillHeight: !page.compactLayout
                        Layout.preferredHeight: page.compactLayout ? 0 : 1
                    }

                    Rectangle {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: Math.min(page.compactLayout ? 148 : 230, parent.width - 20)
                        Layout.preferredHeight: width
                        radius: 30
                        color: "#11161e"
                        border.color: "#293545"
                        clip: true

                        Image {
                            anchors.fill: parent
                            source: musicService.currentCoverUrl
                            fillMode: Image.PreserveAspectCrop
                            visible: musicService.currentCoverUrl.length > 0
                        }

                        Text {
                            anchors.centerIn: parent
                            visible: musicService.currentCoverUrl.length === 0
                            text: "♫"
                            color: page.accent
                            font.pixelSize: page.compactLayout ? 52 : 80
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            Text {
                                Layout.fillWidth: true
                                text: musicService.currentTitle
                                color: page.primaryText
                                font.pixelSize: page.compactLayout ? 18 : 22
                                font.weight: Font.DemiBold
                                horizontalAlignment: Text.AlignHCenter
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: musicService.currentArtist.length > 0
                                      ? musicService.currentArtist
                                      : "MediaDeck Music"
                                color: page.secondaryText
                                font.pixelSize: page.compactLayout ? 13 : 15
                                horizontalAlignment: Text.AlignHCenter
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                visible: musicService.currentAlbum.length > 0
                                text: musicService.currentAlbum
                                color: page.secondaryText
                                opacity: 0.8
                                font.pixelSize: page.compactLayout ? 11 : 13
                                horizontalAlignment: Text.AlignHCenter
                                elide: Text.ElideRight
                            }
                        }

                        HoverButton {
                            hoverAccent: page.accent
                            hoverRadius: 15
                            implicitWidth: page.compactLayout ? 40 : 46
                            implicitHeight: page.compactLayout ? 40 : 46
                            enabled: musicService.hasCurrent

                            background: Rectangle {
                                radius: 14
                                color: parent.down ? "#2b3442" : "#171d27"
                                border.color: musicService.currentFavorite
                                              ? "#ff7b8a"
                                              : "#2a3342"
                            }

                            contentItem: Text {
                                text: musicService.currentFavorite ? "♥" : "♡"
                                color: musicService.currentFavorite
                                       ? "#ff7b8a"
                                       : page.primaryText
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                font.pixelSize: 23
                            }

                            onClicked: musicService.toggleCurrentFavorite()
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Slider {
                            id: progressSlider
                            Layout.fillWidth: true
                            from: 0
                            to: Math.max(1, musicService.duration)
                            value: pressed ? value : musicService.position
                            enabled: musicService.hasCurrent
                            onMoved: musicService.seek(value)
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: musicService.positionText
                                color: page.secondaryText
                                font.pixelSize: 12
                                Layout.fillWidth: true
                            }
                            Text {
                                text: musicService.durationText
                                color: page.secondaryText
                                font.pixelSize: 12
                            }
                        }
                    }

                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: page.compactLayout ? 6 : 12

                        MediaButton {
                            text: "⤨"
                            gamepadSelected: page.controllerNavigation && page.gamepadZone === 2 && page.playerControlIndex === 0
                            enabled: musicService.songCount > 1
                            accent: page.accent
                            primaryText: musicService.shuffle
                                         ? page.accent
                                         : page.primaryText

                            ToolTip.visible: hovered
                            ToolTip.text: musicService.shuffle
                                          ? "Desativar modo aleatório"
                                          : "Ativar modo aleatório"

                            onClicked: musicService.toggleShuffle()
                        }

                        MediaButton {
                            text: "|◀"
                            gamepadSelected: page.controllerNavigation && page.gamepadZone === 2 && page.playerControlIndex === 1
                            enabled: musicService.songCount > 0
                            accent: page.accent
                            primaryText: page.primaryText
                            onClicked: musicService.previous()
                        }

                        MediaButton {
                            text: musicService.playing ? "Ⅱ" : "▶"
                            gamepadSelected: page.controllerNavigation && page.gamepadZone === 2 && page.playerControlIndex === 2
                            enabled: musicService.songCount > 0
                            emphasized: true
                            accent: page.accent
                            primaryText: page.primaryText
                            onClicked: musicService.playPause()
                        }

                        MediaButton {
                            text: "▶|"
                            gamepadSelected: page.controllerNavigation && page.gamepadZone === 2 && page.playerControlIndex === 3
                            enabled: musicService.songCount > 0
                            accent: page.accent
                            primaryText: page.primaryText
                            onClicked: musicService.next()
                        }

                        MediaButton {
                            text: "↻"
                            gamepadSelected: page.controllerNavigation && page.gamepadZone === 2 && page.playerControlIndex === 4
                            enabled: musicService.hasCurrent
                            accent: page.accent
                            primaryText: musicService.repeat
                                         ? page.accent
                                         : page.primaryText
                            onClicked: musicService.toggleRepeat()
                        }
                    }

                    AudioSpectrum {
                        visible: visualizerService.enabled

                        Layout.fillWidth: true
                        Layout.preferredHeight:
                            visualizerService.enabled
                            ? (page.compactLayout ? 60 : 105)
                            : 0

                        accent: page.accent
                        secondaryText: page.secondaryText

                        levels: visualizerService.levels
                        peaks: visualizerService.peaks
                        active: visualizerService.active
                        statusText: visualizerService.status
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Text {
                            visible: musicService.queueCount > 0
                            text: musicService.queueCount + " na fila"
                            color: page.secondaryText
                            font.pixelSize: 13
                            Layout.fillWidth: true
                        }

                        Item {
                            visible: musicService.queueCount === 0
                            Layout.fillWidth: true
                        }

                        Text {
                            visible: visualizerService.enabled
                            text: page.compactLayout ? "VISUALIZER" : "VISUALIZER • 28 BANDAS • 30 FPS"
                            color: page.secondaryText
                            opacity: 0.72
                            font.pixelSize: 10
                        }

                        HoverButton {
                            implicitWidth: 138
                            implicitHeight: 38
                            gamepadSelected: page.controllerNavigation && page.gamepadZone === 2 && page.playerControlIndex === 5

                            hoverAccent: page.accent
                            hoverRadius: 13

                            enabled: musicService.hasCurrent

                            background: Rectangle {
                                radius: 13
                                color: parent.down ? "#29405f" : "#171d27"
                                border.color: "#354153"
                                border.width: 1
                            }

                            contentItem: Text {
                                text: "⛶  Visualização"
                                color: page.primaryText
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }

                            ToolTip.visible: hovered
                            ToolTip.text:
                                visualizerService.enabled
                                ? "Abrir visualizações em tela cheia"
                                : "Ative o visualizador nas Configurações"

                            onClicked: {
                                if (!visualizerService.enabled) {
                                    page.showToast(
                                        "Ative o visualizador nas Configurações."
                                    )
                                    return
                                }

                                page.visualizerRequested()
                            }
                        }
                    }

                    Item {
                        Layout.fillHeight: !page.compactLayout
                        Layout.preferredHeight: page.compactLayout ? 0 : 1
                    }
                }
            }
        }
    }
}
