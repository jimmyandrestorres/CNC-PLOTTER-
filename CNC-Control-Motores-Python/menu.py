# Modules PyQt
from fileinput import filename
from PyQt5 import QtWidgets, uic
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.Qsci import *
from PIL import Image, ImageQt
from PyQt5.QtWidgets import (QApplication, QLabel, QGridLayout, QWidget)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QTimer
from PIL import Image, ImageFilter, ImageQt
from PyQt5 import QtSvg
from PyQt5.QtWidgets import QMainWindow, QApplication, QSizePolicy
from svg_to_gcode.svg_parser import parse_file
from svg_to_gcode.compiler import Compiler, interfaces
from svg_to_gcode.formulas import linear_map
import serial
import serial.tools.list_ports as list_ports
import time
import requests
import os
#import GUIFuncional.recursos
#import cairosSVG
import pygame.camera
import sys
import view3d
import pathlib

class SendFile(QtCore.QObject):
    update = QtCore.pyqtSignal(str)

    def __init__(self, serial, ui):
        super().__init__()
        self.serial = serial 

        #Visualiza texto de comandos
        self.__editor = QsciScintilla()
        ui.codeLayout.addWidget(self.__editor)
        
        font = QFont()
        font.setFamily('Courier')
        font.setFixedPitch(True)
        font.setPointSize(12)
        
        lexer = QsciLexerPython()
        lexer.setDefaultFont(font)
        self.__editor.setLexer(lexer)
        self.__editor.setUtf8(True)  # Set encoding to UTF-8
        self.__editor.setFont(font) 
        self.__editor.setMarginsFont(font) 
        
        fontmetrics = QFontMetrics(font)
        self.__editor.setMarginsFont(font)
        self.__editor.setMarginWidth(0, fontmetrics.width("0000") + 6)
        self.__editor.setMarginLineNumbers(0, True)
        self.__editor.setMarginsBackgroundColor(QColor("#cccccc"))
    
    def set__editor(self, comando):
        self.__editor.append(comando)

    def setFile(self, f):
        self.f = f

    def send_message(self, message):
        data = message + '\n'
        self.serial.write(data.encode('utf-8'))
        self.serial.readline().decode('utf-8')

    def run(self):
        print('Thread')
        if self.serial.is_open:
            try:
                time.sleep(2)
                self.send_message("\n\n")
                for line in self.f:
                    comando = line.strip()
                    if not comando.startswith('(') and not comando.startswith('%'):
                        self.send_message(comando)
                        self.set__editor(comando + '\n')
                self.f.close()
            except:
                print('Stop')


