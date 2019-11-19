from FreeCAD import Gui
from FreeCAD import Base
import FreeCAD, FreeCADGui, Part, os, math

import FreeCAD as App

import FreeCADGui
import FreeCAD
import Part
import sys, os
from PySide import QtGui, QtCore

# create new Tab in ComboView
from PySide import QtGui, QtCore

def getComboView():
    mw = Gui.getMainWindow()
    dw = mw.findChildren(QtGui.QDockWidget)
    for i in dw:
        if str(i.objectName()) == "Combo View":
            return i.findChild(QtGui.QTabWidget)
        elif str(i.objectName()) == "Python Console":
            return i.findChild(QtGui.QTabWidget)
    raise Exception("No tab widget found")


class CreateRevoluteJointForm(QtGui.QDialog):
    """"""

    def __init__(self, parent_ok_callback):
        super(CreateRevoluteJointForm, self).__init__()
        self.parent_ok_callback = parent_ok_callback
        self.initUI()

    def initUI(self):
        option1Button = QtGui.QPushButton("OK")
        option1Button.clicked.connect(self.onOK)
        option2Button = QtGui.QPushButton("Cancel")
        option2Button.clicked.connect(self.onCancel)

        labelPosition = QtGui.QLabel("Position")
        labelRotation = QtGui.QLabel("Rotation")

        hbox_pcj = QtGui.QVBoxLayout()
        self.parent_label = QtGui.QLabel("Parent")
        self.child_label = QtGui.QLabel("Child")
        self.joint_label = QtGui.QLabel("Joint")

        self.button_set_to_selection = QtGui.QPushButton("Set to current selection")
        self.button_set_to_selection.clicked.connect(self.on_set_to_selection)

        hbox_pcj.addWidget(self.parent_label)
        hbox_pcj.addWidget(self.child_label)
        hbox_pcj.addWidget(self.joint_label)
        hbox_pcj.addWidget(self.button_set_to_selection)

        onlyDouble = QtGui.QDoubleValidator()
        self.posX = QtGui.QLineEdit("0")
        self.posX.setValidator(onlyDouble)
        self.posY = QtGui.QLineEdit("0")
        self.posY.setValidator(onlyDouble)
        self.posZ = QtGui.QLineEdit("0")
        self.posZ.setValidator(onlyDouble)
        self.rotX = QtGui.QLineEdit("1")
        self.rotX.setValidator(onlyDouble)
        self.rotY = QtGui.QLineEdit("0")
        self.rotY.setValidator(onlyDouble)
        self.rotZ = QtGui.QLineEdit("0")
        self.rotZ.setValidator(onlyDouble)

        # buttonBox = QtGui.QDialogButtonBox()
        buttonBox = QtGui.QDialogButtonBox(QtCore.Qt.Horizontal)
        buttonBox.addButton(option1Button, QtGui.QDialogButtonBox.ActionRole)
        buttonBox.addButton(option2Button, QtGui.QDialogButtonBox.ActionRole)
        #
        posLabelLayout = QtGui.QHBoxLayout()
        posLabelLayout.addWidget(labelPosition)

        posValueLayout = QtGui.QHBoxLayout()
        posValueLayout.addWidget(QtGui.QLabel("X"))
        posValueLayout.addWidget(self.posX)
        posValueLayout.addWidget(QtGui.QLabel("Y"))
        posValueLayout.addWidget(self.posY)
        posValueLayout.addWidget(QtGui.QLabel("Z"))
        posValueLayout.addWidget(self.posZ)

        rotLabelLayout = QtGui.QHBoxLayout()
        rotLabelLayout.addWidget(labelRotation)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("X"))
        hbox.addWidget(self.rotX)
        hbox.addWidget(QtGui.QLabel("Y"))
        hbox.addWidget(self.rotY)
        hbox.addWidget(QtGui.QLabel("Z"))
        hbox.addWidget(self.rotZ)

        mainLayout = QtGui.QVBoxLayout()
        mainLayout.addLayout(hbox_pcj)
        mainLayout.addLayout(posLabelLayout)
        mainLayout.addLayout(posValueLayout)
        mainLayout.addLayout(rotLabelLayout)
        mainLayout.addLayout(hbox)
        mainLayout.addWidget(buttonBox)
        self.setLayout(mainLayout)
        # define window   xLoc,yLoc,xDim,yDim
        self.retStatus = 0

    def onOK(self):
        self.retStatus = 1
        self.parent_ok_callback()
        self.close()

    def onCancel(self):
        self.retStatus = 2
        self.close()

    def on_set_to_selection(self):
        selection = Gui.Selection.getSelection()
        sel_ex = Gui.Selection.getSelectionEx()
        if len(selection) == 1 and len(sel_ex) == 1 and sel_ex[0].HasSubObjects:
            sel_ex = sel_ex[0]
            if len(sel_ex.SubObjects) != 1:
                FreeCAD.Console.PrintMessage("Too many faces selected :/")
            else:
                face = sel_ex.SubObjects[0]
                # if type(face) != Part.Face:
                #     FreeCAD.Console.PrintMessage("Need to select a face!")
                center = face.CenterOfMass
                normal = face.normalAt(0, 0)
                self.posX.setText(str(round(center[0], 6)))
                self.posY.setText(str(round(center[1], 6)))
                self.posZ.setText(str(round(center[2], 6)))
                self.rotX.setText(str(normal[0]))
                self.rotY.setText(str(normal[1]))
                self.rotZ.setText(str(normal[2]))

        for el in selection:
            print (el.Label)
        self.parent_label.setText("Parent: " + selection[0].Label)
        self.child_label.setText("Child: " + selection[1].Label)
        if len(selection) == 3:
            self.joint_label.setText("Joint: " + selection[2].Label)
        else:
            self.joint_label.setText("Joint: <empty>")


