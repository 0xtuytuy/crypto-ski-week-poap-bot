from queue import Empty
import re
from flask import Flask, request
import telegram
import redis
import os
import json


global bot, TOKEN, URL
TOKEN = os.environ.get("BOT_TOKEN")
bot = telegram.Bot(token=TOKEN)
URL = os.environ.get("BOT_URL")
r = redis.from_url(os.environ.get("REDIS_URL"))
app = Flask(__name__)

@app.route('/{}'.format(TOKEN), methods=['POST'])
def respond():
    # retrieve the message in JSON and then transform it to Telegram object
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    if update.message is None:
        return 'ok'
    
    chat_id = update.message.chat.id
    msg_id = update.message.message_id

    # Telegram understands UTF-8, so encode text for unicode compatibility
    text = update.message.text.encode('utf-8').decode()
    # for debugging purposes only
    print("got text message :", text)
    print("username: ", update.message.from_user['username'])
    
    # the first time you chat with the bot AKA the welcoming message
    if "/start" in text:
        # print the welcoming message
        bot_welcome = """
Welcome to Unit Crypto Ski Week POAP giveaway! 

POAP = proof of attendance protocol. 

Please claim it if you have bought your Crypto Ski Week Pass or were a resident of Crypto Ski Week. 
Claim your GiveAway by typing  your name after the command /name, here is an example:

/name satoshi

Built by 0xTuytuy
        """
        # registering the chat_id
        save_user(chat_id, update.message.from_user['username'], 'started')
        # send the welcoming message
        bot.sendMessage(chat_id=chat_id, text=bot_welcome, reply_to_message_id=msg_id)
    elif "/claim" in text:
        try:
            #get all users
            registered_user = json.loads(r.get('registered'))  
            #loop over all users
            for person in registered_user:
                #if user status says poap already claimed
                if person['name'] == update.message.from_user['username'] and person['status'] == 'claimed':
                    bot.sendMessage(chat_id=chat_id, text="You seem to have already claimed your POAP :/", reply_to_message_id=msg_id)
                    return 'ok'
                #looking for this user in the redis
                if person['name'] == update.message.from_user['username']:
                    # clear the message we got from any non alphabets
                    text = re.sub(r"\W", "_", text)
                    text = text.replace('_claim_', '')
                    poapUrls = json.loads(r.get('poapUrls'))
                    if "poapUrls" is None:
                        bot.sendMessage(chat_id=chat_id, text="We have ran out, if you were a paying participant in the CSW please get in touch with the UNIT team.", reply_to_message_id=msg_id)
                        return 'ok'
                    else:
                        bot.sendMessage(chat_id=chat_id, text="Just click on the link and follow insturctions to claim your POAP, if you have any problem reach out to @Oxtuytuy on Telegram " + poapUrls.pop(), reply_to_message_id=msg_id)
                        r.set('poapUrls', json.dumps(poapUrls))
                        save_user(chat_id, person['name'], 'claimed')
                        return 'ok'
        except Exception as e:
            # if things went wrong
            bot.sendMessage(chat_id=chat_id, text="There was a problem with claiming your POAP, please reach out to the Unit team", reply_to_message_id=msg_id)
            print(e)
    return 'ok'

@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    s = bot.setWebhook('{URL}{HOOK}'.format(URL=URL, HOOK=TOKEN))
    if s:
        return "webhook setup ok"
    else:
        return "webhook setup failed"

@app.route('/')
def index():
    return '.'

@app.errorhandler(404)
def handle_404(e):
    # handle all other routes here
    return 'Not Found, but we HANDLED IT'

def save_user(chat_id, name, status):
    try:
        # getting the pople who have registered already
        registered_users = json.loads(r.get('registered'))
        #checking if user exist before appending
        for id, person in enumerate(registered_users):
            if person['chat_id'] == chat_id:
                registered_users[id] = {'chat_id': chat_id, 'name': name, 'status': status}
                r.set('registered', json.dumps(registered_users))
                return
        new_user = {'chat_id': chat_id, 'name': name, 'status': status}
        #adding the new user to the list
        registered_users.append(new_user)
        #updating the list in DB
        r.set('registered', json.dumps(registered_users))
    except Exception as e:
        # if things went wrong
        print(e)
        return(e)

if __name__ == '__main__':
    app.run(threaded=True)
    