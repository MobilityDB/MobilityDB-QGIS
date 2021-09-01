import processing
import time

FRAMES_NB = 1
temporalController = iface.mapCanvas().temporalController()
frame = temporalController.currentFrameNumber()
datetime=temporalController.dateTimeRangeForFrameNumber(frame).begin()
processing_times = []
add_features_times = []

# Processing algorithm parameters
parameters = { 'DATABASE' : "postgres", # Enter name of database to query
'SQL' : "",
'ID_FIELD' : 'id'
}

# Setup resulting vector layer
vlayer = QgsVectorLayer("Point", "points_4", "memory")
pr = vlayer.dataProvider()
pr.addAttributes([QgsField("id", QVariant.Int), QgsField("time", QVariant.DateTime)])
vlayer.updateFields()
tp = vlayer.temporalProperties()
tp.setIsActive(True)
tp.setMode(1)  # Single field with datetime
tp.setStartField("time")
vlayer.updateFields()
vlayer.startEditing()

# Populate vector layer with features at beginning time of every frame
now = time.time()
for i in range(FRAMES_NB):
    datetime=temporalController.dateTimeRangeForFrameNumber(frame+i).end()
    sql = "SELECT ROW_NUMBER() OVER() as id, '"+datetime.toString("yyyy-MM-dd HH:mm:ss")+"' as time, valueAtTimestamp(trip, '"+datetime.toString("yyyy-MM-dd HH:mm:ss")+"') as geom FROM trips"
    parameters['SQL'] = sql # Update algorithm parameters with sql query
    now = time.time()
    output = processing.run("qgis:postgisexecuteandloadsql", parameters) # Algorithm returns a layer containing the features, layer can be accessed by output['OUTPUT']
    now2 = time.time()
    processing_times.append(now2-now)
    vlayer.addFeatures(list(output['OUTPUT'].getFeatures())) # Add features from algorithm output layer to result layer
    add_features_times.append(time.time()-now2)
    
vlayer.commitChanges()
iface.vectorLayerTools().stopEditing(vlayer)

# Add result layer to project
QgsProject.instance().addMapLayer(vlayer)
print("Processing times : " + str(sum(processing_times)))
print("Add features times : " + str(sum(add_features_times)))
print("Total time : " + str(sum(processing_times)+sum(add_features_times)))
