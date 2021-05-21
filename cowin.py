import requests
import json
import time
import pytz
import fake_useragent
import logging
import threading
import pandas as pd
from datetime import datetime
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
district = pd.read_csv("district_mapping.csv")
tz = pytz.timezone('Asia/Kolkata')
district_mapper = dict()
state_mapper = dict()
state_district_mapper = dict()
SORRY_MSG = "Message is clumsy because data is too much for telegram!!"
NO_DATA_MSG = "No Data Found"
SUMMARY_NO_DATA = "Try again with another date and location"
COWIN_RANGE_ITR_MSG = "For Date:="
SERVER_REBOOT_MSG = "Server to be rebooted!!\n" \
                    "No vaccination slot found at {} for age {}\n" \
                    "Register again after 10 minutes"
STOP_MSG = "Notification Stopped!!"
ERROR_MSG_REG = "You have to register first!!"
ERROR_MSG_DISTRICT = "ERROR!! in district name\n" \
                  "TYPE-> /d <YOUR STATE NAME> to find correct name"
ERROR_MSG_STATE = "ERROR!! in state name\n" \
                  "TYPE-> /s to find correct name"
ERROR_MSG_DATE = "ERROR!! Invalid date format\n" \
                       "Enter as DDMMYYYY"
ERROR_MSG_AGE = "ERROR!! Invalid age. 18 or 45 only allowed"
THREAD_LIST = dict()
STOP_FLAG = dict()
NOTIFICATION_PERIOD = 10
AGE_15 = 15
AGE_45 = 45
MSG_CHUNK_LENGTH = 50
REBOOT_HOUR = 11
REBOOT_MINUTE = 4

NOTIFICATION_MSG = "You will be notified when slot is available at "


def popuate():
    for index, row in district.iterrows():
        district_mapper[str(row['district name']).lower()] = row['district id']
        state_mapper[str(row['state_name']).lower()] = row['state_id']
        if str(row['state_name']).lower() in state_district_mapper.keys():
            state_district_mapper[str(row['state_name']).lower()].append(str(row['district name']).lower())
        else:
            state_district_mapper[str(row['state_name']).lower()] = [str(row['district name']).lower()]


def util_registry(district_name, district_id, age, update, context):
    noti_msg = NOTIFICATION_MSG + district_name + " for age " + str(age)
    update.message.reply_text(noti_msg)
    id = update.message.from_user['id']
    temp_user_agent = fake_useragent.UserAgent(verify_ssl=False)
    browser_header = {'User-Agent': temp_user_agent.random}
    summary = ""
    while (not STOP_FLAG[id]):
        if (datetime.now(tz).hour == REBOOT_HOUR) and (datetime.now(tz).minute == REBOOT_MINUTE):
            break
        date = str(datetime.now(tz).day) + "-" + str(datetime.now(tz).month) + "-" + str(datetime.now(tz).year)
        URL_DIS_ID_DATE = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id={}&" \
                          "date={}".format(district_id, date)
        response = requests.get(URL_DIS_ID_DATE, headers=browser_header)
        resp_json = response.json()["centers"]
        if len(resp_json) == 0:
            continue

        summary = ""
        for item in resp_json:
            for i in range(len(item['sessions'])):
                if AGE_45 == age and int(item['sessions'][i]['min_age_limit']) == age and int(item['sessions'][i]['available_capacity']) > 0:
                    summary += "Slot is Available for 45yrs old at " + str(item['name']) + ".\n"
                    break
                elif AGE_15 == age and int(item['sessions'][i]['min_age_limit']) == age and int(item['sessions'][i]['available_capacity']) > 0:
                    summary += "Slot is Available for 18yrs old at " + str(item['name']) + ".\n"
                    break

        if summary != "":
            try:
                update.message.reply_text(summary)
            except:
                summary = summary.split("\n")
                for i in range(0, len(summary), MSG_CHUNK_LENGTH):
                    update.message.reply_text("\n".join(summary[i:i+MSG_CHUNK_LENGTH]))
                update.message.reply_text(SORRY_MSG)
        time.sleep(NOTIFICATION_PERIOD)
    if summary == "" and (not STOP_FLAG[id]):
        update.message.reply_text(SERVER_REBOOT_MSG.format(district_name, age))


