import sys
import configparser
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Azure OpenAI
import os
from openai import AzureOpenAI

from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)

# google drive access 
scope = ['https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive"]

credentials = ServiceAccountCredentials.from_json_keyfile_name("cpcschoolkey.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("customerlog").sheet1
# Config Parser
config = configparser.ConfigParser()
config.read("config.ini")

# Azure OpenAI Key
client = AzureOpenAI(
    api_key=config["AzureOpenAI"]["KEY"],
    api_version=config["AzureOpenAI"]["VERSION"],
    azure_endpoint=config["AzureOpenAI"]["BASE"],
)

app = Flask(__name__)

channel_access_token = config["Line"]["CHANNEL_ACCESS_TOKEN"]
channel_secret = config["Line"]["CHANNEL_SECRET"]
if channel_secret is None:
    print("Specify LINE_CHANNEL_SECRET as environment variable.")
    sys.exit(1)
if channel_access_token is None:
    print("Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.")
    sys.exit(1)

handler = WebhookHandler(channel_secret)

configuration = Configuration(access_token=channel_access_token)

@app.route("/callback", methods=["POST"])
def callback():
    # get X-Line-Signature header value
    signature = request.headers["X-Line-Signature"]
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessageContent)
def message_text(event):
    if (event.message.text[0]=='/'):

        azure_openai_result = azure_openai(event.message.text[1:])
        userid=event.source.user_id
        userinput=event.message.text[1:]
        
    else:
        return
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        #username=line_bot_api.get_profile (event.source.user_id)
        sheet.append_rows([[userid,userinput,azure_openai_result]])
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=azure_openai_result)],
            )
        )

