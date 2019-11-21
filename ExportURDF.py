from FreeCAD import Gui
from FreeCAD import Base
import FreeCAD, FreeCADGui, Part
from PySide import QtGui
import Mesh, BuildRegularGeoms
import os, sys, math

sys.path.append('/home/wolfv/.FreeCAD/Mod/')
from bs4 import BeautifulSoup

def float_to_str(f):
    return "{:.20f}".format(f)


def deg2rad(a):
    return a * 0.01745329252


def str2obj(a):
    return FreeCAD.ActiveDocument.getObject(a)


def bodyFromPad(a):
    objs = FreeCAD.ActiveDocument.Objects
    for obj in objs:
        if obj.TypeId == "PartDesign::Body":
            if obj.hasObject(a):
                return obj


def bodyLabelFromObjStr(a):
    b = FreeCAD.ActiveDocument.getObject(a)
    if b is not None:
        return b.Label
    else:
        return "##NONE##"

joint_mapping = {
    'RevoluteJoint': 'revolute',
    'PrismaticJoint': 'prismatic',
    'FixedJoint': 'fixed',
    'ContinuousJoint': 'continuous'
}

def get_parent_frame(obj):
    parent = obj.Parent

    # b = FreeCAD.ActiveDocument.getObject()

    objs = FreeCAD.ActiveDocument.Objects
    for o in objs:
        if "Joint" in o.Name:
            if o.Child == parent:
                return o
    return None

def get_parent_joint(obj):
    link_name = obj.Name
    # b = FreeCAD.ActiveDocument.getObject()

    objs = FreeCAD.ActiveDocument.Objects
    for o in objs:
        if "Joint" in o.Name:
            if o.Child == link_name:
                return o
    return None

