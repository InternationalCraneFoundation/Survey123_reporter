# sacr_reporter.py
# Modifed by Brian Barbieri based on the script by Dorn Moore, ICF
# 2018-01-16

# Purpose: Send email with new SACR sightings to list of reseachers depending
# on locations of the birds.
#
# TO DO
# Print messages to a log file

# Updated 2018-04-20 - Dorn Moore


# Establish a connection to your GIS.
from arcgis.gis import GIS

# This runs the python script named to pre-load the attachments
from DownloadAttachments import getAttachments

from datetime import datetime, timedelta
import os
import glob

# sendmail is an internal script
from sendmail import send_mail
# Get the secret passwords etc from the file
# Make sure you don't load secrets to your public GitHub - Bad things can happen, trust me.
from secrets import *


def convertTime(utcTimeStamp):  # convert stored times to readable times/dates
    # convert utcTimeStamp to seconds
    utcTimeStamp = utcTimeStamp/1e3

    # handle times before teh current epoch
    if utcTimeStamp < 0:
        ts = datetime(1970, 1, 1) + timedelta(seconds=utcTimeStamp)
    else:
        ts = datetime.fromtimestamp(utcTimeStamp)
    return ts


# What are your ArcGIS Enterprise/ArcGIS Online credentials? This is case
# sensitive.
# The variable below are encrypted to help with security

# --- Critical Parameters ---
PortalUrl = 'https://www.arcgis.com'

# AGOL Layer
agol_layer = 'your_agol_layer_id'
agol_qry = 'report_emailed =\'no\' or report_emailed is null'


# --- End Critical Parameters ---


# Setup pieces for ArcGIS Portal

# Set to False if ArcGIS Enterprise cert is not valid
PortalCertVerification = True

# Collect Attachments for files about to be processed.
getAttachments(PortalUserName, PortalPassword, PortalUrl, agol_layer, agol_qry)

# Connect to GIS, and get Feature Layer information
if PortalUserName == '' and PortalPassword == '':
    gis = GIS()
else:
    gis = GIS(PortalUrl, PortalUserName, PortalPassword,
              verify_cert=PortalCertVerification)

# search for the feature layer
search_result = gis.content.search(agol_layer)

layer = search_result[0]
lyrs = layer.layers
qr = lyrs[0].query(where=agol_qry)

# assign the feature set
qr_fset = qr.features

# Get the count of observations that match the query
fCount = 0
for f in qr_fset:
    fCount += 1
# print(fCount)

if fCount == 0:
    print("\n No new reports created.\n Ending Script.")

fNum = 0  # counter for the fetaures
while fNum < fCount:
    dict = qr_fset[fNum].attributes
    # Create a simplier set of variables to pass to our email

    # Convert the ESRI (UNIX) timestamp to something readable
    obsdate = convertTime(int(dict['date'])).strftime('%Y-%m-%d')

    submitdate = convertTime(int(dict['CreationDate'])).strftime('%Y-%m-%d')

    # NOTE: the section below here is coded specifically
    #   for our data layers. your feature names and verbage will be different
    #   This is crudely coded - it could use some cleanup but it works.


    # objectID
    objID = dict['objectid']

    # email address for the reporter
    reporter_email = dict['email']

    # cs is the county state variable used in a few locations
    # TODO: Add handling for Parishes in LA and Canadian Provinces
    if (dict['county']) is None:
        cs = dict['state']
    else:
        cs = dict['county'] + " County, " + dict['state']

    # combine the lon & lat to include a link in the report
    latlon = str(qr_fset[fNum].geometry['y'])+", " + \
        str(qr_fset[fNum].geometry['x'])
    link_latlon = "https://www.google.com/maps/place/"+str(qr_fset[fNum].geometry['y'])+"," + \
        str(qr_fset[fNum].geometry['x'])+"/@"+str(qr_fset[fNum].geometry['y'])+"," + \
        str(qr_fset[fNum].geometry['x'])+",17z/data=!3m1!1e3"

    # Construct the Subject Line
    subject = "SACR Report - " + obsdate + \
        " " + dict['time'] + " " + cs

    # Create the the message content for the email
    msg = ''
    msg += 'A new Sandhill Crane Sighting was submitted on %s.\n \n' % submitdate

    msg += "Observation Date:       %s \n" % obsdate
    msg += "Observation Time:       %s \n" % dict['time']
    msg += "Number of SACR:         %s \n" % dict['numsacr']
    msg += "County, State:          %s \n" % cs
    msg += "Latitude, Longitude:    %s \n" % latlon
    msg += "NOTE: Submitter may not have moved the map to locate the actual observation location.\n The location may not be accurate.\n"
    msg += "%s \n" % link_latlon
    msg += "\n"
    msg += "Observer:               %s \n" % dict['name']
    msg += "Email:                  %s \n" % dict['email']
    msg += "Phone #                 %s \n" % dict['phone']
    msg += "\n"
    msg += "Description:\n"
    msg += "%s \n" % dict['details']
    msg += "\n"
    msg += "Location Description:\n"
    msg += "%s \n" % dict['locationdesc']
    msg += "\n"
    msg += "Bands: \n"
    msg += "%s" % dict['bands']

    # TODO - Add attachments
    at = None
    if os.path.isdir(r"scriptDownloads\\SACR_Report\\"+str(objID)):
        at = []
        fileNames = glob.glob(
            "scriptDownloads\\SACR_Report\\"+str(objID)+"\\*.*")
        for file in fileNames:
            at.append(file)

    send_to = 'defaultEmail@ourdomain.org'  # Defualt recipient

    if dict['state'] in ('CA', 'WA', 'OR', 'BC', 'AK'):
        send_to = 'specialRecipient@ourDomain.org'  # Only send to this user if in certain states

    # Send the Message!
    send_mail(email_address, send_to, subject,
              msg, username=email_address,
              password=email_pass, files=at)

    # Set the 'sent' flag attribute to 'yes'
    feat_edit = qr_fset[fNum]
    feat_edit.attributes['report_emailed'] = 'yes'
    update_result = lyrs[0].edit_features(updates=[feat_edit])



    # Send a message to the reporter
    subject = "Thank you for reporting a banded Sandhill Crane!"

    msg = ""
    msg += "Thank you for reporting your banded Sandhill crane sighting.\n"
    msg += "Our researchers will contact you if we have questions.\n\n"

    msg += "Here is the report we received.\n"
    msg += "-------------------------------\n"
    msg += "Observation Date:       %s \n" % obsdate
    msg += "Observation Time:       %s \n" % dict['time']
    msg += "Number of SACR:         %s \n" % dict['numsacr']
    msg += "County, State:          %s \n" % cs
    msg += "\n"
    msg += "Observer:               %s \n" % dict['name']
    msg += "Email:                  %s \n" % dict['email']
    msg += "Phone #                 %s \n" % dict['phone']
    msg += "\n"
    msg += "Description:\n"
    msg += "%s \n" % dict['details']
    msg += "\n"
    msg += "Location Description:\n"
    msg += "%s \n" % dict['locationdesc']
    msg += "\n"
    msg += "Bands: \n"
    msg += "%s" % dict['bands']

    # Send the Message!
    send_mail(email_address,
              reporter_email, subject,
              msg, username=email_address,
              password=email_pass, files=at)

    # advance the count
    fNum += 1
