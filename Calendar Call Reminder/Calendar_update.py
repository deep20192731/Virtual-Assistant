import json
import datetime
import requests
import json
import re

print('Loading function')


def find_notification_id(notification_list, player_id, event_id, calendar_id):
    for element in notification_list:
        # print(element)
        if "include_player_ids" in element and element["include_player_ids"] and player_id in element[
            "include_player_ids"]:
            if element["data"] and "Event id" in element["data"] and "Calender Id" in element["data"]:
                if event_id == element["data"]["Event id"] and calendar_id == element["data"]["Calender Id"] and not \
                element["canceled"] and element['remaining'] == 1:
                    return element["id"]
    return None


def lambda_handler(event, context):
    # print("Received event: " + json.dumps(event, indent=2))
    # print("value1 = " + event['key1'])
    # print("value2 = " + event['key2'])
    # print("value3 = " + event['key3'])
    # return event['key1']  # Echo back the first key value
    # #raise Exception('Something went wrong')
    input = event
    return_response_data = []
    header = {"Content-Type": "application/json; charset=utf-8",
              "Authorization": "Authorization OneSignal ID"}
    player_id = input["onsignal_playerId"]
    for element in input["onesignal_events"]:
        calendar_id = element["Calender Id"]
        event_id = element["Event id"]

        req = requests.get("OneSignal_notification_url=OneSignal_APP_ID",
                           headers=header)
        if req.status_code == 200:
            offset = 0
            response_data = req.json()
            # print(response_data)

            # print(response_data["total_count"])
            iteration_required = int(response_data["total_count"] / 50)
            print(iteration_required)
            i = 0
            flag = True
            # find the notification id
            while flag:
                print(i)
                notification_id = find_notification_id(response_data["notifications"], player_id, event_id, calendar_id)
                if notification_id:
                    # notification id found
                    print(notification_id)
                    # cancel the notification
                    cancel_notification_url = "OneSignal_notification_url" + notification_id + "?app_id=OneSignal_APP_ID"
                    cancel_req = requests.delete(cancel_notification_url, headers=header)
                    if cancel_req.status_code == 200:
                        # create the new notification
                        print("cancel success")
                        new_notification = {}
                        new_notification["onsignal_playerId"] = player_id
                        new_notification["onesignal_events"] = [element]
                        create_new_notification = requests.post(
                            "lambda_calendar_create_function", json=new_notification, headers=header)
                        if create_new_notification.status_code == 200:
                            print("new notification created Success")
                            return_response_data.append(create_new_notification.json())

                    flag = False
                    return_response_data.append(cancel_req.json())

                else:
                    if i <= iteration_required:
                        offset = offset + 50
                        req = requests.get(
                            "OneSignal_notification_url=OneSignal_APP_ID&offset=" + str(
                                offset),
                            headers=header)
                        response_data = req.json()
                        #print(response_data)

                        i = i + 1
                    else:
                        flag = False
                        # result_return = {}
                        # result_return["status_code"] = 400
                        # result_return["error"] = "Error updating calendar event. Event not found"
                        # return_response_data.append(result_return)
                        new_notification = {}
                        new_notification["onsignal_playerId"] = player_id
                        new_notification["onesignal_events"] = [element]
                        create_new_notification = requests.post(
                            "lambda_calendar_create_function", json=new_notification,
                            headers=header)
                        if create_new_notification.status_code == 200:
                            print("new notification created Success")
                            return_response_data.append(create_new_notification.json())
    return return_response_data
