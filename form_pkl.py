import os
import webbrowser
import re
import configparser
from pathlib import Path

from qgis.PyQt import QtCore

from qgis.core import (QgsProject,
                       QgsWkbTypes,
                       QgsVectorLayer,
                       QgsMapLayerProxyModel
                       )

from PyQt5.QtCore import (Qt,
                          QEvent,
                          QVariant)

from PyQt5.QtWidgets import (QDialogButtonBox,
                             QDialog,
                             QFileDialog,
                             QApplication,
                             )

from PyQt5.QtGui import QDesktopServices
from PyQt5 import uic

from GTFS import GTFS
from PKL import PKL
from datetime import datetime

from common import get_qgis_info, zip_directory, getDateTime

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'pkl.ui'))

class form_pkl(QDialog, FORM_CLASS):
    def __init__(self, title):
        super().__init__()
        self.setupUi(self)
        self.setModal(False)
        self.setWindowFlags(Qt.Window)
        self.user_home = os.path.expanduser("~")

        self.setWindowTitle(title)

        self.splitter.setSizes(
            [int(self.width() * 0.75), int(self.width() * 0.25)])

        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()

        self.break_on = False

        self.title = title

        self.progressBar.setValue(0)

        self.showAllLayersInCombo_Line(self.cbRoads)
        self.toolButtonRoads.clicked.connect(self.open_file_dialog)

        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)

        self.toolButton_GTFS.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToGTFS))
        self.toolButton_protocol.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToProtocols))

        self.layer_road = self.get_layer_road()

        self.showAllLayersInCombo_Point_and_Polygon(self.cmbLayers)
        self.cmbLayers.installEventFilter(self)
        self.cmbLayers_fields.installEventFilter(self)

        self.fillComboBoxFields_Id(self.cmbLayers, self.cmbLayers_fields)

        self.cbRoads.currentIndexChanged.connect(self.get_layer_road)

        self.cmbLayers.currentIndexChanged.connect(
            lambda: self.fillComboBoxFields_Id
            (self.cmbLayers, self.cmbLayers_fields))

        self.btnBreakOn.clicked.connect(self.set_break_on)

        self.run_button = self.buttonBox.addButton(
            "Run", QDialogButtonBox.ActionRole)
        self.close_button = self.buttonBox.addButton(
            "Close", QDialogButtonBox.RejectRole)
        self.help_button = self.buttonBox.addButton(
            "Help", QDialogButtonBox.HelpRole)

        self.run_button.clicked.connect(self.on_run_button_clicked)
        self.close_button.clicked.connect(self.on_close_button_clicked)
        self.help_button.clicked.connect(self.on_help_button_clicked)

        self.ParametrsShow()

    def get_layer_road(self):
        selected_item = self.cbRoads.currentText()

        if os.path.isfile(selected_item):
            layer_road = QgsVectorLayer(selected_item, "LayerRoad", "ogr")
        else:
            layers = QgsProject.instance().mapLayersByName(selected_item)
            if layers:  
                layer_road = layers[0]
            else:
                layer_road = None  

        return layer_road

    def open_file_dialog(self):
        
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Choose a File",
            "",
            "Shapefile (*.shp);"
        )

        if file_path:
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            layer = QgsVectorLayer(file_path, file_name, "ogr")
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                self.cbRoads.addItem(file_path, file_path)
                
                index = self.cbRoads.findText(file_path)
                self.cbRoads.setCurrentIndex(index)

    def fillComboBoxFields_Id(self, obj_layers, obj_layer_fields):
        obj_layer_fields.clear()
        selected_layer_name = obj_layers.currentText()
        layers = QgsProject.instance().mapLayersByName(selected_layer_name)

        if not layers:
            return
        layer = layers[0]

        fields = layer.fields()
        osm_id_exists = False

        # regular expression to check for the presence of only digit
        digit_pattern = re.compile(r'^\d+$')

        # field type and value validation
        for field in fields:
            field_name = field.name()
            field_type = field.type()

            if field_type in (QVariant.Int, QVariant.Double, QVariant.LongLong):
                # add numeric fields
                obj_layer_fields.addItem(field_name)
                if field_name.lower() == "osm_id":
                    osm_id_exists = True
            elif field_type == QVariant.String:
                # check the first value of the field for digits only
                first_value = None
                for feature in layer.getFeatures():
                    first_value = feature[field_name]
                    break  # stop after the first value

                if first_value is not None and digit_pattern.match(str(first_value)):
                    obj_layer_fields.addItem(field_name)
                    if field_name.lower() == "osm_id":
                        osm_id_exists = True

        if osm_id_exists:
            # iterate through all the items in the combobox and compare them with "osm_id", 
            # ignoring the case
            for i in range(obj_layer_fields.count()):
                if obj_layer_fields.itemText(i).lower() == "osm_id":
                    obj_layer_fields.setCurrentIndex(i)
                    break

    def showAllLayersInCombo_Line(self, cmb):
        layers = QgsProject.instance().mapLayers().values()
        line_layers = [layer for layer in layers
                       if isinstance(layer, QgsVectorLayer) and
                       layer.geometryType() == QgsWkbTypes.LineGeometry and
                       not layer.name().startswith("Temp") and
                       'memory' not in layer.dataProvider().dataSourceUri()]
        cmb.clear()
        for layer in line_layers:
            cmb.addItem(layer.name(), [])

    def showAllLayersInCombo_Point_and_Polygon(self, cmb):
        layers = QgsProject.instance().mapLayers().values()
        point_layers = [layer for layer in layers
                        if isinstance(layer, QgsVectorLayer) and
                        (layer.geometryType() == QgsWkbTypes.PointGeometry or layer.geometryType() == QgsWkbTypes.PolygonGeometry)]
        cmb.clear()
        for layer in point_layers:
            cmb.addItem(layer.name(), [])

    def EnableComboBox(self, state):

        if state == QtCore.Qt.Checked:
            self.cmbFields.setEnabled(True)
        else:
            self.cmbFields.setEnabled(False)

    def openFolder(self, url):
        QDesktopServices.openUrl(url)

    def set_break_on(self):
        self.break_on = True
        self.close_button.setEnabled(True)

    def on_run_button_clicked(self):

        self.run_button.setEnabled(False)

        self.break_on = False
        self.layer_road = self.get_layer_road()

        if not (self.check_folder_and_file()):
            self.run_button.setEnabled(True)
            return 0

        if not self.cmbLayers.currentText():
            self.run_button.setEnabled(True)
            self.setMessage("Choose the layer")
            return 0

        if not (self.check_feature_from_layer()):
            self.run_button.setEnabled(True)
            return 0

        if not (self.check_type_layer_road()):
            self.run_button.setEnabled(True)
            return 0

        self.saveParameters()
        self.readParameters()

        self.setMessage("Starting ...")
        self.close_button.setEnabled(False)
        self.textLog.clear()
        self.tabWidget.setCurrentIndex(1)
        self.textLog.append("<a style='font-weight:bold;'>[System]</a>")
        qgis_info = get_qgis_info()

        info_str = "<br>".join(
            [f"{key}: {value}" for key, value in qgis_info.items()])
        self.textLog.append(f'<a> {info_str}</a>')
        self.textLog.append("<a style='font-weight:bold;'>[Mode]</a>")
        self.textLog.append(f'<a> Mode: {self.title}</a>')

        self.textLog.append("<a style='font-weight:bold;'>[Settings]</a>")
        
        layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['Layer_pkl'])[0]
        self.layer_buildings_path = layer.dataProvider().dataSourceUri().split("|")[
            0]

        self.textLog.append(
            f"<a> Layer of roads: {self.config['Settings']['Roads_pkl']}</a>")
        self.textLog.append(
            f"<a> Layer of buildings: {self.layer_buildings_path}</a>")
        self.textLog.append(
            f"<a> GTFS folder: {self.config['Settings']['PathToGTFS_pkl']}</a>")
        self.textLog.append(
            f"<a> Folder to store transit database: {self.config['Settings']['PathToProtocols_pkl']}</a>")

        self.prepare()
        self.close_button.setEnabled(True)

    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        module_path = os.path.join(current_dir, 'help', 'build', 'html')
        file = os.path.join(module_path, 'building_pkl.html')
        webbrowser.open(f'file:///{file}')

    def showFoldersDialog(self, obj):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", obj.text())
        if folder_path:
            obj.setText(folder_path)
        else:
            obj.setText(obj.text())

    def readParameters(self):
        project_directory = os.path.dirname(QgsProject.instance().fileName())
        file_path = os.path.join(
            project_directory, 'parameters_accessibility.txt')

        self.config.read(file_path)

        if 'PathToGTFS_pkl' not in self.config['Settings']:
            self.config['Settings']['PathToGTFS_pkl'] = 'C:/'

        if 'PathToProtocols_pkl' not in self.config['Settings']:
            self.config['Settings']['PathToProtocols_pkl'] = 'C:/'

        if 'Roads_pkl' not in self.config['Settings']:
            self.config['Settings']['Roads_pkl'] = ''

        if 'Layer_field_pkl' not in self.config['Settings']:
            self.config['Settings']['Layer_field_pkl'] = ''

    # update config file

    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')

        self.config['Settings']['PathToProtocols_pkl'] = self.txtPathToProtocols.text()
        self.config['Settings']['PathToGTFS_pkl'] = self.txtPathToGTFS.text()
        self.config['Settings']['Roads_pkl'] = self.cbRoads.currentText()
        self.config['Settings']['Layer_pkl'] = self.cmbLayers.currentText()
        self.config['Settings']['Layer_field_pkl'] = self.cmbLayers_fields.currentText()

        with open(f, 'w') as configfile:
            self.config.write(configfile)

    def ParametrsShow(self):

        self.readParameters()

        self.txtPathToGTFS.setText(self.config['Settings']['PathToGTFS_pkl'])

        self.cmbLayers.setCurrentText(self.config['Settings']['Layer_pkl'])
        self.cmbLayers_fields.setCurrentText(
            self.config['Settings']['Layer_field_pkl'])
        self.txtPathToProtocols.setText(
            self.config['Settings']['PathToProtocols_pkl'])

        if os.path.isfile(self.config['Settings']['Roads_pkl']):
            self.cbRoads.addItem(self.config['Settings']['Roads_pkl'])
        self.cbRoads.setCurrentText(self.config['Settings']['Roads_pkl'])

    def check_folder_and_file(self):

        if self.cbRoads.currentText() == "":
            self.setMessage(f"The layer of roads is empty")
            return False

        feature_count = self.layer_road.featureCount()
        if feature_count == 0:
            self.setMessage(
                f"No features in the layer '{self.cbRoads.currentText()}'")
            return False

        if not os.path.exists(self.txtPathToGTFS.text()):
            self.setMessage(
                f"Folder '{self.txtPathToGTFS.text()}' does not exist")
            return False

        required_files = ['stops.txt', 'trips.txt',
                          'routes.txt', 'stop_times.txt']
        missing_files = [file for file in required_files if not os.path.isfile(
            os.path.join(self.txtPathToGTFS.text(), file))]

        if missing_files:
            limited_files = missing_files[:2]
            missing_files_message = ", ".join(limited_files)
            self.setMessage(
                f"Files are missing in the '{self.txtPathToGTFS.text()}' forlder: {missing_files_message}")
            return False

        if not os.path.exists(self.txtPathToProtocols.text()):
            self.setMessage(
                f"Folder '{self.txtPathToProtocols.text()}' does not exist")
            return False

        try:
            tmp_prefix = "write_tester"
            filename = f'{self.txtPathToProtocols.text()}//{tmp_prefix}'
            with open(filename, 'w') as f:
                f.write("test")
            os.remove(filename)
        except Exception as e:
            self.setMessage(
                f"Access to the folder '{self.txtPathToProtocols.text()}' is denied")
            return False

        return True

    def setMessage(self, message):
        self.lblMessages.setText(message)

    def check_type_layer_road(self):

        layer = self.layer_road
        try:
            features = layer.getFeatures()
        except:
            self.setMessage(
                f"The layer in '{self.cbRoads.currentText()}' is empty")
            return 0

        for feature in features:
            feature_geometry = feature.geometry()
            feature_geometry_type = feature_geometry.type()
            break

        if (feature_geometry_type != QgsWkbTypes.LineGeometry):
            self.setMessage(
                f"Features in the layer in '{self.cbRoads.currentText()}' must be polylines")
            return 0

        return 1

    def check_feature_from_layer(self):

        layer = self.cmbLayers.currentText()
        if layer == "":
            self.setMessage(f"The layer is empty")
            return 0
        layer = QgsProject.instance().mapLayersByName(layer)[0]

        try:
            features = layer.getFeatures()
        except:
            self.setMessage(f'The layer {layer} is empty')
            return 0

        return 1

    def prepare(self):
        begin_computation_time = datetime.now()
        begin_computation_str = begin_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")
        self.textLog.append(f'<a>Started: {begin_computation_str}</a>')

        self.break_on = False

        layer_origins = self.config['Settings']['Layer_pkl']
        layer_origins = QgsProject.instance().mapLayersByName(layer_origins)[0]
        layer_origins_field = self.config['Settings']['Layer_field_pkl']

        QApplication.processEvents()

        gtfs_path = os.path.join(
            self.config['Settings']['PathToProtocols_pkl'], 'GTFS')
        pkl_path = self.config['Settings']['PathToProtocols_pkl']

        path_to_file = self.config['Settings']['PathToProtocols_pkl']+'/GTFS//'
        path_to_GTFS = self.config['Settings']['PathToGTFS_pkl']+'//'

        run = True

        if True:
            if not os.path.exists(gtfs_path):
                os.makedirs(gtfs_path)

            if not os.path.exists(pkl_path):
                os.makedirs(pkl_path)
            

            if True: 

                calc_GTFS = GTFS(self,
                                 path_to_file,
                                 path_to_GTFS,
                                 pkl_path,
                                 layer_origins,
                                 self.layer_road,
                                 layer_origins_field,
                                 )
                res = calc_GTFS.correcting_files()

                if res == 1:

                    calc_PKL = PKL(self,
                                   dist=400,
                                   path_to_pkl=pkl_path,
                                   path_to_GTFS=gtfs_path,
                                   layer_buildings=layer_origins,
                                   mode_append=False
                                   )
                    calc_PKL.create_files()

                    zip_directory(path_to_file)

            QApplication.processEvents()
            after_computation_time = datetime.now()
            after_computation_str = after_computation_time.strftime(
                '%Y-%m-%d %H:%M:%S')
            self.textLog.append(f'<a>Finished: {after_computation_str}</a>')
            duration_computation = after_computation_time - begin_computation_time
            duration_without_microseconds = str(
                duration_computation).split('.')[0]
            self.textLog.append(
                f'<a>Processing time: {duration_without_microseconds}</a>')

            text = self.textLog.toPlainText()
            postfix = getDateTime()
            filelog_name = f'{pkl_path}//log_pkl_pt_{postfix}.txt'
            with open(filelog_name, "w") as file:
                file.write(text)

            if res == 1:
                self.textLog.append(
                    f'<a href="file:///{pkl_path}" target="_blank" >pkl in folder</a>')

            self.setMessage(f'Finished')

        if not (run):
            self.run_button.setEnabled(True)
            self.close_button.setEnabled(True)
            self.textLog.clear()
            self.tabWidget.setCurrentIndex(0)
            self.setMessage("")

    # if the combobox is in focus, we ignore the mouse wheel scroll event
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            if obj.hasFocus():
                event.ignore()
                return True
        return super().eventFilter(obj, event)
