from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *
import urllib.request
import os
import json

app = Flask(__name__)
app.debug = False

line_bot_api = LineBotApi('token')
handler = WebhookHandler('Secret')

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):

    #送信された緯度・経度を取得。数値でくるので文字列化。
    lat = str(event.message.latitude)
    lon = str(event.message.longitude)

    url = "https://sueat.sikeserver.com/near.php?lat={0}&lon={1}".format(lat, lon)

    #Sikeserverに緯度・経度を送信
    try:
        headers = {"User-Agent": "curl/7.29.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            result = response.read()
    except:
        print("アクセスに失敗しました。")
        return

    #混雑度の低いお店データをJSONデータとしてSikeserverから取得
    columns = []
    restaurants = json.loads(result)

    #テンプレを作る
    for restaurant in restaurants:
        id = restaurant["id"]
        distance = str(restaurant["distance"])
        congestion = str(restaurant["congestion"] / 2)
        name = restaurant["name"]

        columns.append(
            CarouselColumn(
                thumbnail_image_url="https://sueat.sikeserver.com/image.php?restaurant=" + id,
                title=name,
                text="混雑度：約" + congestion + "人/10分\n" + "距離：約" + distance + "m",
                actions=[
                    {"type": "postback", "label": "地図を表示", "data": "M" + id},
                    {"type": "postback", "label": "混雑状況グラフを表示", "data": "C" + id}
                ]
            )
        )

    messages = TemplateSendMessage(
        alt_text='template',
        template=CarouselTemplate(columns=columns),
    )

    line_bot_api.reply_message(event.reply_token, messages=messages)

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
        #これはテスト用
        if (event.message.text == "位置座標"):
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text='line://nv/location')
                ]
            )

@handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data

    #テンプレから「地図を表示ボタン」を押されたら処理
    if data[0] == "M":
        id = data[1:]
        url = "https://sueat.sikeserver.com/restaurant.php?id=" + id

        try:
            headers = {"User-Agent": "curl/7.29.0"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                result = response.read()
        except:
            print("アクセスに失敗しました。")
            return

        #sikeserverからテンプレから押されたお店のJSONデータを取得
        columns = []
        restaurant = json.loads(result)

        title = restaurant["name"]
        address = restaurant["address"]
        latitude = restaurant["latitude"]
        longitude = restaurant["longitude"]

        line_bot_api.reply_message(
            event.reply_token,
            [
                LocationSendMessage(title, address, latitude, longitude)
            ]
        )
    elif data[0] == "C":
        id = data[1:]

        ImageMes = ImageSendMessage(
            original_content_url="https://sueat.sikeserver.com/chart.php?restaurant={}".format(id),
            preview_image_url="https://sueat.sikeserver.com/chart.php?restaurant={}&preview".format(id)
        )

        line_bot_api.reply_message(event.reply_token, ImageMes)

if __name__ == "__main__":
    port = 55555
    app.run(host="0.0.0.0", port=port)
