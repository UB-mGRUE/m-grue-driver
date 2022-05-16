import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Dialogs 1.0
import QtQuick.Window 2.1

Window {
    visible: true
    width: 600
    height: 500
    id: window
    title: "mGRUE"
    color: "lightslategrey"
    property string fileName: "Please select a file"
    property string statusMessage: ""
    property QtObject backend

    Connections {
        target: backend
        function onStatus(msg) {
            statusMessage = msg;
        }
    }

    Rectangle {
        id: title
        anchors.fill: parent
        color: "transparent"
        Text {
            text: "mGRUE Host Device Driver"
            font.family: "Yu Gothic UI Semibold"
            font.pixelSize: 40
            color: "oldlace"
            anchors {
                top: parent.top
                horizontalCenter: parent.horizontalCenter
                topMargin: 12
            }

        }

        Rectangle {
            id: messageSection
            anchors.fill: parent
            color: "transparent"
            Text {
                id: location
                anchors {
                    bottom: messages.top
                    bottomMargin: 12
                    left: messages.left

                }
                text: "Destination Folder: " + window.fileName.substring(7)  // display current destination
                font.pixelSize: 20
                font.family: "Yu Gothic UI Semilight"
                color: "oldlace"
            }
            Text {
                id: messages
                anchors {
                    bottom: parent.bottom
                    bottomMargin: 12
                    left: parent.left
                    leftMargin: 12
                }
                text: "Status: " + statusMessage
                font.pixelSize: 24
                font.family: "Yu Gothic UI Semilight"
                color: "oldlace"
            }
        }


        FileDialog {
            id: fileDialog
            visible: false
            title: "Please choose desired folder location"
            folder: shortcuts.home
            selectFolder: true
            onAccepted: {
                backend.getFileLocation(fileDialog.fileUrls)
                //location.text = "Destination Folder: "+ fileDialog.fileUrls[0]
                window.fileName = fileDialog.fileUrls[0]
                console.log(window.fileName.substring(7))
                close()
            }
            onRejected: {
                console.log("File selection canceled by user")
                close()
            }
        }
        Rectangle {
            id: fileLocation
            anchors.fill: parent
            color: "transparent"

            Button {
            id: selectButton
            text: "Select Folder"
            font.family: "Yu Gothic UI Semilight"
            
            anchors.centerIn: parent
            contentItem: Text {
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                text: selectButton.text
                color: "oldlace"
            }
            background: Rectangle {
                implicitWidth: 300
                implicitHeight: 150
                color: "#36454F"
                radius: 8
            }
            onClicked: fileDialog.visible = true    //Opens file dialog on click
        }

            
        }
    }
}
/*##^##
Designer {
    D{i:0;formeditorZoom:0.9}D{i:1}D{i:3}D{i:5}D{i:4}D{i:6}D{i:8}D{i:11}D{i:7}D{i:2}
}
##^##*/
