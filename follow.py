import folium
import json
from telegram import Update
from telegram.ext import Application, Updater, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler, JobQueue
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import gpxpy
import gpxpy.gpx
import time
from queue import Queue

locations = []
default_map_location = [49.443232, 1.099971]
default_chat_id = -938670097

def save_locations(locations):
    # Ajouter la date et l'heure actuelles à chaque coordonnée comme commentaire
    date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    data = [{'lat': loc['lat'], 'lon': loc['lon'], 'date': date, 'comment': ''} for loc in locations]

    # Enregistrer les données dans un fichier JSON
    with open('locations.json', 'w') as f:
        json.dump(data, f)

def update_locations(index, new_comment):
    # Charger les données de localisation existantes
    locations = load_locations()

    # Mettre à jour le commentaire pour la localisation correspondante
    if index < len(locations):
        locations[index]['comment'] = new_comment

    # Sauvegarder les données de localisation mises à jour
    with open('locations.json', 'w') as f:
        json.dump(locations, f)

def load_locations():
    try:
        with open('locations.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

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

def handle_location(update: Update, context: CallbackContext):
    message = update.message
    chat_id = default_chat_id
    user = message.from_user

    if message.location is not None:
        # Récupération des coordonnées GPS de l'utilisateur
        lat = message.location.latitude
        lon = message.location.longitude
        coords = [lat, lon]

        # Ajouter la date et l'heure actuelles comme commentaire
        comment = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        # Ajout des coordonnées à la liste
        locations.append({'lat': lat, 'lon': lon, 'comment': comment})

        # Sauvegarde des coordonnées
        save_locations(locations)

        # Mise à jour de la carte
        refreshmap()

        # Envoi 
        context.bot.send_message(chat_id=chat_id, text='Coordonnées GPS enregistrées')

        # Affichage des logs dans la console
        print(f"Utilisateur {user.username} ({user.id}) a envoyé les coordonnées GPS : {coords}")

def handle_refreshmap(update, context):
    chat_id = default_chat_id

    # Mise à jour de la carte
    refreshmap()

    # Envoyer un message pour informer l'utilisateur que la carte a été mise à jour
    context.bot.send_message(chat_id=chat_id, text='La carte a été mise à jour !')

    # Affichage des logs dans la console
    print(f"La carte a été mise à jour !")

def edit_comment(update, context):
    message = update.message
    chat_id = default_chat_id
    user = message.from_user

    # Charger les localisations précédentes
    sorted_locations = sorted(load_locations(), key=lambda x: x['date'])

    # Récupérer les 10 dernières localisations
    last_locations = sorted_locations[-10:]

    # Créer un bouton pour chaque localisation
    buttons = []
    for i, loc in enumerate(last_locations):
        button_text = f"Localisation du {loc['date']} "
        button = InlineKeyboardButton(button_text, callback_data=str(i))
        buttons.append([button])

    # Créer un clavier en ligne pour afficher les boutons de localisation
    reply_markup = InlineKeyboardMarkup(buttons)

    # Envoyer le clavier en ligne à l'utilisateur
    context.bot.send_message(chat_id=chat_id, text='Choisissez la localisation à modifier :', reply_markup=reply_markup)

def handle_edit_location(update, context):
    query = update.callback_query
    chat_id = default_chat_id

    # Vérifier que la liste des localisations n'est pas vide
    locations = load_locations()
    if not locations:
        context.bot.send_message(chat_id=chat_id, text='Aucune localisation enregistrée !')
        return

    # Récupérer l'indice de la localisation sélectionnée
    location_index = int(query.data)

    # Demander à l'utilisateur d'entrer un nouveau commentaire
    context.user_data['location_index'] = location_index
    query.edit_message_text(text=f"Entrez le nouveau commentaire pour la localisation du {locations[location_index]['date']} :")

def handle_text(update, context):
    message = update.message
    chat_id = default_chat_id
    user = message.from_user

    # Vérifier si l'utilisateur est en train de modifier un commentaire
    if 'location_index' in context.user_data:
        # Modifier le commentaire pour la localisation choisie
        location_index = context.user_data['location_index']
        comment = message.text
        locations = load_locations()

        if not locations:
            context.bot.send_message(chat_id=chat_id, text='Aucune localisation enregistrée.')
            return

        # Sauvegarder les coordonnées mises à jour
        update_locations(location_index, comment)

        # Envoyer un message pour informer l'utilisateur que le commentaire a été modifié
        context.bot.send_message(chat_id=chat_id, text=f"Le commentaire pour la localisation du {locations[location_index]['date']} a été mis à jour !")

        # Réinitialiser les données utilisateur
        context.user_data.pop('location_index', None)

        # Mise à jour de la carte
        refreshmap()

    else:
        # Envoyer la liste des commandes prises en charge
        commands = [
            "/refreshmap - Mettre à jour la carte",
            "/editcomment - Modifier le commentaire d'une localisation enregistrée",
        ]

        # Créer un message combiné avec "Commande non reconnue" et la liste des commandes
        combined_message = "Commande non reconnue.\n\nVoici la liste des commandes prises en charge :\n\n" + "\n\n".join(commands)
        
        # Envoyer le message combiné à l'utilisateur
        context.bot.send_message(chat_id=chat_id, text=combined_message)

def handle_message(update, context: CallbackContext):
    chat_id = "-914001647"

    if update.message and update.message.chat_id == int(chat_id):
        print(f"New message: {update.message.text}")

def main():
    # Charger la map au démarrage
    refreshmap()

    application = Application.builder().token("5950442484:AAFYRIdzU18QKOBMVEinaukl81gb8JrxUZ4").build()
    
    chat_id = default_chat_id

    location_handler = MessageHandler(filters.LOCATION, handle_location)
    application.add_handler(location_handler)
    
    refreshmap_handler = CommandHandler('refreshmap', handle_refreshmap)
    application.add_handler(refreshmap_handler)
    
    editcomment_handler = CommandHandler('editcomment', edit_comment)
    application.add_handler(editcomment_handler)
    application.add_handler(CallbackQueryHandler(handle_edit_location))
    
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))

    message_handler = MessageHandler(filters.TEXT, handle_message)
    application.add_handler(message_handler)

    # Démarrage du bot
    application.run_polling()

if __name__ == '__main__':
    main()