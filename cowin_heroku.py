import requests
import json
import fake_useragent
import logging
import pandas as pd
import os
from datetime import datetime
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

#pincode = "741101"
#date = "19-05-2021"
#district_id = "728"
#URL_PIN_DATE = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByPin?pincode={}&date={}".format(pincode, date)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
PORT = int(os.environ.get('PORT', '8443'))
TOKEN = "1779972424:AAGGyixrH_8cBQEbAqj6i6stgsrS7BYv7Ys"
APP_NAME = "https://mayukhcowinbot.herokuapp.com/"


def util(district_id, date):
    temp_user_agent = fake_useragent.UserAgent()
    browser_header = {'User-Agent': temp_user_agent.random}
    URL_DIS_ID_DATE = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id={}&" \
                      "date={}".format(district_id, date)
    response = requests.get(URL_DIS_ID_DATE, headers=browser_header)
    return json.dumps(response.json(), indent=4)



# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def cowin(update, context):
    """Send a message when the command /help is issued."""
    request = str(update.message.text).split(" ")[-1]
    date = str(str(datetime.now().day) + "-" + str(datetime.now().month) + "-" + str(datetime.now().year))
    district_id = "728"
    print(request, date, district_id)
    msg = util(district_id, date)
    update.message.reply_text(msg)


def help(update, context):
    text = "start -> check service is working\n" \
           "help -> get all commands\n" \
           "cowin <YOUR DISTRICT NAME> -> get Availability"
    update.message.reply_text(text)


def echo(update, context):
    """Echo the user message."""
    update.message.reply_text(update.message.text)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("cowin", cowin))
    dp.add_handler(CommandHandler("help", help))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_webhook(listen="0.0.0.0",
                          port=PORT,
                          url_path=TOKEN)
    # updater.bot.set_webhook(url=settings.WEBHOOK_URL)
    updater.bot.set_webhook(APP_NAME + TOKEN)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
