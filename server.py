from datetime import datetime
from flask import Flask, request

from markupsafe import escape

import json
import folium

app = Flask(__name__)

default_map_location = [49.443232, 1.099971]

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
        center_location=default_map_location

    # Créer une carte centrée sur les coordonnées du premier point
    m = folium.Map(location=center_location, zoom_start=11)

    # # Ajouter les points GPX sur la carte
    # for track in gpx.tracks:
    #     for segment in track.segments:
    #         points = [[point.latitude, point.longitude] for point in segment.points]
    #         folium.PolyLine(locations=points, color="green").add_to(m)

    return m


def refreshmap(): 
    print('Refresh map')
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
    if len(sorted_locations) > 1:
        folium.PolyLine(locations=[[loc['lat'], loc['lon']] for loc in sorted_locations], color='green').add_to(m)
    m.save('map.html')


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

#End points
@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route('/user/<uuid:user_id>/adresses',methods=['GET','POST'])
def index(user_id):
    if str(user_id) == '7a072a59-25a3-4700-ba83-5c1c0019c14a':
        if request.method == 'POST':
            adresses = request.form['adresses']
            adressesJson = json.loads(adresses)
            save_locations(adressesJson)
            # return f'Endpoint d\'envoi de géolocalisation d\'un user : {user_id} avec les adresses : {escape(adresses)}'
            #Version  rawdata
            # rawdata =  request.get_data().decode("utf-8")
            # bothArray =  rawdata.split(";",2)
            # latArray = bothArray[0].split(",")
            # longArray = bothArray[1].split(",")
            return 'Ok'

        else:
            return f'Endpoint de recup ? de géolocalisation d\'un user : {user_id}'
    else:
        return 'bad request', 400

if __name__ == '__main__':
    refreshmap()
    app.run()