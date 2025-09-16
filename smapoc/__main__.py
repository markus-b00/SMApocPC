def main(splash=True):
    import sys
    import os
    from PyQt5.QtWidgets import QApplication, QSplashScreen
    from PyQt5.QtCore import Qt, QEventLoop
    from PyQt5.QtGui import QPixmap, QColor
    from __version__ import version, info
    import smapoc_rc

    app = QApplication(sys.argv)


    if splash:
        splash_pix = QPixmap(":/splash/splash.png")  # Replace 'splash.png' with the path to your splash screen image
        splash = QSplashScreen(splash_pix, Qt.WindowType.SplashScreen)
        text = f'Version: {version()}'
        splash.showMessage("     "+text, color=QColor('white'))
        splash.show()
        # qtc.QTimer.singleShot(3000, splash.close)
        # qtc.QTimer.singleShot(3000, window.show)
        # make sure Qt really displays the splash screen
        app.processEvents(QEventLoop.AllEvents, 1000)

    from PyQt5 import QtGui as qtg
    from .gui import SMApocMain

    # Set Application Icon
    icon_path = os.path.join(":/icon/icon.png")
    app.setWindowIcon(qtg.QIcon(icon_path))

    window = SMApocMain()
    window.show()
    if splash:
        splash.finish(window)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