# Class Monitor - Inherits from QMainWindow
class Menu(QtWidgets.QMainWindow):

    # Constructor
    def __init__(self):
        super(Menu, self).__init__()
        # Load user interface
        self.ui = uic.loadUi("INTERFAZ_GRUPO.ui", self)
        
        #Visualizar Camara
        pygame.camera.init()
        cameras = pygame.camera.list_cameras()
        self.cam = pygame.camera.Camera(cameras[0], (640, 480)) 

        self.label = self.ui.label_camera
        # self.ui.gridLayout_Camera.addWidget(self.label)
        # self.setLayout(self.ui.gridLayout_Camera)

        self.timer = QTimer()
        #self.timer.timeout.connect(self.showCamera)
        self.cam.start()
        self.timer.start()
        

        # Serial port object 
        self.serial = serial.Serial()
        self.fileName = ''
        self.comandos = ''
        #Visualiza Gcode en 3D
        self.view_3D = view3d.View3D()
        self.ui.viewLayout.addWidget(self.view_3D)


        for baud in self.serial.BAUDRATES:
            self.ui.baudOptions.addItem(str(baud))

        self.baud = 115200
        self.ui.baudOptions.setCurrentIndex(self.serial.BAUDRATES.index(self.baud))

        ports = list_ports.comports()
        
        if ports:
            for port in ports:
                self.ui.portOptions.addItem(port.device)

            self.serial.baudrate = self.baud
            self.serial.port = self.ui.portOptions.currentText()
            self.ui.connectButton.setEnabled(True)
        
        # Create a Timer for reading data
        self.thread = QtCore.QThread()

        self.sendFile = SendFile(self.serial, self.ui)

        self.sendFile.moveToThread(self.thread)
        self.thread.started.connect(self.sendFile.run)

        self.ui.connectButton.clicked.connect(self.connect)
        self.ui.X_izquierda.clicked.connect(self.X_L)
        self.ui.inputEdit.returnPressed.connect(self.send)
        self.ui.baudOptions.currentIndexChanged.connect(self.changeBaud)
        self.ui.X_derecha.clicked.connect(self.X_R)
        self.ui.Y_arriba.clicked.connect(self.Y_UP)
        self.ui.Y_abajo.clicked.connect(self.Y_DOWN)
        self.ui.Diag_Der_UP.clicked.connect(self.R_DiagUP)
        self.ui.Diag_Izq_UP.clicked.connect(self.L_DiagUP)
        self.ui.Diag_Der_DOWN.clicked.connect(self.R_DiagDOWN)
        self.ui.Diag_Izq_DOWN.clicked.connect(self.L_DiagDOWN)
        self.ui.openButton.clicked.connect(self.abrir_archivo)
        self.ui.iniciarButton.clicked.connect(self.ejecutar)
        self.ui.reset_ceroButton.clicked.connect(self.resetZero)
        self.ui.ceroButton.clicked.connect(self.returnZero)
        self.pararButton.clicked.connect(self.stop)
        self.servo_arriba.clicked.connect(self.Z_UP)
        self.servo_abajo.clicked.connect(self.Z_DOWN)
        self.button_Camera_On_Off.clicked.connect(self.showCamera)
        self.button_TomarFoto.clicked.connect(self.tomarFoto)
        self.button_Enviar_Imagen.clicked.connect(self.enviarFoto)
               
        self.timer = QtCore.QTimer()
        if self.serial.is_open:
            self.timer.start(10)
            self.timer.timeout.connect(self.read)
	
    def showCamera(self):
        self.show()
        self.ui.button_Camera_On_Off.setText('Off')
        image = self.cam.get_image()
        raw_str = pygame.image.tostring(image, 'RGB', False)
        pil_image = Image.frombytes('RGB', image.get_size(), raw_str)
        
        self.im = ImageQt.ImageQt(pil_image)
        pixmap = QPixmap.fromImage(self.im)
        self.label.setPixmap(pixmap)
        #self.showCamera

    def tomarFoto(self):
        image = self.cam.get_image()
        self.cam.stop()
        raw_str = pygame.image.tostring(image, 'RGB', False)
        pil_image = Image.frombytes('RGB', image.get_size(), raw_str)
        pil_image = pil_image.convert('L')

        threshold = 115
        img_new = pil_image.point(lambda x:255 if x < threshold else 0)
        img_new = img_new.filter(ImageFilter.CONTOUR)
        img_new.save('photo.bmp')
        
        self.im = ImageQt.ImageQt(img_new)
        pixmap = QPixmap.fromImage(self.im)
        self.label.setPixmap(pixmap)

        input_file = "photo.bmp"
        output_file = "photo.svg"

        os.system("potrace {} --svg -o {}".format(input_file, output_file))
    
    def enviarFoto(self):
        self.fileName = "photo.svg"
        self.visual3D()

    def connect(self):
        if not self.serial.is_open:
            self.serial.open()       
            #self.thread.start()
            self.ui.sendButton.setEnabled(True)
            self.ui.iniciarButton.setEnabled(True)
            self.ui.pararButton.setEnabled(True)
            self.ui.reset_ceroButton.setEnabled(True)
            self.ui.servo_arriba.setEnabled(True)
            self.ui.servo_abajo.setEnabled(True)
            self.ui.homeButton.setEnabled(True)
            self.ui.Diag_Izq_UP.setEnabled(True)
            self.ui.Diag_Der_UP.setEnabled(True)
            self.ui.Diag_Izq_DOWN.setEnabled(True)
            self.ui.Diag_Der_DOWN.setEnabled(True)
            self.ui.Y_arriba.setEnabled(True)
            self.ui.Y_abajo.setEnabled(True)
            self.ui.X_izquierda.setEnabled(True)
            self.ui.X_derecha.setEnabled(True)
            self.ui.ceroButton.setEnabled(True)
            self.ui.connectButton.setText('Desconectar')
            self.ui.inputEdit.setEnabled(True)
        else:
            self.thread.quit()
            self.serial.close()
            self.ui.sendButton.setEnabled(False)
            self.ui.iniciarButton.setEnabled(False)
            self.ui.pararButton.setEnabled(False)
            self.ui.reset_ceroButton.setEnabled(False)
            self.ui.servo_arriba.setEnabled(False)
            self.ui.servo_abajo.setEnabled(False)
            self.ui.homeButton.setEnabled(False)
            self.ui.Diag_Izq_UP.setEnabled(False)
            self.ui.Diag_Der_UP.setEnabled(False)   
            self.ui.Diag_Izq_DOWN.setEnabled(False)
            self.ui.Diag_Der_DOWN.setEnabled(False)
            self.ui.Y_arriba.setEnabled(False)
            self.ui.Y_abajo.setEnabled(False)
            self.ui.X_izquierda.setEnabled(False)
            self.ui.X_derecha.setEnabled(False)
            self.ui.ceroButton.setEnabled(False)
            self.ui.connectButton.setText('Conectar')
            self.ui.inputEdit.setEnabled(False)

    def refresh(self):  
        # Get available ports
        ports = list_ports.comports()
        
        self.ui.portOptions.clear()
        
        if ports:
            for port in ports:
                self.ui.portOptions.addItem(port.device)

            self.serial.baudrate = self.baud
            self.serial.port = self.ui.portOptions.currentText()
            self.ui.connectButton.setEnabled(True)

    def changeBaud(self, index):
        self.baud = self.ui.baudOptions.itemText(index)
        if self.serial.is_open:
            self.serial.baudrate = self.baud
            self.serial.close()
            self.serial.open()


    def abrir_archivo(self):
        self.fileName = QFileDialog.getOpenFileName(self, "Open file", "/home/alejandro", 
                                                "*.gcode *.ngc *.svg")[0]
        
        self.sendFile.set__editor(self.fileName + '\n')
        print("Ruta v3: "+self.fileName)
        self.visual3D()

    def visual3D(self):
        extension = pathlib.Path(self.fileName)
        if extension.suffix == ".svg":

            gcode_compiler = Compiler(interfaces.Gcode, movement_speed=1000, cutting_speed=300, pass_depth=1)
            curves = parse_file(self.fileName)

            gcode_compiler.append_curves(curves) 
            gcode_compiler.compile_to_file("imagen.gcode")
            self.sendFile.set__editor(str(gcode_compiler) + '\n')
            
            fichero = open("imagen.gcode", 'r')
            f = open('grafico.gcode', 'w')
            for line in fichero:
                comando = line.strip().replace(';','')
                if comando.find('M3 S255') != -1:
                    comando = comando.replace('M3 S255','M5 S255')
                elif comando.find('M5') != -1:
                    comando = comando.replace('M5','M3')
                    
                f.write(comando + '\n')
                
            fichero.close()
            f.close()

            self.fileName = 'grafico.gcode'
            gcode = open(self.fileName).read()
            self.view_3D.compute_data(gcode)
            self.view_3D.draw()
        
        else: 
            gcode = open(self.fileName).read()
            self.view_3D.compute_data(gcode)
            self.view_3D.draw()

    def ejecutar(self):
        f = open(self.fileName, 'r')
        self.sendFile.setFile(f)
        self.thread.start()
                

    def resetZero(self):
        self.send_message('G10 P0 L20 X0 Y0 Z0')

    def returnZero(self):
        self.send_message('G21G90 G0Z5')
        self.send_message('G90 G0 X0 Y0')
        self.send_message('G90 G0 Z0')

    def stop(self):
        self.thread.quit()
        self.send_message('GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0')
        #self.serial.close()

    def Z_UP(self):
        self.send_message('M3 S255')
        self.send_message('G90G21')

    def Z_DOWN(self):
        self.send_message('M5 S255')
        self.send_message('G90G21')

    def Y_UP(self):
        self.send_message('G21G91G1Y1F10')
        self.send_message('G90G21')

    def Y_DOWN(self):
        self.send_message('G21G91G1Y-1F10')
        self.send_message('G90G21')

    def X_L(self):
        self.send_message('G21G91G1X-1F10')
        self.send_message('G90G21')

    def X_R(self):
        self.send_message('G21G91G1X1F10')
        self.send_message('G90G21')

    def R_DiagDOWN(self):
        self.send_message('G21G91X1Y-1F10')
        self.send_message('G90G21')

    def R_DiagUP(self):
        self.send_message('G21G91X1Y1F10')
        self.send_message('G90G21')

    def L_DiagUP(self):
        self.send_message('G21G91X-1Y1F10')
        self.send_message('G90G21')

    def L_DiagDOWN(self):
        self.send_message('G21G91X-1Y-1F10')
        self.send_message('G90G21')

    def send_message(self, message):
        self.sendFile.set__editor(message + '\n')
        data = message + '\n'
        self.serial.write(data.encode('utf-8'))
        self.serial.readline().decode('utf-8')



    def send(self):
        if self.serial.is_open:
            data = self.ui.inputEdit.text() + '\n'
            self.serial.write(data.encode('iso-8859-1'))
            self.sendFile.set__editor(data)
            self.ui.inputEdit.setText('')


    def __del__(self):
        if self.serial.is_open:
            self.serial.close()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    menu = Menu()
    menu.show()
    app.exec_()