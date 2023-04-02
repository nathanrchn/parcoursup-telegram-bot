from telegram import Bot
from json import dumps, load
from time import time, sleep
from requests import post, get
from numpy import polyfit, linspace
from datetime import datetime, timedelta
from matplotlib.pyplot import plot, xlim, ylim, savefig, legend, close
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler

LOGIN: str = ""
CODE: str = ""
X_TOKEN_ID: int = 0
BOT_TOKEN: str = ""

PASSWORD = range(1)
URL = "https://mobile.parcoursup.fr/NotificationsService/services/"

users = []
bot = Bot(BOT_TOKEN)
time_for_summary = 1654578000
updater = Updater(BOT_TOKEN, use_context=True)
with open("voeux.json", "r") as v:
    voeux = load(v)


def login():
    headers = {
        "Host": "mobile.parcoursup.fr",
        "Authorization": "",
        "X-Token-Id": str(X_TOKEN_ID),
        "Content-Type": "application/json"
    }

    data = {
        "tokenId": int(X_TOKEN_ID),
        "login": LOGIN,
        "code": CODE
    }

    req = post(f"{URL}login", headers=headers, data=dumps(data))

    return req.headers["Authorization"], req.headers["X-Auth-Token"]


def get_enattente(authorization: str, x_auth_token: str):
    headers = {
        "Host": "mobile.parcoursup.fr",
        "Authorization": authorization,
        "X-Token-Id": str(X_TOKEN_ID),
        "X-Auth-Login": LOGIN,
        "X-Auth_Token": x_auth_token,
        "Content-Type": "application/json"
    }

    req = get(f"{URL}voeux?liste=enattente", headers=headers)

    return req.json()["voeux"]


def get_new_positions(voeux_list: list):
    global voeux

    for i in range(len(voeux_list)):
        for j in range(len(voeux["targets"])):
            if voeux["targets"][j]["voeuId"] == voeux_list[i]["voeuId"]:
                voeux["targets"][j]["positions"].append(int(voeux_list[i]["autresInformations"][0]["texte"].split("<strong>")[1].split("</strong>")[0]))


def get_graphs_and_dates():
    N = [i for i in range(voeux["n"] + 1)]
    LS = linspace(0, 50, 50)
    D = []

    for i in range(len(voeux["targets"])):
        A, B = polyfit(N, voeux["targets"][i]["positions"], 1)
        plot(N, voeux["targets"][i]["positions"], "r", label=f"{voeux['targets'][i]['name']}")
        plot(LS, A * LS + B, "b", label=f"{voeux['targets'][i]['name']} PREDICTION", alpha=0.3)
        ylim(0, max(voeux["targets"][i]["positions"]) + 10)
        xlim(0, 50)
        legend()
        savefig(f"{voeux['targets'][i]['name']}.png")
        close()

        D.append(-B/A)

    return D


def send_message(dates):
    for i in range(len(voeux["targets"])):    
        new_pct_change = round(((voeux["targets"][i]["positions"][-2] / voeux["targets"][i]["positions"][-1])-1)*100, 2)
        pct_change= round(((voeux["targets"][i]["positions"][0] / voeux["targets"][i]["positions"][-1])-1)*100, 2)
        nb_postitions_d = voeux["targets"][i]["positions"][0] - voeux["targets"][i]["positions"][-1]
        nb_postitions = voeux["targets"][i]["positions"][-2] - voeux["targets"][i]["positions"][-1]

        message = f"{voeux['targets'][i]['name']}:\n\nPourcentage d'avancement depuis hier: {new_pct_change}%,\nNombre de places prises depuis hier: {nb_postitions},\nPourcentage d'avancement depuis le début: {pct_change}%,\nNombre de places prises depuis le début: {nb_postitions_d},\nPosition actuelle en liste d'attente: {voeux['targets'][i]['positions'][-1]}\nDate prévue pour l'accès: {(datetime.strptime('02/06/22', '%d/%m/%y') +timedelta(days = dates[i])).strftime('%A %d %B')}\n\nGraphique:"

        for j in range(len(users)):
            bot.send_message(users[j], message)
            bot.send_photo(users[j], open(f"{voeux['targets'][i]['name']}.png", "rb"))

def start(update, context):
    update.message.reply_text("Bonjour, veuillez saisir le mot de passe:")
    return PASSWORD


def password(update, context):
    global users

    if update.message.text == "nathanestbeau":
        users.append(update.message.chat_id)
        update.message.reply_text(
            "Tous les jours à 7 heures du matin, je vais vous envoyer l'avancement du dossier Parcoursup de votre enfant.")
    else:
        update.message.reply_text("Mot de passe incorrect, veuillez réessayer.")
    return ConversationHandler.END


def cancel(update, context):
    return ConversationHandler.END


updater.dispatcher.add_handler(ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        PASSWORD: [MessageHandler(None, password)]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
))


def main():
    global time_for_summary, voeux

    while True:
        with open("voeux.json", "r") as v:
            voeux = load(v)
        if len(users) > 0 and time() > time_for_summary:
            voeux["n"] += 1
            auth, x_auth = login()
            voeux_list = get_enattente(auth, x_auth)
            get_new_positions(voeux_list)
            dates = get_graphs_and_dates()
            send_message(dates)
            with open("voeux.json", "w") as v: v.write(dumps(voeux))
            time_for_summary += 86400
            sleep(1)


updater.start_polling()
updater.dispatcher.run_async(main())
