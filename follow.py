import folium
import json
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

locations = []

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

    # Mise à jour de la carte
    last_location = sorted_locations[-1]
    m = folium.Map(location=[last_location['lat'], last_location['lon']], zoom_start=11)        
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

def handle_location(update: Update, context: CallbackContext):
    message = update.message
    chat_id = message.chat_id
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
    chat_id = update.message.chat_id

    # Mise à jour de la carte
    refreshmap()

    # Envoyer un message pour informer l'utilisateur que la carte a été mise à jour
    context.bot.send_message(chat_id=chat_id, text='La carte a été mise à jour !')

    # Affichage des logs dans la console
    print(f"La carte a été mise à jour !")

def edit_comment(update, context):
    message = update.message
    chat_id = message.chat_id
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
    chat_id = query.message.chat_id

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
    chat_id = message.chat_id
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

def main():
    # Connexion au bot Telegram
    updater = Updater('6064029835:AAF7qvRP-fLmYvDaXUBB_tKcGHgJ2cEv8Io')

    # Gestionnaire de commandes
    dispatcher = updater.dispatcher
    
    location_handler = MessageHandler(Filters.location, handle_location)
    dispatcher.add_handler(location_handler)
    
    refreshmap_handler = CommandHandler('refreshmap', handle_refreshmap)
    dispatcher.add_handler(refreshmap_handler)
    
    editcomment_handler = CommandHandler('editcomment', edit_comment)
    dispatcher.add_handler(editcomment_handler)
    dispatcher.add_handler(CallbackQueryHandler(handle_edit_location))
    
    dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), handle_text))

    # Démarrage du bot
    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