def azure_openai(user_input):
    message_text = [
        {
            "role": "system",
            "content": "",
        },
        {"role": "user", "content": user_input},
    ]
    liveguide='''
<住宿須知>
一、 報到地點：台灣中油公司人力資源處訓練所，嘉義市東區吳鳳南路94號。
交通方式： 
1. 由「國道1 號」嘉義交流道進入北港路，右轉進入中興路直行接興業西路，右轉吳鳳南路，直行100 公尺抵達。 
2. 由「國道3 號」下中埔交流道，往嘉義市區方向行駛，經忠義橋直行彌陀路，左轉芳安路，左轉吳鳳南路即抵達。
3. 台鐵火車站至訓練所之公車轉乘：公車時刻表請自行至嘉義縣公車處或嘉義客運網站查詢
二、 報到程序：
1.請依通知按時至指定地點辦理報到及簽到。
2.領取識別證及宿舍鑰匙（前一日提早入住者請於本所警衛室領取）。
三、食宿：
1.宿舍備有沐浴乳與洗髮精，受訓人員請自備環保杯、換洗衣物、毛巾、牙刷、
牙膏、肥皂、修面用具、文具用品、個人藥品及個人保健用品。
2.遠道受訓人員如需提前住宿，請於前一晚23點以前至中油訓練所大門守衛
室憑報到通知拿房間鑰匙進駐(提早入住者，晚餐請自理)。
3.敬業樓教室全面禁食，請勿於教室用餐。
四、注意事項：
1. 如攜帶貴重物品到訓，請自行保管。
2. 如需使用到「無障礙設施空間」，敬請事先電告各班輔導員。
3. 為利訓練相關前置作業，請受訓人員務必於至國家文官學院訓練資訊服務網
（網址：https://tis.nacs.gov.tw）填寫「資料卡」。
4. 遠道申請住宿受訓人員請注意:居住於嘉義縣市以外地區者可申請住宿，每週
請至少住宿3日以上，未達3日取消住宿資格(居住嘉義縣偏遠地區且單程車程
超過90分鐘者可申請住宿)。
五、住宿須知
1. 一般事項
(1) 受訓期間之活動，請依訓練手冊作息時間表實施。
(2) 請先熟悉環境瞭解緊急出口及避難器具等相關設施，並與班務輔導員、
宿舍管理員密切配合，如有建議事項請隨時反映處理。
(3) 宿舍內遇有困難或偶突發事件，請迅速報告班務輔導員，夜間則該向值
班人員或警衛報告（值班人員－17:30至隔日08:00，分機8000；警衛室週五晚間17:00至週一08:00，分機5099）。
2. 住宿生活作息須知
(1) 食：
A. 用餐時間及地點：早餐(7:30－8:00)、午餐(12:00－12:30)、晚餐
(17:30－18:00)，倘若上課至18:30，則晚餐改提供便當。用餐地點：
樂群樓宿舍B棟1樓餐廳，星期五不供晚餐，假日不供餐。
B. 中油訓練所室內全面內禁止吸煙及嚼食檳榔，教室禁止飲食。
C. 餐畢，請將桌面整理乾淨，座椅歸回原位，並將餐具、菜渣、果皮依分
類置放於收集桶內。
(2) 衣：服裝以端莊、典雅及整潔為原則，不宜穿著拖鞋、海灘褲等過於休
閒服飾。除晚間於寢室區外，均不得穿著拖鞋。
(3) 住：
A. 浴室提供沐浴乳及洗髮精，寢室內用品配備詳「附表1」，用畢請歸位。
B. 受訓人員未經許可，請勿擅自更換寢室及移動床位；宿舍內不得留
宿親友。
C. 請隨時依規定將寢具收存放置整齊，並保持寢室內之整潔，將派員不
定期抽檢。
D. 午休時間及晚間熄燈後，請保持安靜，避免影響他人休息。
E. 中油訓練所大門於晚間23:00時關閉，外出或假日請按時返回本所。
F. 宿舍內嚴禁吸煙、喝酒、嚼食檳榔及烹煮食物；離開寢室時，請隨手
關閉門外電源總開關，以維安全。
G. 衣物洗滌後應曬於宿舍區曬衣場或指定之場所，不得隨意置掛於寢
室，以維觀瞻。
H. 為配合節能措施，室內溫度未達26度時不開冷氣。
I. 床單、枕頭套、被套寢具換洗：換洗時，請勿放置物品於床舖上，如
有貴重物品請隨身攜帶。
J。
(4) 行：受訓人員可憑學員證及房間鑰匙，至警衛室借用中油訓練所腳踏
車。出發前請檢查車況，腳踏車僅供受訓人員外出購物使用，請勿騎至
上下坡等危險路段，如有遺失及損毀應負責修護恢復原狀或照價賠償之
責。
3. 保健：各樓層教室及宿舍備有簡易醫療箱（置於交誼廳）。若有重大疾病，
請速通知自治幹部或班務輔導員，或夜間值班人員，以便協助處理送醫治療。
4. 其他：
(1) 寢室提供鑰匙，貴重物品請自行妥善保管。
(2) 請保持室內清潔。
(3) 訓期結束請歸還借用物品及檢視個人物品是否有遺留再離開。
(4) 請於結訓日上午上課前將行李攜出，並將房間鑰匙帶到教室投入回收籃。
「附表1」光復樓宿舍物品清單一覽表
項目 物 品 名 稱 數量 備註
耗
品
1 沐浴乳 每間一瓶 (1)訓練期間每房衛生紙最多補充
3 卷，如尚不足請自備。
(2)沐浴乳洗髮精若用畢可補充。
2 洗髪乳 每間一瓶
3 衛生紙 每間 3 卷
常
備
物
品
1 棉被(或涼被) 每床 1 條
2 床 單 每床 1 條
3 枕 巾 每床 1 條
4 枕 頭 每床 1 個
5 衣 架 每人 5 支
6 雨 傘 每人 1 把
7 熱水瓶 每人 1 支
8 漱口杯 每人 1 個
9 玻璃杯 每人 1 個
10 拖 鞋 每人 1 雙
11 浴室拖鞋 每房 1 雙
12 吹風機 每房一台
公
共
物
品
1 飲水機
2 脫水機
3 烘乾機
4 洗衣精
5 洗衣板、刷子
6 電視機
備註：
1. 宿舍為雙人套房，內有兩張單人床、衣櫃、書桌、椅子及檯燈。
2. 住宿請自備毛巾、牙膏、牙刷、洗面乳及其他修面用品。
3. 洗衣間位於各樓層西側。（3 樓住宿人員請至其他樓層使用）
4. 晒衣場位於 1 樓外面北邊西側。
5. 本所總機（05）2282168，各宿舍房間號碼前加 8，即為該寢室之電
話號碼，例如 101 號房的電話分機為 8101，所內各房可直接互打，
找受訓人員之外線電話，請於撥通總機後，再按撥分機號碼即可。
6. 下班時間緊急聯絡電話：分機 8000 或 5099。
7.非公務需求可自費詳洽人訓所
8.熱水供應時間為下午5:00-24:00
</住宿須知>
'''

    message_text[0]["content"] += "你是一個中油人訓所住宿管理人員, "

    message_text[0]["content"] += "請一律用繁體中文回答，"
    message_text[0]["content"] += "請根據以下<住宿須知>規定回答，若<住宿須知>沒有寫的內容，請回答不清楚，請務必不要回答內容沒有寫的部份，並在回答前一步一步重新檢查是否為<住宿須知>的內容，例如有人問誰創造了，你要回答不知道。"
    message_text[0]["content"] += liveguide

    

    completion = client.chat.completions.create(
        model=config["AzureOpenAI"]["DEPLOYMENT_NAME"],
        messages=message_text,
        max_tokens=800,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
    )
    print(completion)
    return completion.choices[0].message.content


if __name__ == "__main__":
    app.run()