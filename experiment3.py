## MAKE SURE TO RUN create_temporal_layer.py BEFORe RUNNING THIS SCRIPT
# Import rows of mobilitydb table into a 'rows' variable
import psycopg2
import time
from mobilitydb.psycopg import register

canvas = iface.mapCanvas()
temporalController = canvas.temporalController()
currentFrameNumber = temporalController.currentFrameNumber()
FRAMES_NB = 1
connection = None
now = time.time()

try:
    # Set the connection parameters to PostgreSQL
    connection = psycopg2.connect(host='localhost', database='postgres', user='postgres', password='postgres')
    connection.autocommit = True

    # Register MobilityDB data types
    register(connection)

    # Open a cursor to perform database operations
    cursor = connection.cursor()

    # Query the database and obtain data as Python objects
    
    dt1 = temporalController.dateTimeRangeForFrameNumber(currentFrameNumber).begin().toString("yyyy-MM-dd HH:mm:ss")
    dt2 = temporalController.dateTimeRangeForFrameNumber(currentFrameNumber+FRAMES_NB-1).begin().toString("yyyy-MM-dd HH:mm:ss")
    select_query = "select atPeriod(trip, period('"+dt1+"', '"+dt2+"', true, true)) from trips"
    #select_query = "SELECT valueAtTimestamp(trip, '"+range.end().toString("yyyy-MM-dd HH:mm:ss-04")+"') FROM trips_test"
    
    cursor.execute(select_query)
    rows = cursor.fetchall()
    print("Query execution time:", time.time()-now)


except (Exception, psycopg2.Error) as error:
    print("Error while connecting to PostgreSQL", error)

finally:
    # Close the connection
    if connection:
        connection.close()
features_list = []
interpolation_times = []
feature_times = []

# For every frame, use  mobility driver to retrieve valueAtTimestamp(frameTime) and create a corresponding feature
for i in range(FRAMES_NB):
    dtrange = temporalController.dateTimeRangeForFrameNumber(currentFrameNumber+i)
    for row in rows:
        now2 = time.time()
        val = None
        if row[0]:
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
