# Author: ichivite@esri.com
# Tested with ArcGIS for Server 10.2.2
# Latest here: https://github.com/Cintruenigo/ArcGIS-Server-Stuff/edit/master/UpdateHatches.py

import arcpy, os, datetime
from arcpy import env

def main(argv=None):


     # Get Input Parameters
     env.workspace = r"D:\Tests\StatOil\StatOil.gdb"
     env.overwriteOutput = True
     lineFC = r"IHS_Europe_Calibrated_Small"                                 #PolylineM featureclass defining the input geometries for which hatches will be created. Typically roads, pipes etc
     routeIDFieldName = "NAME"                                               #The name of the field with unique values representing the route IDs in the PolylineM featureclass
     eventsFC = r"D:\Tests\StatOil\gdb in ismael.sde/GDB.DBO.events_"        #The point featureclass representing hatches being served by ArcGIS Server. Typically in a multi-user geodatabase
     routeMFieldName = "RouteM"                                              #The name of the field holding M information in the featureclass with events that will be served
     updateModeReplaceTable = True                                           #2 update modes:
                                                                             #   If True, the table in the geodatabase (eventsFC) is deleted and a new table with new events is created in its place.
                                                                             #   If False, the table in the gdb is first cleaned up (remove all rows), then new rows are added and indexes rebuilt
                                                                             #   If using updateModeReplace as True, make sure that your map service has 'schema locking' disabled so you do not have to stop the service while the script executes.
                                                                             #      I like updateModeReplaceTable as True  because it reduces the time requests to your eventsFC will return inconsistent results
                                                                             #      It is also comparatively faster, particularly as the size of the tables grows

     startTime =  datetime.datetime.now()
     
     for interval in [50000,10000,5000,50]:
          eventsFCInterval = eventsFC + str(interval)
          UpdateEvents (lineFC,routeIDFieldName,routeMFieldName,interval,eventsFCInterval, updateModeReplaceTable)

     endtime =  datetime.datetime.now()
     diff =  endtime - startTime  
     print "Time elapsed: " + diff
                         
def UpdateEvents(lineFC, routeIDFieldName, routeMFieldName, interval,eventsFC,updateModeReplaceTable):


     print "Processing interval: " + str(interval)
     print " Creating event table..."
     arcpy.CreateTable_management("in_memory","temp_Event_Table")
     event_Table = "in_memory/temp_Event_Table"
     fields = arcpy.Describe(lineFC).fields
     routeIDFieldExists=False
     routeIDFieldName = routeIDFieldName.lower()
     for field in fields:
          if field.name.lower()==routeIDFieldName:
               arcpy.AddField_management(event_Table, routeIDFieldName, field.type, field.scale,field.precision)
               routeIDFieldExists = True
     if routeIDFieldExists==False:
          print " Error! " + routeIDFieldName + " does not exist in: " + lineFC
          exit
     arcpy.AddField_management(event_Table, routeMFieldName, "DOUBLE")


     print " Populating event table..."
     #Construct string with events
     insertCursor = arcpy.da.InsertCursor(event_Table,[routeIDFieldName,routeMFieldName])
     with arcpy.da.SearchCursor(lineFC, ["SHAPE@",routeIDFieldName]) as lines:
          for row in lines:
               lineShape = row[0]
               startM = lineShape.firstPoint.M
               endM = lineShape.lastPoint.M
               #routeID = row[1].encode('utf-8')
               routeID = row[1]
               eventM = ((int(startM/interval))*interval)+interval
               while eventM < endM:
                    insertCursor.insertRow((routeID,eventM))
                    eventM = eventM + interval
     del insertCursor

     print " Create event layer..."
     #Create event layer
     arcpy.MakeRouteEventLayer_lr (lineFC, routeIDFieldName , event_Table, routeIDFieldName + " POINT " + routeMFieldName, "Ms", "#", "NO_ERROR_FIELD", "ANGLE_FIELD")

     if updateModeReplaceTable==False:
          print " Deleting events..."
          #Delete old events 
          arcpy.DeleteFeatures_management(eventsFC)
          print " Loading events..."
          #Append new events to eventsFC
          arcpy.Append_management(["Ms"], eventsFC, "NO_TEST","","")
          #Rebuild indexes. 
          print " Update indexes..."
          workspace = os.path.split(eventsFC)[0]
          tableName = os.path.split(eventsFC)[1]
          arcpy.RebuildIndexes_management(workspace, "NO_SYSTEM",tableName, "ALL")
     if updateModeReplaceTable==True:
          print " Persist events in temporary table..."
          #Persist events
          arcpy.CopyFeatures_management("Ms", eventsFC + "_temp")
          print " Swapping event tables"
          #Swapping event featureclasses
          arcpy.Rename_management(eventsFC, eventsFC + "_old", "FeatureClass")
          arcpy.Rename_management(eventsFC + "_temp", eventsFC, "FeatureClass")
          arcpy.Delete_management(eventsFC + "_old", "FeatureClass")


if __name__ == "__main__":
     sys.exit(main(sys.argv[1:]))