def util(district_id, date):
    temp_user_agent = fake_useragent.UserAgent(verify_ssl=False)
    browser_header = {'User-Agent': temp_user_agent.random}
    URL_DIS_ID_DATE = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id={}&" \
                      "date={}".format(district_id, date)
    response = requests.get(URL_DIS_ID_DATE, headers=browser_header)
    resp_json = response.json()["centers"]
    if len(resp_json) == 0:
        return NO_DATA_MSG, SUMMARY_NO_DATA

    results = []
    summary = ""
    for item in resp_json:
        result = dict()
        result['name'] = item['name']
        result['address'] = item['address']
        result['block'] = item['block_name']
        result['pincode'] = item['pincode']
        result['fee'] = item['fee_type']
        res = []
        for i in range(len(item['sessions'])):
            r = dict()
            r['avl'] = item['sessions'][i]['available_capacity']
            r['min_age'] = item['sessions'][i]['min_age_limit']
            r['vaccine'] = item['sessions'][i]['vaccine']
            r['avl_1'] = item['sessions'][i]['available_capacity_dose1']
            r['avl_2'] = item['sessions'][i]['available_capacity_dose2']
            res.append(r)
        result['itr'] = res

        for i in range(len(item['sessions'])):
            if int(result['itr'][i]['min_age']) == 45:
                if int(result['itr'][i]['avl']) > 0:
                    summary += "Slot is Available for 45yrs old at " + result['name'] + ".\n"
                    break
                else:
                    summary += "Slot was Available for 45yrs old at " + result['name'] + ".\n"
                    break
            elif int(result['itr'][i]['min_age']) == 18:
                if int(result['itr'][i]['avl']) > 0:
                    summary += "Slot is Available for 18yrs old at " + result['name'] + ".\n"
                    break
                else:
                    summary += "Slot was Available for 18yrs old at " + result['name'] + ".\n"
                    break
        results.append(result)

    summary += "\nCheck ^ for detailed info!!"
    return json.dumps({'results':results}, indent=4), summary


def start(update, context):
    update.message.reply_text("Hi! Welcome to Cowin utility chatbot!!\n"
                              "TYPE-> /help for available functionalities")


def getstates(update, context):
    text = ""
    for item in state_mapper.keys():
        text += str(item) + "\n"
    update.message.reply_text(text)


def getdistricts(update, context):
    state = " ".join(str(update.message.text).split(" ")[1:]).lower()
    text = ""
    try:
        districts = state_district_mapper[state]
    except:
        update.message.reply_text(ERROR_MSG_STATE)
        return
    for item in districts:
        text += str(item) + "\n"
    update.message.reply_text(text)


def cowin(update, context):
    district_name = " ".join(str(update.message.text).split(" ")[1:]).lower()
    date = str(datetime.now(tz).day) + "-" + str(datetime.now(tz).month) + "-" + str(datetime.now(tz).year)
    try:
        district_id = district_mapper[district_name.lower()]
    except:
        update.message.reply_text(ERROR_MSG_DISTRICT)
        return
    msg, summary = util(district_id, date)
    try:
        update.message.reply_text(msg)
        update.message.reply_text(summary)
    except:
        msg = json.loads(msg)
        for item in msg["results"]:
            update.message.reply_text(item)
        summary = summary.split("\n")
        for i in range(0, len(summary), MSG_CHUNK_LENGTH):
            update.message.reply_text("\n".join(summary[i:i + MSG_CHUNK_LENGTH]))
        update.message.reply_text(SORRY_MSG)


