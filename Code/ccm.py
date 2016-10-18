'''----------------------------------------------------------------------------------
 Tool Name:   Conditioned Choropleth Mapmaker
 Source Name: ccm.py
 Version:     ArcGIS 10.0
 Author:      Geotech
 Description: Creates a conditional choropleth map (CCM) using the parameters
              specified in the tool. The CCM is then exported as an image file
              to the path specified by the user.
----------------------------------------------------------------------------------'''

import arcpy
import ast
import os
import numpy

arcpy.env.overwriteOutput = True

def ccm():

    # Get parameters from tool
    fc = arcpy.GetParameterAsText(0)
    output = arcpy.GetParameterAsText(1)
    filetype = arcpy.GetParameterAsText(2)
    classbreaktype = arcpy.GetParameterAsText(3)
    mainvar = arcpy.GetParameterAsText(4)
    mainvarbreaks = arcpy.GetParameterAsText(5).split(", ")
    convars = [arcpy.GetParameterAsText(6), arcpy.GetParameterAsText(8)]
    convarbreaks = [arcpy.GetParameterAsText(7).split(", "), arcpy.GetParameterAsText(9).split(", ")]

    # Define data fram schema
    schema = ['l_lset', 'l_mset', 'l_hset',
              'm_lset', 'm_mset', 'm_hset',
              'h_lset', 'h_mset', 'h_hset']

    # Load feature class into memory, create dataset
    fcmemory = arcpy.CreateFeatureclass_management('in_memory', 'in_memort_fc', template = fc)
    arcpy.CopyFeatures_management(fc, fcmemory)
    arcpy.MakeFeatureLayer_management(fcmemory, "ccmap_dataset")
    existing_fields = [i.name for i in arcpy.ListFields("ccmap_dataset")]
    for i in schema:
        if not i in existing_fields:
            arcpy.AddField_management("ccmap_dataset", i, "SHORT",
                                      field_alias = 'classes in {}'.format(i))

    # Convert mainvarbreaks to numbers for calculation
    for i in range(len(mainvarbreaks)):
        mainvarbreaks[i] = ast.literal_eval(mainvarbreaks[i])

    # Convert conditional variables to numbers for calculation
    for i in range(2):
        for j in range(4):
            convarbreaks[i][j] = ast.literal_eval(convarbreaks[i][j])
            
    # Generate SQL statements, selections, load into dataset
    quantiles = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    for i in range(3):
        if i == len(convarbreaks[0]) - 2:
            select_clause1 = '{} >= {} AND {} <= {}'.format(convars[0],
                                                            convarbreaks[0][i],
                                                            convars[0],
                                                            convarbreaks[0][i+1])
        else:
            select_clause1 = '{} >= {} AND {} < {}'.format(convars[0],
                                                           convarbreaks[0][i],
                                                           convars[0],
                                                           convarbreaks[0][i+1])
        for j in range(3):
            if j == len(convarbreaks[1]) - 2:
                select_clause2 = '{} >= {} AND {} <= {}'.format(convars[1],
                                                                convarbreaks[1][j],
                                                                convars[1],
                                                                convarbreaks[1][j+1])
            else:
                select_clause2 = '{} >= {} AND {} < {}'.format(convars[1],
                                                               convarbreaks[1][j],
                                                               convars[1],
                                                               convarbreaks[1][j+1])

            select_clause = select_clause1 + " AND " + select_clause2
            arcpy.SelectLayerByAttribute_management("ccmap_dataset",
                                                    "NEW_SELECTION",
                                                    select_clause)

            with arcpy.da.UpdateCursor("ccmap_dataset",
                                       (mainvar,
                                        schema[i*3+j],
                                        convars[0],
                                        convars[1])) as cur:
                for row in cur:
                    quantiles[1][i] += 1
                    quantiles[2][j] += 1
                    for k in range(len(mainvarbreaks)-1):
                        if k == len(mainvarbreaks)-2:
                            if row[0] >= mainvarbreaks[k] and row[0] <= mainvarbreaks[k+1]:
                                row[1] = k + 1
                                quantiles[0][k] += 1
                                break
                            else:
                                row[1] = 0
                        else:
                            if row[0] >= mainvarbreaks[k] and row[0] < mainvarbreaks[k+1]:
                                row[1] = k + 1
                                quantiles[0][k] += 1
                                break
                            else:
                                row[1] = 0                        
                    cur.updateRow(row)

            arcpy.SelectLayerByAttribute_management("ccmap_dataset",
                                                    "SWITCH_SELECTION")
            with arcpy.da.UpdateCursor("ccmap_dataset", (schema[i*3+j])) as cur:
                for row in cur:
                    row[0] = 0
                    cur.updateRow(row)
    
    # Clear selections from processing
    arcpy.SelectLayerByAttribute_management("ccmap_dataset", "CLEAR_SELECTION")

    outputmap("ccmap_dataset", output, mainvar, convars, mainvarbreaks,
               convarbreaks, filetype, classbreaktype)


