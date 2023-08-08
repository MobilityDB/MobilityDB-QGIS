# Visualizing MobilityDB data using QGIS
The work presented here was carried out as part of an MA1 project at the ULB. It attempts to explore and compare different ways to visualize MobilityDB data using QGIS, a desktop application that can be used to view, edit and analyze geospatial data.

A report with the detailed information is available [here](https://docs.mobilitydb.com/pub/MobilityDB-QGIS.pdf))

## Problem description

The goal is to be able to display MobilityDB data using QGIS, for example, moving points on a 2D plane. Since MobilityDB introduces new data types to account for its temporal dimension, it is not possible to simply "link" a temporal geometry column from the database to a QGIS layer. To display such data, we need to transform it into types QGIS recognizes. To do the actual visualization, we can make use of QGIS's temporal controller. This tool allows for the creation of animations (an animation frame contains a set of features during a given time range) and introduces a way to filter which features in a layer are shown depending on one or several time attributes. 

## Assumptions

The data set used for the experiments is a table of 100 rows that each contain the information of the trajectory of a single point. Each row is divided into several columns. Several columns contain non-spatial information (e.g. a unique identifier). One column stores the spatio-temporal information of each point (i.e. its trajectory) as a tgeompoint. The goal is to interpolate each point's tgeompoint trajectory for every frame's timestamp of QGIS's temporal controller to create an animation.

## Using the Temporal Controller
Since we need a way to visualize data with a temporal dimension, we'll be using the temporal controller. Each frame from this controller will be showing the collection of objects at a different time. Stringing these frames together will produce an animation where each object moves along its trajectory. To detect when the temporal controller goes to a new frame we can connect a slot to the updateTemporalRange() signal. See the following script :
```python
temporalController = iface.mapCanvas().temporalController()

def onNewFrame(range):
    ### Do something clever here
    
temporalController.updateTemporalRange.connect(onNewFrame)
```
The _onNewFrame_ function is called whenever the temporal controller changes its temporal range, i.e. whenever a new frame needs to be drawn. The range parameter the function receives is the frame's temporal range (begin and end times can be retrieved by calling range.begin() and range.end()). 
The interpolation from a point's trajectory to its location at a single instant (e.g. the beginning, middle, or end of the frame) will need to be done inside this function.

### On-the-fly interpolation
We could do the interpolation every time the _onNewFrame_ function is called. Again, the animation will only be smooth if execution_time < 1/FPS. Here, features need not store an attribute with the time of the interpolation since only features from the current frame are part of the layer (either the features are deleted and created at every frame, or the geometry of a fixed 100 features is changed every tick).
From this we can see two main ways of doing things.

### Buffering frames
We can do the interpolation for a fixed amount of frames, N. If we want the animation to be completely smooth, the execution of interpolation of the points for these N frames needs to be less than the time it takes for the N frames to be rendered (execution_time < N/FPS). For this solution, even though N frames are buffered, only 1 frame of the animation needs to be rendered at any given time. This means that the features generated will need to contain an attribute with the time of the interpolation. The temporal controller can then filter on this attribute to only show the features corresponding to the current frame.

## Experiments
The goal of these experiments is to measure the most efficient way to produce an animation. Achieving high performance is necessary if we want to be able to visualize the data in real time (i.e. not needing to pre-generate frames). There are 3 main time sinks:
- Querying the data from the database
- Interpolating a trajectory with a given timestamp (either database-side or qgis-side using the mobilitydb python driver)
- Adding features to a layer so they can be displayed

The following experiments attempt to compare different possible solutions

### Experiment 1
![Experiment1](https://user-images.githubusercontent.com/49359624/113512140-97710700-9563-11eb-9ea1-380f1228617a.png)
There are two steps to this experiment:
1. A one-time query to the database to retrieve the trajectories and store them in memory. This takes some time but we don't take it into account since it is a one-time operation.
2. The interpolation and addition of the interpolated values to add to the layer. This is done every **N**th frame, where **N** is the number of frames that are buffered (**N**=1 means no buffering). Here, there are two main time sinks, the time for the driver to do the interpolation and the time to add the features to the layer.

For easier measurements, we will simply simulate what a call of onNewFrame() would trigger in [this](#experiment-1-1) script. 

Running the script at two different times for 1 frame we obtain the following results  :
```
Total time: 0.07577347755432129 s.
Add features time: 0.023220062255859375 s.
Interpolation: 0.05182647705078125 s.
Number of features generated: 7
```
```
Total time: 0.10847806930541992 s.
Add features time: 0.04535698890686035 s.
Interpolation: 0.06148695945739746 s.
Number of features generated: 24
```
We can see that the interpolation time doesn't change much with the number of features generated. This is expected since interpolation is done on 100 features in any case, even if only a quarter (or tenth) actually yield a non-null result.
On the other hand, we can see the editing time (i.e. time to add features to the map) also logically increases with the number of features to be added to the layer.

By extrapolating these results, we can conclude that if this script was run at each frame (on-the-fly interpolation), the maximum framerate that could be achieved would be around 10 FPS.

Running this script with FRAMES_NB=50 at two different start frames we obtain the following results  :
```
Total time: 4.051093339920044 s.
Add features time: 1.458411693572998 s.
Interpolation: 2.5336971282958984 s.
Number of features generated: 1151
```
```
Total time: 2.549457311630249 s.
Add features time: 0.48203563690185547 s.
Interpolation: 2.041699171066284 s.
Number of features generated: 369
```
We can see that the interpolation time doesn't change much even though the number of features generated is very different. This is expected since the valueAtTimestamp() function from the driver is called 5000 times in both cases regardless of its return value. The editing time seems to be proportional to the number of features that are effectively added to the map. All in all, if we consider running this script takes between 3 and 4 seconds to generate 50 frames, the framerate's theoretical cap would be around 15 FPS, which isn't much better than on-the-fly interpolation.

#### Remarks
These experiments measure the performance of running the interpolation on the data and displaying features on the canvas. It is assumed that the trajectories for 100 rows have already been queried and stored in memory. Depending on how the query is performed (it could be advantageous to only store a small segment of the trajectory inside memory), this would also take time and be needed for an "in real time" animation. The theoritecal framerates obtained for both experiments are thus upper bounds on the final performance.

### Experiment 2
In this experiment, we try to query the interpolation of the trajectory directly from the database (i.e. without using the mobilitydb python driver). We can do so using the postgisexecuteandloadsql algorithm, which allows us to obtain a layer with features directly.
![Experiment2](https://user-images.githubusercontent.com/49359624/113512562-7d382880-9565-11eb-9427-6293224c3162.png)
The two main time sinks are now:
1. The processing algorithm time which runs the query, which includes the interpolation time since it is done database side.
2. The time to copy features from the processing algorithm result to the output layer.


Again, we will simulate a call of onNewFrame() in [this](#experiment-2-1) script.
Running the  script with FRAMES_NB=1 yields the following result:
```
Processing times : 0.07295393943786621
Add features times : 0.046048641204833984
Total time : 0.1190025806427002
```
Again we can see that we wouldn't be able to run the animation at more than 10 FPS.

Running the script with FRAMES_NB=50 and FRAMES_NB=200 gives the following:
```
Processing times : 2.367760419845581
Add features times : 0.9431586265563965
Total time : 3.3109190464019775
```
```
Processing times : 8.728699445724487
Add features times : 3.4965109825134277
Total time : 12.225210428237915
```
We can see performance here also seems to be capped at around 15 FPS.

#### Remarks
Due to an unknown bug, features that are generated using the algorithm don't actually show on the map unless the temporal controller is turned off, which makes it impossible to use unless the bug can be fixed.

### Experiment 3
Let's revisit experiment 1, but this time, instead of storing the whole tgeompoint column from the database into memory, let's only store the part needed to do the interpolation for the next 50 frames.
![Experiment3](https://user-images.githubusercontent.com/49359624/113595428-4895a100-9639-11eb-84b7-4cf1bf24ada6.png)

Since the interpolation will be done on a smaller segment of the trajectory, we can expect it to be much faster. However, the time to add the features to the layer, which is proportional to the number of features, probably won't change much.

The script for this experiment can be found [here](#experiment-3-1)
Running this with NB_FRAMES=1 outputs the following:
```
Total time: 1.1713242530822754 s.
Add features time: 0.06384944915771484 s.
Interpolation: 0.0006940364837646484 s.
Number of features generated: 24
```
Since we only want the features for 1 frame, we are ignoring the time for the query takes to execute, since it would only need to be run once every 50 frames. We can see that the interpolation time is now very small. The limiting factor is now the time it takes for features to be added to the layer, or about 0.064 seconds which would result in a framerate around 15 FPS.

Let's now generate the features for all 50 frames of the period
```
Total time: 3.0664803981781006 s.
Query execution time: 1.0994305610656738
Total time without connection and query: 1.9227006435394287 s.
Add features time: 1.6872003078460693 s.
Interpolation: 0.16837859153747559 s.
Number of features generated: 1204
```
Since the query is done for 50 frames, we need to take its time into account, which is about 1.1 seconds. We can see that the interpolation time is still very low, almost negligible. Since 1200 features need to be added, the time to do so is relatively large. The main time consumption is due to the addition of the features to the layer and the time to run the query. This brings us to a time of around 2.8 seconds to generate 50 frames, or ~18 FPS.

## Summary
Experiment|FPS cap|Remarks
----------|-------|-------
1 No buffer|10|The query result is assumed to be stored whole in memory
1 Buffer|15|
2 No buffer|10|Due to a bug, features don't actually show
2 Buffer|15|
3 No buffer|15|/
3 Buffer|18|


## Parallelization
To parallelize the animation rendering and feature generation processes we can use a QGIS *task*. This object from the API provides a way to start some computer intensive work in a background thread, without the rest of the application freezing. This is exactly what we want to do when querying data from the database and generating features. However, there is a catch: anything interacting with GUI components (such as the canvas or layers) should only do so in the main thread, and cannot be done inside a task. This means that we can parallelize the query, the creation of the features themselves, but not the addition of the generated features to the layer.

The final implementation works in the following way, and we assume we are using a buffer of 50 frames, and that the current buffer the temporal controller is currently rendering has already been generated:

Every frame the *onNewFrame* function is called by the temporal controller. If the frame number is a multiple of 50 (let's say we are at frame number 0), the function launches a QGIS task that generate the features for the frames between frame 50 and frame 99, which are the frames from the next buffer (frames between 0 and 49 are assumed to already have been generated). Once the task has performed the query to the database to get the corresponding trajectory segments, it creates features with geometries that are the interpolation of between every segment and the timestamps of the 50 different frames. Once this is done, the task ends, and a function from the main thread can then add the features to the layer. If all of the features are added before the temporal controller reaches frame 50, the animation should be smooth.

### Problem
In practice the above example works as expected except for one (pretty major) problem. The task (meaning the interpolation and feature generation procedure) is done in about 20 frames. Which means that at frame 20 of the animation, the features corresponding to frames between 50 and 99 are added to the layer. Adding these features takes less than the 29 remaining frames before frame 50, but the temporal controller stops nonetheless. This means that the animation pauses at frame 20, before resuming at frame 21 once all of the features from the buffer have been added. Unfortunately, since adding the features to the layer must be done from the main thread, there is no way to solve this issue using this approach. Other approaches have been experimented with but weren't successful, which means that navigating through the MobilityDB table using the temporal controller in real time could not be achieved.
## Appendix
### Experiment 1
```python
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
```
[Back to experiment 1](#experiment-1)

### Experiment 2
```python
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
```
[Back to experiment 2](#experiment-2)

### Experiment 3
```python
## Import rows of mobilitydb table into a 'rows' variable
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
```
[Back to experiment 3](#experiment-3)