def cowin_date(update, context):
    district_name = " ".join(str(update.message.text).split(" ")[1:-1]).lower()
    date = str(update.message.text).split(" ")[-1]
    try:
        date = str(date[:2]) + "-" + str(date[2:4]) + "-" + str(date[4:])
    except:
        update.message.reply_text(ERROR_MSG_DATE)
        return
    try:
        district_id = district_mapper[district_name.lower()]
    except:
        update.message.reply_text(ERROR_MSG_DISTRICT)
        return
    msg, summary = util(district_id, date)
    try:
        update.message.reply_text(msg)
        update.message.reply_text(summary)
    except:
        msg = json.loads(msg)
        for item in msg["results"]:
            update.message.reply_text(item)
        summary = summary.split("\n")
        for i in range(0, len(summary), MSG_CHUNK_LENGTH):
            update.message.reply_text("\n".join(summary[i:i + MSG_CHUNK_LENGTH]))
        update.message.reply_text(SORRY_MSG)


def cowin_date_range(update, context):
    district_name = " ".join(str(update.message.text).split(" ")[1:-1]).lower()
    date_range = int(str(update.message.text).split(" ")[-1])
    try:
        district_id = district_mapper[district_name.lower()]
    except:
        update.message.reply_text(ERROR_MSG_DISTRICT)
        return
    for i in range(date_range):
        date = str(datetime.now(tz).day + i) + "-" + str(datetime.now(tz).month) + "-" + str(datetime.now(tz).year)
        msg, summary = util(district_id, date)
        update.message.reply_text(COWIN_RANGE_ITR_MSG + date)
        try:
            update.message.reply_text(msg)
            update.message.reply_text(summary)
        except:
            msg = json.loads(msg)
            for item in msg["results"]:
                update.message.reply_text(item)
            summary = summary.split("\n")
            for i in range(0, len(summary), MSG_CHUNK_LENGTH):
                update.message.reply_text("\n".join(summary[i:i + MSG_CHUNK_LENGTH]))
            update.message.reply_text(SORRY_MSG)


def register(update, context):
    district_name = " ".join(str(update.message.text).split(" ")[1:-1]).lower()
    age = int(str(update.message.text).split(" ")[-1])
    if age != 18 and age != 45:
        update.message.reply_text(ERROR_MSG_AGE)
        return
    try:
        district_id = district_mapper[district_name.lower()]
    except:
        update.message.reply_text(ERROR_MSG_DISTRICT)
        return
    THREAD = threading.Thread(target=util_registry, args=(district_name, district_id, age, update, context, ))
    THREAD.start()
    THREAD_LIST[update.message.from_user['id']] = THREAD
    STOP_FLAG[update.message.from_user['id']] = False


def stop(update, context):
    user = update.message.from_user
    # print('You talk with user {} and his user ID: {} '.format(user['username'], user['id']))
    if user['id'] in THREAD_LIST.keys():
        STOP_FLAG[user['id']] = True
        THREAD_LIST[user['id']].join()
        del THREAD_LIST[user['id']]
        del STOP_FLAG[user['id']]
        update.message.reply_text(STOP_MSG)
    else:
        update.message.reply_text(ERROR_MSG_REG)


def help(update, context):
    text = "/start -> check service is working\n" \
           "/help -> get all commands\n" \
           "/c <YOUR DISTRICT NAME> -> get Availability\n" \
           "/s -> get all the state names\n" \
           "/d <YOUR STATE NAME> -> get all the district names\n" \
           "/cd <YOUR DISTRICT NAME> <DDMMYYYY> -> get availability on that day\n" \
           "/cdr <YOUR DISTRICT NAME> <RANGE> -> get availability on the range of days\n" \
           "/r <YOUR DISTRICT NAME> <AGE> -> register for slot availability notification\n" \
           "/stop-> stop receiving notification"
    update.message.reply_text(text)


def echo(update, context):
    update.message.reply_text(update.message.text)


def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    updater = Updater("1779972424:AAGGyixrH_8cBQEbAqj6i6stgsrS7BYv7Ys", use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("c", cowin))
    dp.add_handler(CommandHandler("s", getstates))
    dp.add_handler(CommandHandler("d", getdistricts))
    dp.add_handler(CommandHandler("cd", cowin_date))
    dp.add_handler(CommandHandler("cdr", cowin_date_range))
    dp.add_handler(CommandHandler("r", register))
    dp.add_handler(CommandHandler("stop", stop))

    dp.add_handler(MessageHandler(Filters.text, echo))

    dp.add_error_handler(error)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    popuate()
    main()
