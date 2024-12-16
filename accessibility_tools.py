# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QTreeWidget,
                             QTreeWidgetItem,
                             QVBoxLayout,
                             QWidget
                             )
from qgis.PyQt.QtGui import QIcon, QFont
import os
import webbrowser
from qgis.core import QgsProject

from .form_raptor_detailed import RaptorDetailed
from .form_raptor_summary import RaptorSummary
from .form_car import CarAccessibility
from .form_pkl import form_pkl
from .form_pkl_car import form_pkl_car
from .form_relative import form_relative
from .form_roads_clean import form_roads_clean
from .form_visualization_clean import form_visualization_clean
from .form_visualization_clean_h import form_visualization_clean_h


class AccessibilityTools(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        self.tree_widget = QTreeWidget()

        self.path_to_pkl = ""
        self.dict_footpath_b_b = {}
        self.dict_footpath = {}

        font = QFont()
        font.setBold(True)

        # change the setting to absolute paths if it is not already set.
        project = QgsProject.instance()
        is_absolute, _ = project.readBoolEntry("Paths", "Absolute")
        if not is_absolute:
            project.writeEntry("Paths", "Absolute", True)
            project.write()

        self.tree_widget.setHeaderHidden(True)
        group1 = QTreeWidgetItem(self.tree_widget, ['Constructing databases'])
        group1.setExpanded(True)
        self.item2 = QTreeWidgetItem(group1, ['Road database'])
        self.item20 = QTreeWidgetItem(
            group1, ['Buidings and visuailization database'])
        #self.item19 = QTreeWidgetItem(
        #    group1, ['Buidings and visuailization database (hexagon)'])
        self.item3 = QTreeWidgetItem(group1, ['Transit routing database'])
        self.item17 = QTreeWidgetItem(group1, ['Car routing database'])

        group2 = QTreeWidgetItem(self.tree_widget, ['Transit accessibility'])
        group2.setExpanded(True)
        group3 = QTreeWidgetItem(group2, ['Service area maps'])
        self.item4 = QTreeWidgetItem(
            group3, ['From service locations – Fixed-time departure'])
        self.item5 = QTreeWidgetItem(
            group3, ['From service locations – Schedule-based departure'])
        self.item6 = QTreeWidgetItem(
            group3, ['To service location – Fixed-time arrival'])
        self.item7 = QTreeWidgetItem(
            group3, ['To service location – Schedule-based arrival'])
        group3.setExpanded(True)

        group4 = QTreeWidgetItem(group2, ['Region maps'])
        self.item8 = QTreeWidgetItem(
            group4, ['From every location – Fixed-time departure'])
        self.item9 = QTreeWidgetItem(
            group4, ['From every location – Schedule-based departure'])
        self.item10 = QTreeWidgetItem(
            group4, ['To every location – Fixed-time arrival'])
        self.item11 = QTreeWidgetItem(
            group4, ['To every location – Schedule-based arrival'])
        group4.setExpanded(True)

        group5 = QTreeWidgetItem(self.tree_widget, ['Car accessibility'])
        group8 = QTreeWidgetItem(group5, ['Service area maps'])
        self.item12 = QTreeWidgetItem(
            group8, ['From service locations – Fixed-time departure'])
        self.item13 = QTreeWidgetItem(
            group8, ['To service location – Fixed-time arrival'])
        group5.setExpanded(True)
        group8.setExpanded(True)

        group6 = QTreeWidgetItem(group5, ['Region maps'])
        self.item14 = QTreeWidgetItem(
            group6, ['From every location – Fixed-time departure'])
        self.item15 = QTreeWidgetItem(
            group6, ['To every location – Fixed-time arrival'])
        group6.setExpanded(True)

        group7 = QTreeWidgetItem(
            self.tree_widget, ['Compare accessibility maps'])
        self.item16 = QTreeWidgetItem(group7, ['Service areas'])
        self.item18 = QTreeWidgetItem(group7, ['Regions'])
        group7.setExpanded(True)

        self.item1 = QTreeWidgetItem(self.tree_widget, ['Help and tutorial'])

        icon1 = os.path.join(os.path.dirname(__file__),
                             'folder.png')  # icon for groups
        icon2 = os.path.join(os.path.dirname(__file__),
                             'ring.png')    # icon for elements

        for group_index in range(self.tree_widget.topLevelItemCount()):
            group_item = self.tree_widget.topLevelItem(group_index)
            group_item.setIcon(0, QIcon(icon1))

            # process second-level elements
            for child_index in range(group_item.childCount()):
                child_item = group_item.child(child_index)

                # if an element has child elements, we consider it a group
                if child_item.childCount() > 0:
                    # icon for a group (folder)
                    child_item.setIcon(0, QIcon(icon1))

                    # process third-level elements
                    for item_index in range(child_item.childCount()):
                        item = child_item.child(item_index)
                        # icon for elements (ring)
                        item.setIcon(0, QIcon(icon2))
                else:
                    # If it is not a group, but a regular element
                    # icon for elements (ring)
                    child_item.setIcon(0, QIcon(icon2))

        icon3 = os.path.join(os.path.dirname(__file__), 'help.png')
        self.item1.setIcon(0, QIcon(icon3))
       
        layout.addWidget(self.tree_widget)

        self.setLayout(layout)
        self.tree_widget.itemDoubleClicked.connect(self.on_tree_item_clicked)

    def on_tree_item_clicked(self, item, column):

        if item == self.item1:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            module_path = os.path.join(current_dir, 'help', 'build', 'html')
            file = os.path.join(module_path, 'introduction.html')
            webbrowser.open(f'file:///{file}')

        if item == self.item2:
            roads_clean = form_roads_clean(
                title="Constructing databases. Road database")
            roads_clean.exec_()

        if item == self.item20:
            visualization_clean = form_visualization_clean(
                title="Constructing databases. Buidings and visuailization database")
            visualization_clean.exec_()

        #if item == self.item19:
        #    visualization_clean_h = form_visualization_clean_h(
        #        title="Constructing databases. Buidings and visuailization database (hexagon)")
        #    visualization_clean_h.exec_()    

        if item == self.item3:
            pkl = form_pkl(
                title="Constructing databases. Transit routing database")
            pkl.textInfo.setPlainText("")
            pkl.show()

        if item == self.item17:
            pkl_car = form_pkl_car(
                title="Constructing databases. Car routing database")
            # pkl_car.textInfo.setPlainText("Description process of building CAR dictionary (pkl)")
            pkl_car.show()

        if item == self.item4:
            raptor_detailed = RaptorDetailed(self, mode=1,
                                             protocol_type=2,
                                             title="Transit accessibility. Service area maps. From service locations – Fixed-time departure",
                                             timetable_mode=False)
            raptor_detailed.textInfo.setPlainText("")
            raptor_detailed.show()

        if item == self.item5:
            raptor_detailed = RaptorDetailed(self, mode=1,
                                             protocol_type=2,
                                             title="Transit accessibility. Service area maps. From service locations – Schedule-based departure",
                                             timetable_mode=True)
            raptor_detailed.textInfo.setPlainText("")
            raptor_detailed.show()

        if item == self.item6:
            raptor_detailed = RaptorDetailed(self, mode=2,
                                             protocol_type=2,
                                             title="Transit accessibility. Service area maps. To service location – Fixed-time arrival",
                                             timetable_mode=False)
            raptor_detailed.textInfo.setPlainText("")
            raptor_detailed.show()

        if item == self.item7:
            raptor_detailed = RaptorDetailed(self, mode=2,
                                             protocol_type=2,
                                             title="Transit accessibility. Service area maps. To service location – Schedule-based arrival",
                                             timetable_mode=True)
            raptor_detailed.textInfo.setPlainText("")
            raptor_detailed.show()

        if item == self.item8:
            raptor_summary = RaptorSummary(self, mode=1,
                                           protocol_type=1,
                                           title="Transit accessibility. Region maps. From every location – Fixed-time departure",
                                           timetable_mode=False
                                           )
            raptor_summary.textInfo.setPlainText("")
            raptor_summary.show()

        if item == self.item9:
            raptor_summary = RaptorSummary(self, mode=1,
                                           protocol_type=1,
                                           title="Transit accessibility. Region maps. From every location – Schedule-based departure",
                                           timetable_mode=True)
            raptor_summary.textInfo.setPlainText("")
            raptor_summary.show()

        if item == self.item10:
            raptor_summary = RaptorSummary(self, mode=2,
                                           protocol_type=1,
                                           title="Transit accessibility. Region maps. To every location – Fixed-time arrival",
                                           timetable_mode=False)
            raptor_summary.textInfo.setPlainText("")
            raptor_summary.show()

        if item == self.item11:
            raptor_summary = RaptorSummary(self, mode=2,
                                           protocol_type=1,
                                           title="Transit accessibility. Region maps. To every location – Schedule-based arrival",
                                           timetable_mode=True)
            raptor_summary.textInfo.setPlainText("")
            raptor_summary.show()

        if item == self.item12:
            car_accessibility = CarAccessibility(mode=1,
                                                 protocol_type=2,
                                                 title="Car accessibility. Service area maps. From service locations – Fixed-time departure")
            # car_accessibility.textInfo.setPlainText("Sample description car accessibility")
            car_accessibility.show()

        if item == self.item13:
            car_accessibility = CarAccessibility(mode=2,
                                                 protocol_type=2,
                                                 title="Car accessibility. Service area maps. To service location – Fixed-time arrival")
            # car_accessibility.textInfo.setPlainText("Sample description car accessibility")
            car_accessibility.show()

        if item == self.item14:
            car_accessibility = CarAccessibility(mode=1,
                                                 protocol_type=1,
                                                 title="Car accessibility. Region maps. From every location – Fixed-time departure")
            # car_accessibility.textInfo.setPlainText("Sample description car accessibility")
            car_accessibility.show()

        if item == self.item15:
            car_accessibility = CarAccessibility(mode=2,
                                                 protocol_type=1,
                                                 title="Car accessibility. Region maps. To every location – Fixed-time arrival")
            # car_accessibility.textInfo.setPlainText("Sample description car accessibility")
            car_accessibility.show()

        if item == self.item16:
            relative = form_relative(
                title="Compare accessibility. Service areas", mode=1)
            relative.textInfo.setPlainText("")
            relative.show()

        if item == self.item18:
            relative = form_relative(
                title="Compare accessibility. Regions", mode=2)
            relative.textInfo.setPlainText("")
            relative.show()       
