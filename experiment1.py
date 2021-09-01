## Populate a layer stored in variable 'vlayer' with features using rows stored in variable 'rows'
## MAKE SURE to run import_rows_to_memory_using_driver.py and create_temporal_layer.py before
## running this script
import time
now = time.time()
FRAMES_NB = 50 # Number of frames to generate
canvas = iface.mapCanvas()
temporalController = canvas.temporalController()
currentFrameNumber = temporalController.currentFrameNumber()
features_list = []
interpolation_times = []
feature_times = []

# For every frame, use  mobility driver to retrieve valueAtTimestamp(frameTime) and create a corresponding feature
for i in range(FRAMES_NB):
    dtrange = temporalController.dateTimeRangeForFrameNumber(currentFrameNumber+i)
    for row in rows:
        now2 = time.time()
        val = row[0].valueAtTimestamp(dtrange.begin().toPyDateTime().replace(tzinfo=row[0].startTimestamp.tzinfo)) # Get interpolation
        interpolation_times.append(time.time()-now2)
        if val: # If interpolation succeeds
            now3 = time.time()
            feat = QgsFeature(vlayer.fields())   # Create feature
            feat.setAttributes([dtrange.end()])  # Set its attributes
            geom = QgsGeometry.fromPointXY(QgsPointXY(val[0],val[1])) # Create geometry from valueAtTimestamp
            feat.setGeometry(geom) # Set its geometry
            feature_times.append(time.time()-now3)
            features_list.append(feat)
        
now4 = time.time()
vlayer.startEditing()
vlayer.addFeatures(features_list) # Add list of features to vlayer
vlayer.commitChanges()
iface.vectorLayerTools().stopEditing(vlayer)
now5 = time.time()

print("Total time:", time.time()-now, "s.")
print("Add features time:", now5-now4, "s.") # Time to add features to the map
print("Interpolation:", sum(interpolation_times), "s.")
print("Number of features generated:", len(features_list))
