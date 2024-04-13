import sys
import configparser
# Azure Text Analytics
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient

# Azure OpenAI

import os
from openai import AzureOpenAI
from flask import Flask, request, abort
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)

#Config Parser
config = configparser.ConfigParser()
config.read('config.ini')
# Azure OpenAI Key
client = AzureOpenAI(
    api_key=config["AzureOpenAI"]["KEY"],
    api_version=config["AzureOpenAI"]["VERSION"],
    azure_endpoint=config["AzureOpenAI"]["BASE"],
)
app = Flask(__name__)

channel_access_token = config['Line']['CHANNEL_ACCESS_TOKEN']
channel_secret = config['Line']['CHANNEL_SECRET']
#Config Azure Analytics
credential = AzureKeyCredential(config['AzureLanguage']['API_KEY'])

if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

handler = WebhookHandler(channel_secret)

configuration = Configuration(
    access_token=channel_access_token
)
@app.route("/")
@app.route("/hello")
def hello():
    return "Hello, World!"
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def message_text(event):
    #sentiment_result=azure_sentiment(event.message.text)
    sentiment_result, mining_result = azure_sentiment(event.message.text)
    if mining_result == None:
        mining_result = "no"
    openai_result = azure_openai(sentiment_result, mining_result)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                #messages=[TextMessage(text=sentiment_result)]
                messages=[TextMessage(text=openai_result)],
                # messages=[
                #     TextMessage(text=sentiment_result),
                #     TextMessage(text=mining_result),
                # ],
            )
        )
def azure_sentiment(user_input):
    text_analytics_client = TextAnalyticsClient(
        endpoint=config['AzureLanguage']['END_POINT'], 
        credential=credential)
    documents = [user_input]
    response = text_analytics_client.analyze_sentiment(
        documents, 
        show_opinion_mining=True,language="zh-cht")
    print(response)
    docs = [doc for doc in response if not doc.is_error]
    for idx, doc in enumerate(docs):
        print(f"Document text : {documents[idx]}")
        print(f"Overall sentiment : {doc.sentiment}")
    #return docs[0].sentiment
    if "mined_opinions" in docs[0].sentences[0]:
        if len(docs[0].sentences[0].mined_opinions) > 0:
            return docs[0].sentiment, docs[0].sentences[0].mined_opinions[0].target.text
        else:
            return docs[0].sentiment, None
    else:
        return docs[0].sentiment, None
def azure_openai(sentiment_result, mining_result):
    message_text = [
        {
            "role": "system",
            "content": "你是一名非常善解人意的客戶服務專員，懂得察言觀色，妥善地回應客人。",
        }
    ]

    user_input = ""

    if mining_result == "no":
        user_input = f"客戶對於這一次服務的感覺是{sentiment_result}，請針對這樣的感覺寫一段回覆給客戶，50個字以內。"
    else:
        user_input = f"客戶對於這一次服務的感覺是{sentiment_result}，他的感覺是對於{mining_result}，請針對這樣的感覺寫一段回覆給客戶，特別針對{mining_result}，50個字以內。"

    message_text.append({"role": "user", "content": user_input})

    completion = client.chat.completions.create(
        model=config["AzureOpenAI"]["DEPLOYMENT_NAME"],
        messages=message_text,
        temperature=0.7,
        max_tokens=800,
        top_p=0.95,

        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
    )
    modelname=config["AzureOpenAI"]["DEPLOYMENT_NAME"]
    print(modelname)
    airesult=modelname+completion.choices[0].message.content
    #return completion.choices[0].message.content
    return airesult
if __name__ == "__main__":
    app.run()