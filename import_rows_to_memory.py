## Import rows of mobilitydb table into a 'rows' variable
import psycopg2
from mobilitydb.psycopg import register
canvas = iface.mapCanvas()
temporalController = canvas.temporalController()
currentFrameNumber = temporalController.currentFrameNumber()

connection = None

try:
    # Set the connection parameters to PostgreSQL
    connection = psycopg2.connect(host='localhost', database='postgres', user='postgres', password='postgres')
    connection.autocommit = True

    # Register MobilityDB data types
    register(connection)

    # Open a cursor to perform database operations
    cursor = connection.cursor()

    # Query the database and obtain data as Python objects
    select_query = "SELECT trip FROM trips_test"
    dtrange = temporalController.dateTimeRangeForFrameNumber(currentFrameNumber)
    #select_query = "SELECT valueAtTimestamp(trip, '"+range.end().toString("yyyy-MM-dd HH:mm:ss-04")+"') FROM trips_test"
    cursor.execute(select_query)
    rows = cursor.fetchall()

except (Exception, psycopg2.Error) as error:
    print("Error while connecting to PostgreSQL", error)

finally:
    # Close the connection
    if connection:
        connection.close()
