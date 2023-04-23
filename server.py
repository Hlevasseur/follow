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

from telegram.ext import Application, ContextTypes, MessageHandler, filters

app = Flask(__name__)

DEFAULT_MAP_LOCATION = [49.443232, 1.099971]
ARCHIVE_FILE_PATH = 'MapArchives/'
MAP_FILE_NAME = 'map.html'

#Metier
def load_locations_history_from_file():
    try:
        with open('locations.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    
def initiate_map(center_location):
    # Si center_location est vide, on définit par défaut
    if center_location is None:
        center_location=DEFAULT_MAP_LOCATION

    # Créer une carte centrée sur les coordonnées du premier point
    return folium.Map(location=center_location, zoom_start=11)



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
    
    for loc in sorted_locations:
        popup = f"<div style='width:200px'><small>le {loc['date']}</small><br/><br/>{loc['comment']}</div>"
        if loc['comment'] != '':
            icon=folium.Icon(color="green")
        else:
            icon=folium.Icon(color="black")            
        folium.Marker([loc['lat'], loc['lon']], popup=popup, icon=icon).add_to(m)
    m.save(MAP_FILE_NAME)

def save_locations(locations:json):
    locationsHistory = load_locations_history_from_file()

    # # Ajouter la date et l'heure actuelles à chaque coordonnée comme commentaire
    date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    data = [{'lat': loc['lat'], 'lon': loc['lon'], 'date': date, 'comment': ''} for loc in locations]
    # Ajout des coordonnées envoyée à l'hitorique
    for loc in data:
        locationsHistory.append(loc) 
    # # Enregistrer les données dans un fichier JSON
    with open('locations.json', 'w') as f:
        json.dump(locationsHistory, f)

    refreshmap()

def historize_Map_File():
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
    os.remove(MAP_FILE_NAME) 
    m = initiate_map(DEFAULT_MAP_LOCATION)
    m.save(MAP_FILE_NAME)


#Telegram
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await print(update.message.text)

async def load_gpx_to_map(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print('load GPX')
    file = await context.bot.get_file(update.message.document)
    await file.download_to_drive('import.gpx')
    
    # context.bot.get_file(update.message.document).download()


    # Charger le fichier GPX
    # with open('gr210.gpx', 'r') as gpx_file:
    with open('import.gpx', 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)

    # Si center_location est vide, on définit par défaut
    if center_location is None:
        center_location=DEFAULT_MAP_LOCATION

    # Créer une carte centrée sur les coordonnées du premier point
    first_point = gpx.tracks[0].segments[0].points[0]
    m = folium.Map(location=first_point, zoom_start=11)
    # m = folium.Map(location=center_location, zoom_start=11)

    # Ajouter les points GPX sur la carte
    for track in gpx.tracks:
        for segment in track.segments:
            points = [[point.latitude, point.longitude] for point in segment.points]
            folium.PolyLine(locations=points, color="green").add_to(m)

    return m
#End points
@app.route('/user/<uuid:user_id>/adresses/historizeMap')
def historize_User_Map(user_id):
    if str(user_id) == '7a072a59-25a3-4700-ba83-5c1c0019c14a':
        historize_Map_File()
        return 'ok'
    else:
        return 'bad request', 400

@app.route('/user/<uuid:user_id>/adresses',methods=['GET','POST'])
def index(user_id):
    if str(user_id) == '7a072a59-25a3-4700-ba83-5c1c0019c14a':
        if request.method == 'POST':
            adresses = request.form['adresses']
            adressesJson = json.loads(adresses)
            save_locations(adressesJson)
            return 'Ok'
        else:
            return load_locations_history_from_file()
    else:
        return 'bad request', 400


def main():
    print('main')
    refreshmap()
    # Create the Application and pass it your bot's token.
    application = Application.builder().token("5950442484:AAFYRIdzU18QKOBMVEinaukl81gb8JrxUZ4").build()

    # on non command i.e message - echo the message on Telegram
    print('eco')

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    print('gpx')

    application.add_handler(MessageHandler(filters.Document.FileExtension("gpx"), load_gpx_to_map))
    print('polling')

    application.run_polling()
    print('fin main')


#Initialisation du serveur
if __name__ == '__main__':
    main()
    app.run()
    