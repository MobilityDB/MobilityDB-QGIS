import psycopg2
from mobilitydb.psycopg import register

# Parameters
FRAMES_NB = 50    #Number of frames per buffer

def generateFrames(task, timestamps):
    print('Started task: {}'.format(task.description()))
    # First query the database
    t1 = timestamps[0].toString("yyyy-MM-dd HH:mm:ss")
    t2 = timestamps[-1].toString("yyyy-MM-dd HH:mm:ss")
    select_query = "select atPeriod(trip, period('"+t1+"', '"+t2+"', true, true)) from trips"
    cursor.execute(select_query)
    rows = cursor.fetchall()
    # Generate features from timestamps
    print("Query done, starting feature generation")
    features_list = []
    for t in timestamps:
        for row in rows:
            val = None
            if row[0]:
                val = row[0].valueAtTimestamp(t.toPyDateTime().replace(tzinfo=row[0].startTimestamp.tzinfo)) # Get interpolation
            if val: # If interpolation succeeds
                feat = QgsFeature(vlayer.fields())   # Create feature
                feat.setAttributes([t])  # Set its attributes
                geom = QgsGeometry.fromPointXY(QgsPointXY(val[0],val[1])) # Create geometry from valueAtTimestamp
                feat.setGeometry(geom) # Set its geometry
                features_list.append(feat)
    print("Features Generated")
    return features_list

def workdone(exception, features_list):
    print("Adding features")
    vlayer.startEditing()
    vlayer.addFeatures(features_list,flags=QgsFeatureSink.FastInsert)
    vlayer.commitChanges()
    iface.vectorLayerTools().stopEditing(vlayer)
    print("Workdone")
    
def onNewFrame(dtrange):
    canvas = iface.mapCanvas()
    temporalController = canvas.temporalController()
    currentFrameNumber = temporalController.currentFrameNumber()
    firstFrameOfBuffer = currentFrameNumber + FRAMES_NB
    if currentFrameNumber%FRAMES_NB == 0 and firstFrameOfBuffer + FRAMES_NB <= temporalController.totalFrameCount():
        timestamps = []
        for i in range(FRAMES_NB):
            timestamps.append(temporalController.dateTimeRangeForFrameNumber(firstFrameOfBuffer+i).begin())
        globals()['task1'] = QgsTask.fromFunction('Generate Frames', generateFrames, on_finished=workdone, timestamps=timestamps)
        QgsApplication.taskManager().addTask(globals()['task1'])

# Open new connection to database
try:
    # Set the connection parameters to PostgreSQL
    connection = psycopg2.connect(host='localhost', database='postgres', user='postgres', password='postgres')
    connection.autocommit = True

    # Register MobilityDB data types
    register(connection)
    # Open a cursor to perform database operations
    cursor = connection.cursor()

except (Exception, psycopg2.Error) as error:
    print("Error while connecting to PostgreSQL", error)

# Create vector layer
vlayer = QgsVectorLayer("Point", "points_visualization", "memory")
pr = vlayer.dataProvider()
pr.addAttributes([QgsField("time", QVariant.DateTime)])
vlayer.updateFields()
tp = vlayer.temporalProperties()
tp.setIsActive(True)
tp.setMode(1) #single field with datetime
tp.setStartField("time")
vlayer.updateFields()
crs = vlayer.crs()
crs.createFromId(22992)
vlayer.setCrs(crs)
QgsProject.instance().addMapLayer(vlayer)

# Connect temporal controller to onNewFrame()
canvas = iface.mapCanvas()
temporalController = canvas.temporalController()
temporalController.updateTemporalRange.connect(onNewFrame)

# Populate first buffer and second buffer
temporalController.rewindToStart()
timestamps = []
for i in range(2*FRAMES_NB):
    timestamps.append(temporalController.dateTimeRangeForFrameNumber(i).begin())
globals()['task1'] = QgsTask.fromFunction('Generate Frames', generateFrames, on_finished=workdone, timestamps=timestamps)
QgsApplication.taskManager().addTask(globals()['task1'])
