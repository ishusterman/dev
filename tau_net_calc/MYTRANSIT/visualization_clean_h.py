import os
from datetime import datetime

from PyQt5.QtCore import QVariant

from qgis.core import (
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsTask,
    QgsProject,
    QgsFeature,
    QgsField,
    QgsSpatialIndex,
    edit)

from qgis import processing

from common import getDateTime, convert_meters_to_degrees

class cls_clean_visualization_h(QgsTask):
    def __init__(self, parent, begin_computation_time, layer, folder_name, task_name="Hexagones Task"):
        super().__init__(task_name)
        self.parent = parent
        self.begin_computation_time = begin_computation_time
        self.layer = layer
        self.folder_name = folder_name
        self.exception = None
        self.break_on = False
        self.parent.progressBar.setMaximum(10)

    def run(self):

        uri = self.layer.dataProvider().dataSourceUri()
        input_layer_path = uri.split("|")[0] if "|" in uri else uri
        self.layer_road_path_dir = os.path.dirname(input_layer_path)
        file_name = os.path.basename(input_layer_path)
        self.name, self.ext = os.path.splitext(file_name)
        input_layer = QgsVectorLayer(input_layer_path, "Layer Name", "ogr")

        ################################
        self.parent.setMessage('Delete holes ...')
        deleteholes_result = processing.run("qgis:deleteholes", {
            'INPUT': input_layer,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })
        layer_deleteholes = deleteholes_result['OUTPUT']
        if self.break_on:
            return 0
        self.parent.progressBar.setValue(1)
        ###############################

        self.parent.setMessage('Remove null geometries ...')
        empty_geometry_features = []

        for feature in layer_deleteholes.getFeatures():
            if feature.geometry().isNull():
                empty_geometry_features.append(feature)

        if empty_geometry_features:
            with edit(layer_deleteholes):
                for feature in empty_geometry_features:
                    layer_deleteholes.deleteFeature(feature.id())

        if self.break_on:
            return 0
        self.parent.progressBar.setValue(2)
        ##############################

        self.parent.setMessage('Converting multipart to singlepart ...')
        singlepart_result = processing.run("native:multiparttosingleparts", {
            'INPUT': layer_deleteholes,
            'OUTPUT': 'memory:'
        })
        layer_singlepart = singlepart_result['OUTPUT']
        if self.break_on:
            return 0
        self.parent.progressBar.setValue(3)

        ############################################

        self.parent.setMessage('Renumbering repeated osm_id ...')
        osm_id_counter = {}
        layer_singlepart.startEditing()

        for feature in layer_singlepart.getFeatures():
            osm_id = feature['osm_id']
            if osm_id in osm_id_counter:
                osm_id_counter[osm_id] += 1
                new_id = f"{osm_id}_{osm_id_counter[osm_id]}"
            else:

                osm_id_counter[osm_id] = 1
                new_id = osm_id
            feature['osm_id'] = new_id
            layer_singlepart.updateFeature(feature)
        layer_singlepart.commitChanges()
        if self.break_on:
            return 0
        self.parent.progressBar.setValue(4)
        #############################################
        
        self.parent.setMessage('Constructing centroids ...')
        centroids_layer = self.make_centroids(layer_singlepart)
        if self.break_on:
            return 0
        self.parent.progressBar.setValue(5)
        
        
        #############################################
        self.parent.setMessage('Constructing hexagones ...')

        first_feature = next(input_layer.getFeatures())
        first_point = first_feature.geometry().centroid().asPoint()
        units = input_layer.crs().mapUnits()
        crs_grad = (units == 6)
        SPACING = 100
        if crs_grad:
            SPACING = convert_meters_to_degrees(
                SPACING, first_point.y())
        
        hexagones_result = processing.run("native:creategrid", 
                       {'TYPE':4,
                        'EXTENT':input_layer.extent(),
                        'HSPACING':SPACING,
                        'VSPACING':SPACING,
                        'HOVERLAY':0,
                        'VOVERLAY':0,
                        'CRS':input_layer.crs(),
                        'OUTPUT':'TEMPORARY_OUTPUT'}
                        )
        hexagones_layer = hexagones_result['OUTPUT']
        
        if self.break_on:
            return 0
        self.parent.progressBar.setValue(6)
        #############################################
        self.parent.setMessage('Filtering hexagones ...')
        self.filter_hexagons_by_intersection(hexagones_layer, layer_singlepart)
        
        if self.break_on:
            return 0
        self.parent.progressBar.setValue(7)
        #############################################
        self.parent.setMessage('Add nearest osm_id to hexogons ...')
        self.add_nearest_osm_id(hexagones_layer, centroids_layer)
        QgsProject.instance().addMapLayer(hexagones_layer, True)

        if self.break_on:
            return 0
        self.parent.progressBar.setValue(8)

        """
        #########################
        # Saving result
        #########################
        self.parent.setMessage('Saving ...')
        file_dir = self.folder_name
        self.output_file_name = f"{self.name}_voronoi{self.ext}"
        output_path = os.path.join(file_dir, self.output_file_name)
        self.unique_output_path = self.get_unique_path(output_path)
        self.layer_name = os.path.splitext(
            os.path.basename(self.unique_output_path))[0]
        QgsVectorFileWriter.writeAsVectorFormat(
            clip_layer,
            self.unique_output_path,
            "UTF-8",
            clip_layer.crs(),
            "ESRI Shapefile"
        )
        saved_layer = QgsVectorLayer(
            self.unique_output_path, self.layer_name, "ogr")
        if saved_layer.isValid():
            QgsProject.instance().addMapLayer(saved_layer)
        if self.break_on:
            return 0
        self.parent.progressBar.setValue(9)
        ###################################
        QgsProject.instance().removeMapLayer(voronoi_layer)
        """
        self.write_finish_info()
        self.parent.btnBreakOn.setEnabled(False)
        self.parent.close_button.setEnabled(True)
        self.parent.setMessage('Finished')
        self.parent.progressBar.setValue(10)
        return True

    def write_finish_info(self):
        after_computation_time = datetime.now()
        after_computation_str = after_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.parent.textLog.append(f'<a>Finished: {after_computation_str}</a>')
        duration_computation = after_computation_time - self.begin_computation_time
        duration_without_microseconds = str(duration_computation).split('.')[0]
        self.parent.textLog.append(
            f'<a>Processing time: {duration_without_microseconds}</a>')

        text = self.parent.textLog.toPlainText()
        postfix = getDateTime()

        filelog_name = f'{self.folder_name}//log_visualization_database_{postfix}.txt'
        with open(filelog_name, "w") as file:
            file.write(text)

        self.parent.textLog.append(
            f'"{self.layer_name}.shp" in <a href="file:///{self.folder_name}" target="_blank" >folder</a>')
        self.parent.textLog.append(
            f'"{self.centoids_layer_name}.shp" in <a href="file:///{self.folder_name}" target="_blank" >folder</a>')

        self.parent.setMessage(f'Finished')

    def cancel(self):
        try:
            self.parent.progressBar.setValue(0)
            self.parent.setMessage(f'')
            self.break_on = True
            super().cancel()
        except:
            return

    def get_unique_path(self, base_path):
        """
        Generates a unique path by appending an index if the file already exists.
        :param base_path: The initial path for saving the file
        :return: A unique path with an appended index
        """
        if not os.path.exists(base_path):
            return base_path

        base, ext = os.path.splitext(base_path)
        index = 1
        while os.path.exists(f"{base}_{index}{ext}"):
            index += 1
        return f"{base}_{index}{ext}"

    def make_centroids(self, input_layer):

        centroid_layer = QgsVectorLayer(
            "Point?crs=" + input_layer.crs().authid(), "Centroids", "memory")
        provider = centroid_layer.dataProvider()
        provider.addAttributes(input_layer.fields())
        centroid_layer.updateFields()

        with edit(centroid_layer):
            for i, feature in enumerate(input_layer.getFeatures()):
                if i % 100 == 0:
                    if self.break_on:
                        return 0
                centroid = feature.geometry().centroid()
                if centroid.isEmpty():
                    continue
                centroid_feature = QgsFeature()
                centroid_feature.setGeometry(centroid)
                centroid_feature.setAttributes(feature.attributes())
                if centroid_feature.geometry() is not None:
                    provider.addFeature(centroid_feature)

        file_dir = self.folder_name
        self.output_file_name = f"{self.name}_centroids{self.ext}"
        output_path = os.path.join(file_dir, self.output_file_name)
        self.unique_output_path = self.get_unique_path(output_path)
        self.layer_name = os.path.splitext(
            os.path.basename(self.unique_output_path))[0]

        output_path = self.unique_output_path
        QgsVectorFileWriter.writeAsVectorFormat(
            centroid_layer,
            output_path,
            "utf-8",
            input_layer.crs(),
            "ESRI Shapefile"
        )

        layer_name = os.path.splitext(os.path.basename(output_path))[0]
        centroid_layer = QgsProject.instance().addMapLayer(
            QgsVectorLayer(output_path, layer_name, "ogr"))
        #input_layer_path = centroid_layer.id()

        first_feature = next(centroid_layer.getFeatures())
        first_point = first_feature.geometry().centroid().asPoint()
        units = centroid_layer.crs().mapUnits()
        crs_grad = (units == 6)
        dist_buffer = 50
        if crs_grad:
            dist_buffer = convert_meters_to_degrees(
                dist_buffer, first_point.y())
        return centroid_layer
        #return input_layer_path, layer_name, dist_buffer

    

    def filter_hexagons_by_intersection(self, hexagones_layer, input_layer):
        """
        Retain only features in hexagones_layer that intersect with any feature in input_layer.

        :param hexagones_layer: QgsVectorLayer, the layer containing hexagons.
        :param input_layer: QgsVectorLayer, the input layer to check intersections against.
        :raises ValueError: If either of the layers is invalid.
        """
        
        # Start editing the hexagones_layer
        if not hexagones_layer.isEditable():
            hexagones_layer.startEditing()

        # Create a spatial index for input_layer
        input_index = QgsSpatialIndex(input_layer.getFeatures())
        count = hexagones_layer.featureCount()

        # Iterate through hexagones_layer and check for intersection
        for i, hex_feature in enumerate(hexagones_layer.getFeatures()):
            if i%10000 == 0:
                if self.break_on:
                    return 0
                self.parent.setMessage(f'Filtering hexagon {i} from {count}...')
            hex_geom = hex_feature.geometry()

            # Get potential intersecting features using the spatial index
            candidate_ids = input_index.intersects(hex_geom.boundingBox())

            # Check if the hexagon intersects with any candidate geometry
            intersects = False
            for candidate_id in candidate_ids:
                candidate_feature = input_layer.getFeature(candidate_id)
                if hex_geom.intersects(candidate_feature.geometry()):
                    intersects = True
                    break

            # Delete the hexagon if it does not intersect
            if not intersects:
                hexagones_layer.deleteFeature(hex_feature.id())

        # Commit the changes to the hexagones_layer
        hexagones_layer.commitChanges()

    def add_nearest_osm_id(self, hexagones_layer, centroids_layer):

        hexagones_layer.startEditing()

        if "osm_id" not in [field.name() for field in hexagones_layer.fields()]:
            hexagones_layer.dataProvider().addAttributes([QgsField("osm_id", QVariant.String)])
            hexagones_layer.updateFields()

        field_index = hexagones_layer.fields().lookupField("osm_id")    
    
        input_index = QgsSpatialIndex(centroids_layer.getFeatures())
        input_features = {feat.id(): feat for feat in centroids_layer.getFeatures()}
        hex_centroids = {feat.id(): feat.geometry().centroid() for feat in hexagones_layer.getFeatures()}
        count = len(hex_centroids)

        updates = {}
        for i, (feat_id, hex_centroid) in enumerate(hex_centroids.items()):
            if i % 100 == 0:
                if self.break_on:
                    return 0
                self.parent.setMessage(f'Add nearest osm_id to hexagons {i} from {count}...')
        
            nearest_id = input_index.nearestNeighbor(hex_centroid.asPoint(), 1)
            if nearest_id:
                nearest_feature = input_features[nearest_id[0]]
                nearest_osm_id = nearest_feature["osm_id"]
                updates[feat_id] = {field_index: nearest_osm_id}    
        
        hexagones_layer.dataProvider().changeAttributeValues(updates)
        
        hexagones_layer.commitChanges()

        



