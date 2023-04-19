import time
import json
import gpxpy
import gpxpy.gpx
import folium

from telegram import Bot
from telegram.ext import Updater, CallbackContext, MessageHandler, Filters

locations = []
default_map_location = [49.443232, 1.099971]
default_chat_id = -1001886649860

# Fonction permettant de charger le fichier json locations.json
def load_locations():
    try:
        with open('locations.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Fonction permettant de céer la carte si elle n'existe pas, ou de la recharger à partir des locations.json 
def refreshmap(): 
    # Recharger les données du fichier JSON
    sorted_locations = sorted(load_locations(), key=lambda x: x['date'])

    # Mise à jour de la carte centrer sur la dernière localisation et avec le gpx chargé
    if not sorted_locations:
        center_location = None
    else :
        last_location = sorted_locations[-1]
        center_location = [last_location['lat'], last_location['lon']]
    
    m = load_gpx_to_map(center_location=center_location)
          
    for loc in sorted_locations:
        popup = f"<div style='width:200px'><small>le {loc['date']}</small><br/><br/>{loc['comment']}</div>"
        if loc['comment'] != '':
            icon=folium.Icon(color="green")
        else:
            icon=folium.Icon(color="black")            
        folium.Marker([loc['lat'], loc['lon']], popup=popup, icon=icon).add_to(m)
    if len(sorted_locations) > 1:
        folium.PolyLine(locations=[[loc['lat'], loc['lon']] for loc in sorted_locations], color='green').add_to(m)
    m.save('map.html')

# Fonction permettant de charger si il existe, un fichier GPX sur la carte
def load_gpx_to_map(center_location):
    # Charger le fichier GPX
    with open('gr210.gpx', 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)

    # Si center_location est vide, on définit par défaut
    if center_location is None:
        center_location=default_map_location

    # Créer une carte centrée sur les coordonnées du premier point
    first_point = gpx.tracks[0].segments[0].points[0]
    m = folium.Map(location=center_location, zoom_start=11)

    # Ajouter les points GPX sur la carte
    for track in gpx.tracks:
        for segment in track.segments:
            points = [[point.latitude, point.longitude] for point in segment.points]
            folium.PolyLine(locations=points, color="green").add_to(m)

    return m

# Fonction qui traite les message reçu dans la conversation avec le bot
def handle_message(update, context: CallbackContext):
    chat_id = default_chat_id

    if update.message and update.message.chat_id == int(chat_id):
        print(f"New message: {update.message.text}")

def main():
    # Charger la map au démarrage
    refreshmap()

    bot_token = "6164311515:AAH7n5JeaOMx7bjWK5GLbwotbSchSUHqbaI"
    updater = Updater(bot_token)

    # Ajout d'un gestionnaire pour les messages
    dispatcher = updater.dispatcher
    message_handler = MessageHandler(Filters.text, handle_message)
    dispatcher.add_handler(message_handler)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

# https://api.telegram.org/bot6254604417:AAEZ_T80jfVOcFl5B0vJURlDE79gmU57VTM/sendMessage?chat_id=-870934366&text=Hello