def outputmap(dataset, output, mainvar, convars, mainvarbreaks,
                   convarbreaks, filetype, classbreaktype):

    # Load map document, data frames, layers and symbology template
    mxd = arcpy.mapping.MapDocument(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                'ccm_template.mxd'))
    dataframes = arcpy.mapping.ListDataFrames(mxd)
    layer = arcpy.mapping.Layer(dataset)
    symlayers = arcpy.mapping.Layer(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                  'ccm_symbology.lyr'))
    # Load maps to data frames
    for df in dataframes:
        symlayer = arcpy.mapping.ListLayers(symlayers, ('*' + df.name + '*'))[0]
        arcpy.mapping.UpdateLayer(df, layer, symlayer, True)
        arcpy.mapping.AddLayer(df, layer)

    # Output maps to data frams in layout view
    # (To be coded)
    #
    #

    # Populate text fields in template
    for elm in arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT"):
        if elm.name == "mainvartitle": elm.text = mainvar
        if elm.name == "convar1title": elm.text = convars[0]
        if elm.name == "convar2title": elm.text = convars[1]
        if elm.name == "mainmin": elm.text = str(round(float(mainvarbreaks[0]), 2))
        if elm.name == "mainb1": elm.text = str(round(float(mainvarbreaks[1]), 2))
        if elm.name == "mainb2": elm.text = str(round(float(mainvarbreaks[2]), 2))
        if elm.name == "mainmax": elm.text = str(round(float(mainvarbreaks[3]), 2))
        if elm.name == "con1min": elm.text = str(round(float(convarbreaks[0][0]), 2))
        if elm.name == "con1b1": elm.text = str(round(float(convarbreaks[0][1]), 2))
        if elm.name == "con1b2": elm.text = str(round(float(convarbreaks[0][2]), 2))
        if elm.name == "con1max": elm.text = str(round(float(convarbreaks[0][3]), 2))
        if elm.name == "con2min": elm.text = str(round(float(convarbreaks[1][0]), 2))
        if elm.name == "con2b1": elm.text = str(round(float(convarbreaks[1][1]), 2))
        if elm.name == "con2b2": elm.text = str(round(float(convarbreaks[1][2]), 2))
        if elm.name == "con2max": elm.text = str(round(float(convarbreaks[1][3]), 2))
    arcpy.RefreshActiveView()

    # Output map to specified file type
    if filetype == "AI": arcpy.mapping.ExportToAI(mxd, output)
    if filetype == "BMP": arcpy.mapping.ExportToBMP(mxd, output)
    if filetype == "EMF": arcpy.mapping.ExportToEMF(mxd, output)
    if filetype == "EPS": arcpy.mapping.ExportToEPS(mxd, output)
    if filetype == "GIF": arcpy.mapping.ExportToGIF(mxd, output)
    if filetype == "JPEG": arcpy.mapping.ExportToJPEG(mxd, output)
    if filetype == "PDF": arcpy.mapping.ExportToPDF(mxd, output)
    if filetype == "PNG": arcpy.mapping.ExportToPNG(mxd, output)
    if filetype == "SVG": arcpy.mapping.ExportToSVG(mxd, output)
    if filetype == "TIFF": arcpy.mapping.ExportToTIFF(mxd, output)

if __name__ == '__main__':
    
    ccm()
