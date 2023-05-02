from datetime import datetime
from flask import Flask, request
import shutil
import os
from markupsafe import escape
import glob
import json
import folium
from telegram import Update
import gpxpy
import gpxpy.gpx
import threading

from telegram.ext import Application, ContextTypes, MessageHandler, CommandHandler, filters

DEFAULT_MAP_LOCATION = [49.443232, 1.099971]
ARCHIVE_FILE_PATH = 'MapArchives/'
MAP_FILE_NAME = 'map.html'
LOCATION_FILE_NAME = 'locations.json'
GPX_FILE_NAME = 'current.gpx'
USER_ID = '7a072a59-25a3-4700-ba83-5c1c0019c14a'


class FlaskThread(threading.Thread):
    def run(self) -> None:
        app.run(host="0.0.0.0")


class TelegramThread(threading.Thread):
    def run(self) -> None:
        main()

app = Flask(__name__)

#Metier
def load_locations_history_from_file():
    try:
        with open(LOCATION_FILE_NAME, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    
def load_gpx_to_map(m):
    # Charger le fichier GPX
    try:
        with open(GPX_FILE_NAME, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)

        # Ajouter les points GPX sur la carte
        for track in gpx.tracks:
            for segment in track.segments:
                points = [[point.latitude, point.longitude] for point in segment.points]
                folium.PolyLine(locations=points, color="green").add_to(m)
        
        return m
    except IOError:
        return m
    
def initiate_map(center_location):
    # Si center_location est vide, on définit par défaut
    if center_location is None:
        center_location=DEFAULT_MAP_LOCATION

    # Créer une carte centrée sur les coordonnées du premier point
    return folium.Map(location=center_location, zoom_start=11)

def addLocationsToMap(sorted_locations,m):
    for loc in sorted_locations:
        popup = f"<div style='width:200px'><small>le {loc['date']}</small><br/><br/>{loc['comment']}</div>"
        if loc['comment'] != '':
            icon=folium.Icon(color="green")
        else:
            icon=folium.Icon(color="black")            
        folium.Marker([loc['lat'], loc['lon']], popup=popup, icon=icon).add_to(m)
    return m

def refreshmap(): 
    # Recharger les données du fichier JSON
    sorted_locations = sorted(load_locations_history_from_file(), key=lambda x: x['date'])

    #Définition du centrage de la carte
    if not sorted_locations:
        center_location = None
    else :
        last_location = sorted_locations[-1]
        center_location = [last_location['lat'], last_location['lon']]
    
    m = initiate_map(center_location)
    m = load_gpx_to_map(m)
    m = addLocationsToMap(sorted_locations,m)
    m.save(MAP_FILE_NAME)

def save_locations(locations:json):
    locationsHistory = load_locations_history_from_file()

    # # Ajouter la date et l'heure actuelles à chaque coordonnée comme commentaire
    # date = datetime.fromtimestamp(loc['time']).strftime("%d-%m-%Y %H:%M:%S")
    # date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    data = [{'lat': loc['lat'], 'lon': loc['lon'], 'date': datetime.fromtimestamp(loc['time']).strftime("%d-%m-%Y %H:%M:%S"), 'comment': ''} for loc in locations]
    # Ajout des coordonnées envoyée à l'hitorique
    for loc in data:
        locationsHistory.append(loc) 
    # # Enregistrer les données dans un fichier JSON
    with open(LOCATION_FILE_NAME, 'w') as f:
        json.dump(locationsHistory, f)

    refreshmap()

def historize_Map_Files():
    print("Archiver")
    newArchiveNumber = 0
    newArchiveday = int(datetime.today().strftime('%Y%m%d'))

    # Recuperation de la dernière archive pour gestion à la journée et au numéro
    mapArchiveList = glob.glob(f"{ARCHIVE_FILE_PATH}/*")
    mapArchiveList.sort(reverse=True)

    #Si déjà une archive et une archive aujourd'hui, on positionne le numéro incrémenté
    if len(mapArchiveList) > 0:
        lastFileId = mapArchiveList[0].replace("MapArchives\\","").replace(".html","").replace("map","").split("-")
        if len(lastFileId) > 1:
            lastArchiveday = int(lastFileId[0])
            lastArchiveNumber = int(lastFileId[1])
            if lastArchiveday == newArchiveday:
                newArchiveNumber = lastArchiveNumber + 1

    shutil.copy2(MAP_FILE_NAME, f'{ARCHIVE_FILE_PATH}map{newArchiveday}-{newArchiveNumber}.html') 
    shutil.copy2(LOCATION_FILE_NAME, f'{ARCHIVE_FILE_PATH}location{newArchiveday}-{newArchiveNumber}.json') 
    
    os.remove(MAP_FILE_NAME) 
    m = initiate_map(DEFAULT_MAP_LOCATION)
    m.save(MAP_FILE_NAME)
    with open(LOCATION_FILE_NAME, 'w') as f:
        json.dump([], f)

#
#Telegram
#
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ExplicationText = "Ajoute un GPX pour qu'il soit prit en compte \n /Archiver pour sauvegarder les données et repartir sur une carte neuve"
    await update.message.reply_text(ExplicationText)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)

async def load_gpx_to_application(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    file = await context.bot.get_file(update.message.document)
    await file.download_to_drive(GPX_FILE_NAME)
    refreshmap()

async def archive_from_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    historize_Map_Files()
    await update.message.reply_text("Done")
 
#
#End points
#
@app.route('/user/<uuid:user_id>/adresses/historizeMap')
def historize_User_Map(user_id):
    if str(user_id) == USER_ID:
        historize_Map_Files()
        return 'ok'
    else:
        return 'bad request', 400

@app.route('/user/<uuid:user_id>/adresses',methods=['GET','POST'])
def index(user_id):
    if str(user_id) == str(USER_ID):
        if request.method == 'POST':
            adressesJson = json.loads(request.data)
            print(adressesJson["adresses"])
            save_locations(adressesJson["adresses"])
            return 'Ok'
        else:
            return load_locations_history_from_file()
    else:
        return 'bad request', 400

#
#Initialisation du serveur
#
def main():
    refreshmap()
    # Create the Application and pass it your bot's token.
    application = Application.builder().token("5950442484:AAFYRIdzU18QKOBMVEinaukl81gb8JrxUZ4").build()

    application.add_handler(CommandHandler('Help', help))
    application.add_handler(CommandHandler('Archiver', archive_from_telegram))
    application.add_handler(MessageHandler(filters.Document.FileExtension("gpx"), load_gpx_to_application))

    application.run_polling()

if __name__ == '__main__':
    flask_thread = FlaskThread()
    flask_thread.start()
    main()
    