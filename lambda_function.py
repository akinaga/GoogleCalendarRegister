#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function
import urllib
import boto3
import httplib2
from apiclient import discovery
from oauth2client.file import Storage
from email.parser import Parser
from email.header import decode_header
import shutil
import os

print('Loading function')
s3 = boto3.client('s3')
shutil.copy2('credential/calendar-python-quickstart.json', '/tmp/calendar-python-quickstart.json')


def extract_content(row):
    dat = row.split("　")
    content = ""
    for da in dat[1:]:
        if da.replace("　", "") != "":
            content += da.replace("　", "")
    return content


def get_credentials():
    credential_path = '/tmp/calendar-python-quickstart.json'
    store = Storage(credential_path)
    credentials = store.get()
    return credentials


def lambda_handler(event, context):

    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.unquote_plus(event['Records'][0]['s3']['object']['key'].encode('utf8'))
    response = s3.get_object(Bucket=bucket, Key=key)
    print("CONTENT TYPE: " + response['ContentType'])

    body = response['Body'].read()
    # print(body)

    # google calender
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    # Cost Visualizerのカレンダー
    target_calendar_id = os.environ["target_calendar_id"]
    target_email_address = os.environ["target_email_address"]

    # Parsing Email
    headers = Parser().parsestr(body)
    print(decode_header(headers['To']))
    if decode_header(headers['To'])[0][0] == target_email_address:
        subject_iso = decode_header(headers['Subject'])
        if subject_iso[0][1]:
            subject = unicode(subject_iso[0][0], subject_iso[0][1]).encode("utf-8")
        else:
            subject = subject_iso[0][0]

        # DREAMS対応メール
        if "会議開催について" in subject:
            if subject_iso[0][1]:
                body = unicode(body, subject_iso[0][1]).encode("utf-8")
            msg = Parser().parsestr(body)
            body = str(msg.get_payload())
            body_dat = body.split("\n")
            starttime = ""
            endtime = ""
            date = ""
            title = ""
            for row in body_dat:
                if '１．会議名' in row:
                    title = extract_content(row)
                elif '３．実施日' in row:
                    date_txt = extract_content(row)
                    date = date_txt.split(" ")[0].replace("年", "-").replace("月", "-").replace("日", "")
                elif '４．時間' in row:
                    time_txt = extract_content(row)
                    if "〜" in time_txt:
                        starttime = time_txt.split("〜")[0].replace("\r","") + ":00+09:00"
                        endtime = time_txt.split("〜")[1].replace("\r","") + ":00+09:00"

            if title != "" and starttime != "" and endtime != "" and date != "":
                start = date + "T" + starttime
                end = date + "T" + endtime
                reg_event = {
                    'start': {'dateTime': start},
                    'end': {'dateTime': end},
                    'summary': title
                }
                print(str(reg_event).decode('string-escape'))
                created_event = service.events().insert(calendarId=target_calendar_id, body=reg_event).execute()

    return 1