class Joint:
    def __init__(self, obj, parent, child):
        '''"App two point properties"'''
        obj.addProperty("App::PropertyString", "Parent", "Joint").Parent = parent.Name
        obj.addProperty("App::PropertyString", "Child", "Joint").Child = child.Name
        obj.addProperty(
            "App::PropertyAngle", "Angle1", "Joint", "Angle1 of joint"
        ).Angle1 = 90
        obj.addProperty(
            "App::PropertyVector", "axis", "rotation", "End point"
        ).axis = FreeCAD.Vector(1, 0, 0)
        obj.Proxy = self

    def execute(self, fp):
        """"Print a short message when doing a recomputation, this method is mandatory" """
        fp.Shape = Part.makeSphere(1)


class ViewProviderJoint:
    def __init__(self, obj):
        """ Set this object to the proxy object of the actual view provider """
        obj.ShapeColor = (1.0, 0.0, 0.0)
        obj.Proxy = self

    def getDefaultDisplayMode(self):
        """ Return the name of the default display mode. It must be defined in getDisplayModes. """
        return "Flat Lines"


class CreateJoint:
    """RC_CreateJoint"""

    def GetResources(self):
        print FreeCAD.getUserAppDataDir() + "Mod" + "/RobotCreator/icons/createJoint.png"
        return {
            "Pixmap": os.path.join(
                str(FreeCAD.getUserAppDataDir()),
                "Mod",
                "RobotCreator/icons/createJoint.png",
            ),  # the name of a svg file available in the resources
            "Accel": "Shift+j",  # a default shortcut (optional)
            "MenuText": "Create a joint",
            "ToolTip": "Create a joint",
        }

    def Activated(self):
        print "creating a joint"

        self.selection = Gui.Selection.getSelection()
        if len(self.selection) >= 2:
            self.form = CreateRevoluteJointForm(self.ok_clicked)
            self.tab = getComboView()
            self.tab.addTab(self.form, "Create Joint")
            self.tab.setCurrentWidget(self.form)
        else:
            print "Only support selection of two elements on two different objects"

    def ok_clicked(self):
        if self.form.retStatus == 1:
            j = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Joint")
            Joint(j, self.selection[0], self.selection[1])
            # FreeCAD.Console.PrintMessage("Setting Joint to XYZ: %s %s %s\n" % (self.form.posX.text(), self.form.posY.text(), self.form.posZ.text()))
            # FreeCAD.Console.PrintMessage("Setting Joint to RPY: %s %s %s\n" % (self.form.rotX.text(), self.form.rotY.text(), self.form.rotZ.text()))
            j.Placement.Base = FreeCAD.Vector(
                float(self.form.posX.text()),
                float(self.form.posY.text()),
                float(self.form.posZ.text()),
            )
            j.axis = FreeCAD.Vector(
                float(self.form.rotX.text()),
                float(self.form.rotY.text()),
                float(self.form.rotZ.text()),
            )
            ViewProviderJoint(j.ViewObject)
            App.ActiveDocument.recompute()

        elif self.form.retStatus == 2:
            print "abort"

        self.tab.removeTab(self.tab.indexOf(self.form))

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return True


FreeCADGui.addCommand("RC_CreateJoint", CreateJoint())