class URDFExportStatic:
    """RC_URDFExport"""

    def GetResources(self):
        return {
            "Pixmap": str(
                FreeCAD.getUserAppDataDir()
                + "Mod"
                + "/RobotCreator/icons/SDFexportStatic.png"
            ),  # the name of a svg file available in the resources
            "Accel": "Shift+u",  # a default shortcut (optional)
            "MenuText": "Export URDF",
            "ToolTip": "Export URDF",
        }

    def Activated(self):

        selected_directory = QtGui.QFileDialog.getExistingDirectory()

        soup = BeautifulSoup(features="xml")
        robot = soup.new_tag('robot')
        robot.attrs['name'] = "testing"
        soup.append(robot)

        # you might want to change this to where you want your exported mesh/sdf to be located.
        self.robot_name = "testing"
        self.output_folder = os.path.expanduser(selected_directory)

        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        self.srdf_file_path = os.path.join(self.output_folder, 'test.urdf')
        self.mesh_path = os.path.join(self.output_folder, 'meshes/')

        if not os.path.exists(self.mesh_path):
            os.makedirs(self.mesh_path)

        self.srdf_file = open(self.srdf_file_path, "w")

        objs = FreeCAD.ActiveDocument.Objects
        for obj in objs:
            if "Joint" in obj.Name:
                pos = obj.Shape.Placement
                computed_pos = pos.Base * 0.001

                parent_frame = get_parent_frame(obj)
                if parent_frame:
                    computed_pos -= (parent_frame.Shape.Placement.Base * 0.001)

                joint_type = None
                for jt_loop in joint_mapping:
                    if obj.Name.startswith(jt_loop):
                        joint_type = joint_mapping[jt_loop]
                        break

                if not joint_type:
                    raise RuntimeError("No Joint Type found!")

                joint_elem = soup.new_tag('joint', type=joint_type)

                if hasattr(obj, 'Label') and obj.Label != '':
                    joint_elem.attrs['name'] = obj.Label
                else:
                    joint_elem.attrs['name'] = bodyLabelFromObjStr(obj.Parent) + bodyLabelFromObjStr(obj.Child)

                joint_origin = soup.new_tag('origin',
                    xyz=" ".join([str(x) for x in computed_pos]),
                    rpy=" ".join([str(x) for x in pos.Rotation.toEuler()[::-1]])
                )
                joint_elem.append(joint_origin)

                parent_tag = soup.new_tag('parent', link=bodyLabelFromObjStr(obj.Parent))
                joint_elem.append(parent_tag)

                child_tag = soup.new_tag('child', link=bodyLabelFromObjStr(obj.Child))
                joint_elem.append(child_tag)

                if hasattr(obj, 'Axis'):
                    axis = soup.new_tag('axis', xyz=" ".join((str(x) for x in obj.Axis)))
                    joint_elem.append(axis)

                if joint_type in ('revolute', 'prismatic'):
                    limit_tag = soup.new_tag('limit',
                        velocity=obj.VelocityLimit,
                        effort=obj.EffortLimit
                    )

                    if obj.UpperLimit:
                        limit_tag['upper'] = obj.UpperLimit
                    if obj.LowerLimit:
                        limit_tag['lower'] = obj.LowerLimit
                    joint_elem.append(limit_tag)

                robot.append(joint_elem)

            if obj.TypeId == "PartDesign::Body" or obj.TypeId == "Part::Box" or obj.TypeId == "Part::Feature":
                name = obj.Label
                mass = obj.Shape.Mass
                inertia = obj.Shape.MatrixOfInertia
                pos = obj.Shape.Placement
                com = obj.Shape.CenterOfMass
                com *= 0.001
                mass *= 0.001
                A11 = inertia.A11 * 0.000000001
                A12 = inertia.A12 * 0.000000001
                A13 = inertia.A13 * 0.000000001
                A22 = inertia.A22 * 0.000000001
                A23 = inertia.A23 * 0.000000001
                A33 = inertia.A33 * 0.000000001

                pos.Base *= 0.001

                # export shape as mesh (stl)
                mesh_file_name = os.path.join(self.mesh_path, name + ".stl")
                # disable export of mesh for now
                if not os.path.exists(mesh_file_name):
                    Mesh.export([obj], mesh_file_name)
 
                    print("About to scale {}".format(mesh_file_name))
                    # import stl and translate/scale
                    # scaling, millimeter -> meter
                    mesh = Mesh.read(mesh_file_name)

                    pj = get_parent_joint(obj)
                    if pj:
                        mesh.translate(*-pj.Shape.Placement.Base)

                    mat = FreeCAD.Matrix()
                    mat.scale(0.001, 0.001, 0.001)


                    # apply scaling
                    mesh.transform(mat)

                    # # move origo to center of mass
                    # pos.move(com * -1)
                    # mesh.Placement.Base -= mesh.CenterOfMass
                    # mesh.Placement.Base = (0, 0,)

                    # save scaled and transformed mesh as stl
                    mesh.write(mesh_file_name)

                link = soup.new_tag('link')
                link.attrs['name'] = name

                # link_pose = soup.new_tag('pose')
                # link_pose.string = "0 0 0 {} {} {} {}".format(*[deg2rad(x) for x in pos.Rotation.Q])
                # link.append(link_pose)

                visual = soup.new_tag('visual')
                # visual_origin = soup.new_tag('origin', xyz=" ".join(pos.Base), rpy=" ".join(pos.Rotation.toEuler()[::-1]))
                visual_origin = soup.new_tag('origin', xyz="0 0 0", rpy="0 0 0")
                visual.append(visual_origin)

                visual_geom = soup.new_tag('geometry')
                visual_mesh = soup.new_tag('mesh', filename='file://' + mesh_file_name)
                visual_geom.append(visual_mesh)
                visual.append(visual_geom)

                link.append(visual)

                robot.append(link)

                # self.srdf_file.write("<inertial>\n")
                # self.srdf_file.write(
                #     "<pose> "
                #     + str(0 + com.x)
                #     + " "
                #     + str(0 + com.y)
                #     + " "
                #     + str(0 + com.z)
                #     + " "
                #     + str(deg2rad(pos.Rotation.Q[0]))
                #     + " "
                #     + str(deg2rad(pos.Rotation.Q[1]))
                #     + " "
                #     + str(deg2rad(pos.Rotation.Q[2]))
                #     + "</pose>\n"
                # )
                # self.srdf_file.write("<inertia>\n")
                # self.srdf_file.write("<ixx>" + float_to_str(A11) + "</ixx>\n")
                # self.srdf_file.write("<ixy>" + float_to_str(A12) + "</ixy>\n")
                # self.srdf_file.write("<ixz>" + float_to_str(A13) + "</ixz>\n")
                # self.srdf_file.write("<iyy>" + float_to_str(A22) + "</iyy>\n")
                # self.srdf_file.write("<iyz>" + float_to_str(A23) + "</iyz>\n")
                # self.srdf_file.write("<izz>" + float_to_str(A33) + "</izz>\n")
                # self.srdf_file.write("</inertia>\n")
                # self.srdf_file.write("<mass>" + str(mass) + "</mass>\n")
                # self.srdf_file.write("</inertial>\n")

                # self.srdf_file.write('<collision name="collision">\n')
                # self.srdf_file.write("<geometry>\n")
                # self.srdf_file.write("<mesh>\n")
                # self.srdf_file.write(
                #     "<uri>model://"
                #     + self.robot_name
                #     + "Static/meshes/"
                #     + name
                #     + ".stl</uri>\n"
                # )
                # self.srdf_file.write("</mesh>\n")
                # self.srdf_file.write("</geometry>\n")
                # self.srdf_file.write("</collision>\n")
                # self.srdf_file.write('<visual name="visual">\n')
                # self.srdf_file.write("<geometry>\n")
                # self.srdf_file.write("<mesh>\n")
                # self.srdf_file.write(
                #     "<uri>model://"
                #     + self.robot_name
                #     + "Static/meshes/"
                #     + name
                #     + ".stl</uri>\n"
                # )
                # self.srdf_file.write("</mesh>\n")
                # self.srdf_file.write("</geometry>\n")
                # self.srdf_file.write("</visual>\n")
                # self.srdf_file.write("</link>\n")

        self.srdf_file.write(soup.prettify())
        self.srdf_file.close()
        return

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
		are met or not. This function is optional."""
        return True

def export_urdf():
    c = URDFExportStatic()
    c.Activated()
    return True


FreeCADGui.addCommand("RC_ExportURDF", URDFExportStatic())


