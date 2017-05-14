import json
import requests
import re
from datetime import datetime,timedelta

print('Loading function')

def check_skype_id(description):
    match = re.search("https?://(?:www\.)?meet.lync\.com/?.*", description)
    if (match):
        print(description[match.start():match.end()])
        return description[match.start():match.end()]
    else:
        match = re.search("https?://(?:www\.)?join.skype\.com/?.*", description)
        if match:
            return description[match.start():match.end()]
        else:
            return None


def check_phone_number(description):
    match = re.search("\(?\d{3}\)?[-\s\.]?\d{3}[-\s\.]?\d{4}",description)
    if (match):
        print(description[match.start():match.end()])
        return description[match.start():match.end()]
    else:
        return None


def check_hangout_id(description):
    match = re.search("https?://(?:www\.)?hangouts.google\.com/?.*", description)
    if (match):
        print(description[match.start():match.end()])
        return description[match.start():match.end()]
    else:
        return None

def onesignalformat_datetime(datetime_String):
    timezone = datetime_String.rsplit(None, 1)[-1]
    datetime_String_split = datetime_String.rsplit(' ', 1)[0]
    datetime_object = datetime.strptime(datetime_String_split, '%b %d, %Y %I:%M:%S %p')
    datetime_object_1 = datetime_object - timedelta(minutes=1)

    datetime_object_string = datetime_object_1.strftime("%b %d, %Y %I:%M:%S %p")
    return datetime_object_string + " " + timezone

def lambda_handler(event, context):
    input = event
    response_data = []
    header = {"Content-Type": "application/json; charset=utf-8",
          "Authorization": "Authorization OneSignal ID"}
    player_id = input["onsignal_playerId"]
    for element in input["onesignal_events"]:    
    
        type = None
        value = None
        #check if there is hangout link
   
        hangout_id = check_hangout_id(element["description"])
        if hangout_id:
            type = "hangout"
            value = hangout_id
        # else if check if description contain skype id. set type = skype
        else:
            skype_id = check_skype_id(element["description"])
            if skype_id:
                type = "skype"
                value = skype_id
            # else if check if description contain Number.set type = phonenumber
            else:
                phonenumber = check_phone_number(element["description"])
                if (phonenumber):
                    type = "phonenumber"
                    value = phonenumber
                # else:
                #     #check if htmlLink contains hangout link or skype link
                #     skype_id = check_skype_id(element["htmlLink"])
                #     if skype_id:
                #         type = "skype"
                #         value = skype_id
                #     hangout_id = check_hangout_id(element["htmlLink"])
                #     if hangout_id:
                #         type = "hangout"
                #         value = hangout_id
    
        if type and value:
            #send notification
            print("send notification")
            data = {}
            data["Calender Id"] = element["Calender Id"]
            data["Event id"] = element["Event id"]
            data["description"] = element["description"]
            data["start_date"] = element["start_date"]
            data["type"] = type
            data["value"] = value
            send_after_time = onesignalformat_datetime(element["start_date"])
            payload = {"app_id": "OneSignal_APP_ID",
                       "include_player_ids": [player_id],
                       "contents": {"en": element["summary"]},
                        "data" : data,
                       "send_after": send_after_time
                       }
    
            req = requests.post("OneSignal_notification_url", headers=header, data=json.dumps(payload))
            
            print(req.status_code, req.reason)
            response_data.append(req.json())
    return response_data
