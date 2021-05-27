import requests
import json
import fake_useragent
import logging
import os
import pandas as pd
from datetime import datetime
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
district = pd.read_csv("district_mapping.csv")
district_mapper = dict()
state_mapper = dict()
state_district_mapper = dict()
SORRY_MSG = "Message was too long"


PORT = int(os.environ.get('PORT', '88'))
TOKEN = "YOUR TOKEN"
APP_NAME = "https://mayukhcowinbot.herokuapp.com/"


def popuate():
    for index, row in district.iterrows():
        district_mapper[str(row['district name']).lower()] = row['district id']
        state_mapper[str(row['state_name']).lower()] = row['state_id']
        if str(row['state_name']).lower() in state_district_mapper.keys():
            state_district_mapper[str(row['state_name']).lower()].append(str(row['district name']).lower())
        else:
            state_district_mapper[str(row['state_name']).lower()] = [str(row['district name']).lower()]

def util(district_id, date):
    temp_user_agent = fake_useragent.UserAgent(verify_ssl=False)
    browser_header = {'User-Agent': temp_user_agent.random}
    URL_DIS_ID_DATE = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id={}&" \
                      "date={}".format(district_id, date)
    response = requests.get(URL_DIS_ID_DATE, headers=browser_header)
    resp_json = response.json()["centers"]
    if len(resp_json) == 0:
        return "No Data Found"

    results = []
    for item in resp_json:
        result = dict()
        result['name'] = item['name']
        result['address'] = item['address']
        result['block'] = item['block_name']
        result['pincode'] = item['pincode']
        result['fee'] = item['fee_type']
        result['avl'] = item['sessions'][0]['available_capacity']
        result['min_age'] = item['sessions'][0]['min_age_limit']
        result['vaccine'] = item['sessions'][0]['vaccine']
        result['avl_1'] = item['sessions'][0]['available_capacity_dose1']
        result['avl_2'] = item['sessions'][0]['available_capacity_dose2']
        results.append(result)

    return json.dumps({'results':results}, indent=4)


def start(update, context):
    update.message.reply_text('Hi!')


def getstates(update, context):
    text = ""
    for item in state_mapper.keys():
        text += str(item) + "\n"
    update.message.reply_text(text)


def getdistricts(update, context):
    state = " ".join(str(update.message.text).split(" ")[1:]).lower()
    text = ""
    for item in state_district_mapper[state]:
        text += str(item) + "\n"
    update.message.reply_text(text)


def cowin(update, context):
    district_name = " ".join(str(update.message.text).split(" ")[1:]).lower()
    date = str(datetime.now().day) + "-" + str(datetime.now().month) + "-" + str(datetime.now().year)
    district_id = district_mapper[district_name.lower()]
    msg = util(district_id, date)
    try:
        update.message.reply_text(msg)
    except:
        msg = json.loads(msg)
        for item in msg["results"]:
            update.message.reply_text(item)
        update.message.reply_text(SORRY_MSG)


def cowin_date(update, context):
    district_name = " ".join(str(update.message.text).split(" ")[1:-1]).lower()
    date = str(update.message.text).split(" ")[-1]
    date = str(date[:2]) + "-" + str(date[2:4]) + "-" + str(date[4:])
    district_id = district_mapper[district_name.lower()]
    msg = util(district_id, date)
    try:
        update.message.reply_text(msg)
    except:
        msg = json.loads(msg)
        for item in msg["results"]:
            update.message.reply_text(item)
        update.message.reply_text(SORRY_MSG)


def help(update, context):
    text = "/start -> check service is working\n" \
           "/help -> get all commands\n" \
           "/cowin <YOUR DISTRICT NAME> -> get Availability\n" \
           "/states -> get all the state names\n" \
           "/districts <YOUR STATE NAME> -> get all the district names\n" \
           "/cowin_date <YOUR DISTRICT NAME> <DDMMYYYY> -> get availability on that day"
    update.message.reply_text(text)


def echo(update, context):
    update.message.reply_text(update.message.text)


def error(update, context):
    if str(context.error) == "Message is too long":
        print("hi")
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    updater = Updater("YOUR TOKEN", use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("cowin", cowin))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("states", getstates))
    dp.add_handler(CommandHandler("districts", getdistricts))
    dp.add_handler(CommandHandler("cowin_date", cowin_date))

    dp.add_handler(MessageHandler(Filters.text, echo))

    dp.add_error_handler(error)

    updater.start_webhook(listen="0.0.0.0",
                          port=PORT,
                          url_path=TOKEN,
                          webhook_url=APP_NAME+TOKEN)


    updater.idle()


if __name__ == '__main__':
    popuate()
    main()
